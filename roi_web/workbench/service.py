from __future__ import annotations

import base64
import json
import logging
import re
import threading
import uuid
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import psutil
from matplotlib.path import Path as MplPath
from scipy import ndimage
from skimage import measure
from send2trash import send2trash

from roi_workbench.core import CASE_STATUSES, CaseRecord, LabelDefinition, PredictionResult, combine_masks, normalize_case_status, split_label_map
from roi_workbench.imaging import case_image_hash, file_hash, is_completed_roi_path, is_nifti, load_mask, nifti_stem, patient_roi_paths, read_volume, scan_cases, write_mask_on_source_grid
from roi_workbench.models import NnInteractiveClient, NnInteractivePromptEngine, discover_models
from roi_workbench.storage import clear_recovery, labels_from_rows, load_recovery, safe_name, save_case, save_recovery

from roi_web.errors import ConflictError, NotFoundError, ValidationError
from roi_web.workbench.rendering import render_png
from roi_web.workbench.state import EditRecord, LoadedCase, RoiLayer, TaskEntry, WorkbenchState


LOGGER = logging.getLogger("roi_web")


class WorkbenchService:
    MAX_MESH_SOURCE_VOXELS = 2_000_000
    MAX_MESH_TRIANGLES = 300_000
    MAX_MESH_STEP = 8
    VASCULAR_HEPATIC_MODEL = "hepatic_artery"
    VASCULAR_ABDOMINAL_MODEL = "abdominal_artery"

    def __init__(self, project_root: Path):
        self.state = WorkbenchState(project_root.resolve())
        self.models = discover_models(self.state.project_root)
        self._recovery_lock = threading.RLock()
        self._recovery_timer: threading.Timer | None = None
        self._recovery_loaded: LoadedCase | None = None
        self._vascular_lock = threading.RLock()
        self._vascular_active_task_id = ""
        self._vascular_slot_reserved = False
        self._vascular_root_switch_reserved = False
        # Vascular pipelines are intentionally absent from the public build.
        self._vascular_pipeline_factory = None
        self._abdominal_vascular_pipeline_factory = None

    def _cancel_recovery(self, loaded: LoadedCase | None = None, clear: bool = False) -> None:
        with self._recovery_lock:
            if self._recovery_timer is not None and (loaded is None or self._recovery_loaded is loaded):
                self._recovery_timer.cancel()
                self._recovery_timer = None
                self._recovery_loaded = None
        if clear and loaded is not None:
            clear_recovery(loaded.case)

    def _schedule_recovery(self, loaded: LoadedCase) -> None:
        with self._recovery_lock:
            if self._recovery_timer is not None and self._recovery_timer.is_alive():
                return

            def persist() -> None:
                try:
                    with loaded.lock:
                        if loaded.dirty:
                            save_recovery(loaded.case, loaded.masks, loaded.volume, loaded.labels, loaded.provenance)
                finally:
                    with self._recovery_lock:
                        self._recovery_timer = None
                        self._recovery_loaded = None

            self._recovery_loaded = loaded
            self._recovery_timer = threading.Timer(30.0, persist)
            self._recovery_timer.daemon = True
            self._recovery_timer.start()

    def set_root(self, root: Path, discard_dirty: bool = False) -> dict[str, Any]:
        with self._vascular_lock:
            task_id = self._vascular_active_task_id
            active = self.state.tasks.get(task_id) if task_id else None
            if self._vascular_root_switch_reserved or self._vascular_slot_reserved:
                raise ConflictError("血管任务正在启动或数据根目录正在切换；请稍后重试")
            if active is not None and active.status not in {
                "completed", "completed_with_failures", "failed", "cancelled",
            }:
                raise ConflictError("血管任务运行期间不能切换数据根目录；请等待任务结束或先取消任务")
            self._vascular_root_switch_reserved = True
        try:
            return self._set_root_with_vascular_guard(root, discard_dirty)
        finally:
            with self._vascular_lock:
                self._vascular_root_switch_reserved = False

    def _set_root_with_vascular_guard(self, root: Path, discard_dirty: bool = False) -> dict[str, Any]:
        root = root.expanduser().resolve()
        if not root.is_dir():
            raise ValidationError(f"总文件夹不存在或不可访问：{root}")
        with self.state.lock:
            previous_generation = self.state.generation
            previous_loaded = self.state.loaded
            if previous_loaded is not None:
                with previous_loaded.lock:
                    previous_revision = previous_loaded.revision
                    previous_dirty = previous_loaded.dirty
                if previous_dirty and not discard_dirty:
                    raise ConflictError("当前病例有未保存修改；请先保存，或在当前页面确认放弃后再扫描")
            else:
                previous_revision = -1
                previous_dirty = False
        cases = scan_cases(root)
        discarded: LoadedCase | None = None
        with self.state.lock:
            if self.state.generation != previous_generation:
                raise ConflictError("扫描期间数据根目录或病例会话已改变，本次切换已取消")
            if self.state.loaded is not previous_loaded:
                raise ConflictError("扫描期间当前病例已改变；为保护ROI，本次切换已取消")
            if previous_loaded is not None:
                with previous_loaded.lock:
                    if previous_loaded.revision != previous_revision or previous_loaded.dirty != previous_dirty:
                        raise ConflictError("扫描期间病例产生了新修改；为保护ROI，本次切换已取消")
            discarded = self.state.loaded
            self.state.data_root = root
            self.state.cases = cases
            self.state.loaded = None
            self.state.generation += 1
        self._cancel_recovery(discarded, clear=bool(discarded and discard_dirty))
        return {"root": str(root), "case_count": len(cases)}

    def list_cases(self) -> list[dict[str, Any]]:
        with self.state.lock:
            cases = list(self.state.cases)
            data_root = self.state.data_root
        return [self._case_tree_item(case, data_root) for case in cases]

    def root_info(self) -> dict[str, Any]:
        with self.state.lock:
            return {
                "root": str(self.state.data_root) if self.state.data_root is not None else "",
                "case_count": len(self.state.cases),
            }

    @staticmethod
    def _relative_path(path: Path, parent: Path) -> str:
        try:
            return path.relative_to(parent).as_posix()
        except ValueError:
            return path.name

    @staticmethod
    def _layer_key(source_file: str, source_label_id: int) -> str:
        encoded = base64.urlsafe_b64encode(source_file.encode("utf-8")).decode("ascii").rstrip("=")
        return f"{encoded}:{int(source_label_id)}"

    @staticmethod
    def _next_runtime_label_id(used_ids: set[int], preferred: int) -> int:
        if 1 <= preferred <= 65535 and preferred not in used_ids:
            return preferred
        for candidate in range(60000, 65536):
            if candidate not in used_ids:
                return candidate
        for candidate in range(1, 60000):
            if candidate not in used_ids:
                return candidate
        raise ConflictError("当前会话 ROI 图层数已达到上限")

    @staticmethod
    def _resolve_layer(loaded: LoadedCase, label_id: int, layer_key: str = "") -> RoiLayer | None:
        layer = loaded.layers.get(label_id)
        if layer_key:
            if layer is None or layer.layer_key != layer_key:
                raise ConflictError("ROI 图层身份已变化；操作已阻止，请刷新图层列表后重试")
        return layer

    @classmethod
    def _bind_existing_layers(cls, loaded: LoadedCase, source_file: str, editable: bool) -> None:
        """Attach file-scoped metadata to masks restored through the legacy workspace."""
        loaded.layers.clear()
        for label in loaded.labels:
            if label.id not in loaded.masks:
                continue
            label.locked = not editable
            loaded.layers[label.id] = RoiLayer(
                runtime_id=label.id,
                source_file=source_file,
                source_label_id=label.id,
                layer_key=cls._layer_key(source_file, label.id),
                role="editable" if editable else "reference",
                editable=editable,
            )

    @classmethod
    def _file_item(cls, path: Path, patient_dir: Path, role: str) -> dict[str, Any]:
        try:
            size_bytes = path.stat().st_size if path.is_file() else None
        except OSError:
            size_bytes = None
        return {
            "name": path.name,
            "relative_path": cls._relative_path(path, patient_dir),
            "role": role,
            "size_bytes": size_bytes,
        }

    @staticmethod
    def _roi_file_role(path: Path) -> str:
        lower_name = path.name.lower()
        lower_parts = {part.lower() for part in path.parts}
        if lower_name.startswith(("mask.", "mask_")):
            return "mask"
        if "auto_baseline" in lower_parts:
            return "baseline"
        if lower_name == "workspace_labels.nii.gz":
            return "workspace_roi"
        if lower_name in {"roi.nii", "roi.nii.gz", "abdominal_arteries_roi.nii.gz"} or lower_name.startswith("roi_") or lower_name == "segmentation_labels.nii.gz":
            return "saved_roi"
        return "source_roi"

    @classmethod
    def _patient_roi_paths(cls, case: CaseRecord) -> list[Path]:
        return patient_roi_paths(case)

    @classmethod
    def _auto_roi_candidates(cls, case: CaseRecord) -> list[Path]:
        allowed_roles = {"saved_roi", "mask", "source_roi"}

        def order(path: Path) -> tuple[int, int, str]:
            relative = Path(cls._relative_path(path, case.patient_dir))
            top_level = len(relative.parts) == 1
            role = cls._roi_file_role(path)
            role_rank = {
                (True, "saved_roi"): 0,
                (True, "mask"): 1,
                (True, "source_roi"): 2,
                (False, "saved_roi"): 3,
                (False, "mask"): 4,
                (False, "source_roi"): 5,
            }.get((top_level, role), 9)
            try:
                modified = path.stat().st_mtime_ns
            except OSError:
                modified = 0
            return role_rank, -modified, cls._relative_path(path, case.patient_dir).lower()

        return sorted(
            (path for path in cls._patient_roi_paths(case) if cls._roi_file_role(path) in allowed_roles),
            key=order,
        )

    @classmethod
    def _case_tree_item(cls, case: CaseRecord, data_root: Path | None) -> dict[str, Any]:
        patient_dir = case.patient_dir
        if data_root is not None:
            patient_id = cls._relative_path(patient_dir, data_root)
            if patient_id in {"", "."}:
                patient_id = patient_dir.name
        else:
            patient_id = patient_dir.name

        if case.image_path.is_file():
            files = [cls._file_item(case.image_path, patient_dir, "image")]
        else:
            label = case.series_description.strip() or f"DICOM series-{case.case_id.rsplit('-', 1)[-1]}"
            files = [{
                "name": label,
                "relative_path": cls._relative_path(case.image_path, patient_dir),
                "role": "image",
                "size_bytes": None,
            }]

        for path in cls._patient_roi_paths(case):
            files.append(cls._file_item(path, patient_dir, cls._roi_file_role(path)))

        output_dir = case.output_dir()
        if output_dir.is_dir():
            try:
                output_files = sorted(path for path in output_dir.rglob("*") if path.is_file())
            except OSError:
                output_files = []
            for path in output_files:
                relative_parts = path.relative_to(output_dir).parts
                if "_history" in relative_parts or ".roi-workbench" in relative_parts:
                    continue
                name = path.name.lower()
                if name == "roi_project.json":
                    role = "project"
                elif not is_nifti(path):
                    continue
                elif "auto_baseline" in relative_parts:
                    role = "baseline"
                elif name == "workspace_labels.nii.gz":
                    role = "workspace_roi"
                else:
                    role = "saved_roi"
                files.append(cls._file_item(path, patient_dir, role))

        unique_files: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for item in files:
            key = (item["role"], item["relative_path"])
            if key not in seen:
                seen.add(key)
                unique_files.append(item)
        return {
            "case_id": case.case_id,
            "patient_id": patient_id,
            "status": case.status,
            "kind": case.kind,
            "series_description": case.series_description,
            "files": unique_files,
        }

    def _find_case(self, case_id: str) -> CaseRecord:
        with self.state.lock:
            case = next((item for item in self.state.cases if item.case_id == case_id), None)
        if case is None:
            raise NotFoundError("病例不存在，请重新扫描总文件夹")
        return case

    @staticmethod
    def _default_labels() -> list[LabelDefinition]:
        return [LabelDefinition(1, "ROI", "ROI", "#ff3b30", "1")]

    @staticmethod
    def _add_missing_labels(labels: list[LabelDefinition], masks: dict[int, np.ndarray]) -> None:
        known = {label.id for label in labels}
        palette = ["#ff3b30", "#34c759", "#007aff", "#ff9500", "#af52de", "#00c7be"]
        for label_id in sorted(masks):
            if label_id not in known:
                labels.append(LabelDefinition(label_id, f"label_{label_id}", f"Label {label_id}", palette[label_id % len(palette)]))
                known.add(label_id)

    @staticmethod
    def _display_info(loaded: LoadedCase) -> dict[str, Any]:
        array = np.asarray(loaded.volume.array_zyx)
        flat = array.reshape(-1)
        stride = max(1, flat.size // 200_000)
        sample = np.asarray(flat[::stride], dtype=np.float64)
        sample = sample[np.isfinite(sample)]
        if sample.size:
            p01, p1, p99, p999 = (float(value) for value in np.percentile(sample, [0.1, 1.0, 99.0, 99.9]))
            minimum, maximum = float(sample.min()), float(sample.max())
        else:
            p01, p1, p99, p999, minimum, maximum = 0.0, 0.0, 1.0, 1.0, 0.0, 1.0
        robust_low, robust_high = p1, p99
        if robust_high - robust_low < 1e-6:
            robust_low, robust_high = p01, p999
        if robust_high - robust_low < 1e-6:
            robust_low, robust_high = minimum, maximum
        if robust_high - robust_low < 1e-6:
            robust_high = robust_low + 1.0

        declared = str(
            loaded.volume.source_geometry.modality
            if loaded.volume.source_geometry is not None
            else loaded.volume.geometry.modality
        ).upper()
        text = " ".join([
            loaded.case.case_id,
            loaded.case.series_description,
            loaded.case.image_path.name,
        ]).lower()
        if declared in {"CT", "MR"}:
            modality = declared
        elif re.search(r"(^|[^a-z0-9])(mr|mri|t1|t2|dwi|adc|flair|stir)([^a-z0-9]|$)", text):
            modality = "MR"
        elif re.search(r"(^|[^a-z0-9])ct([^a-z0-9]|$)", text) or (minimum <= -200 and maximum >= 200):
            modality = "CT"
        else:
            modality = "UNKNOWN"

        mr_width = max(robust_high - robust_low, 1.0)
        return {
            "suggested_modality": modality,
            "robust_low": robust_low,
            "robust_high": robust_high,
            "minimum": minimum,
            "maximum": maximum,
            "ct_default_level": 40.0,
            "ct_default_width": 400.0,
            "mr_default_level": robust_low + mr_width / 2.0,
            "mr_default_width": mr_width,
        }

    @staticmethod
    def _explicit_roi_path(case: CaseRecord, roi_relative_path: str) -> Path:
        patient_dir = case.patient_dir.resolve()
        candidate = (patient_dir / roi_relative_path).resolve()
        try:
            candidate.relative_to(patient_dir)
        except ValueError as exc:
            raise ValidationError("ROI 文件必须位于当前患者文件夹内") from exc
        if not candidate.is_file() or not is_nifti(candidate):
            raise ValidationError("选择的 ROI 文件不存在或不是 NIfTI")
        if case.image_path.is_file() and candidate == case.image_path.resolve():
            raise ValidationError("不能把原始影像作为 ROI 载入")
        return candidate

    def _vascular_output_identity_mismatch(self, case: CaseRecord, candidate: Path) -> bool:
        """Reject a shared top-level vascular ROI when it cannot be bound to this series."""
        try:
            patient_dir = case.patient_dir.resolve()
            resolved = candidate.resolve()
            is_top_level_vascular_roi = (
                resolved.parent == patient_dir
                and resolved.name.casefold() in {
                    "abdominal_arteries_roi.nii.gz",
                    "roi.nii.gz",
                }
            )
        except OSError:
            return True
        if not is_top_level_vascular_roi:
            return False
        with self.state.lock:
            patient_case_count = sum(
                item.patient_dir.resolve() == patient_dir
                for item in self.state.cases
            )
        matching = self._matching_vascular_manifest(
            case,
            resolved,
            allow_legacy_without_source=patient_case_count <= 1,
        )
        if matching:
            return False
        if self._vascular_manifest_has_conflicting_source(case, resolved):
            return True
        return patient_case_count > 1


    def load_case(
        self,
        case_id: str,
        discard_dirty: bool = False,
        roi_relative_path: str = "",
        expected_roi_sha256: str = "",
    ) -> dict[str, Any]:
        with self.state.lock:
            previous_generation = self.state.generation
            previous_loaded = self.state.loaded
            if previous_loaded is not None:
                with previous_loaded.lock:
                    previous_revision = previous_loaded.revision
                    previous_dirty = previous_loaded.dirty
                if previous_dirty and not discard_dirty:
                    raise ConflictError("已有病例存在未保存修改；请先保存，或在原页面确认放弃后再切换")
            else:
                previous_revision = -1
                previous_dirty = False
        case = self._find_case(case_id)
        volume = read_volume(case)
        labels = self._default_labels()
        masks: dict[int, np.ndarray] = {}
        auto_baseline: dict[int, np.ndarray] = {}
        provenance: dict[str, Any] = {}
        warnings: list[str] = []
        project_payload: dict[str, Any] = {}
        primary_roi_path: Path | None = None
        auto_roi_candidates = self._auto_roi_candidates(case)
        formal_roi_candidates = [path for path in auto_roi_candidates if is_completed_roi_path(case, path)]
        blocked_formal_roi = False
        output_dir = case.output_dir()
        project = output_dir / "roi_project.json"
        workspace = output_dir / "workspace_labels.nii.gz"
        native = output_dir / "segmentation_labels.nii.gz"
        integrity_ok = True
        if project.is_file():
            project_payload = json.loads(project.read_text(encoding="utf-8"))
            case.source_sha256 = case_image_hash(case)
            expected_source = str(project_payload.get("source_sha256", ""))
            if expected_source and expected_source != case.source_sha256:
                warnings.append("原始影像哈希已改变，旧ROI未载入")
                integrity_ok = False
                case.status = "未开始"
            expected_roi = str(project_payload.get("roi_sha256", ""))
            if expected_roi and (not native.is_file() or file_hash(native) != expected_roi):
                warnings.append("最终ROI文件缺失或哈希校验失败，旧ROI未载入")
                integrity_ok = False
                case.status = "失败"
            expected_workspace = str(project_payload.get("workspace_roi_sha256", ""))
            if expected_workspace and (not workspace.is_file() or file_hash(workspace) != expected_workspace):
                warnings.append("工作网格ROI文件缺失或哈希校验失败，旧ROI未载入")
                integrity_ok = False
                case.status = "失败"
            if integrity_ok:
                if project_payload.get("labels"):
                    labels = labels_from_rows(project_payload["labels"])
                provenance = dict(project_payload.get("provenance", {}))
                project_status = normalize_case_status(project_payload.get("status", case.status), "")
                if project_status in CASE_STATUSES:
                    case.status = project_status
                else:
                    case.status = "未开始"
                    warnings.append("项目中的病例状态非法，已重置为未开始")

        if integrity_ok:
            use_workspace = workspace.is_file() and bool(project_payload.get("workspace_roi_sha256"))
            saved_mask = workspace if use_workspace else native
            if saved_mask.is_file():
                masks.update(split_label_map(load_mask(saved_mask, volume)))
                primary_roi_path = saved_mask.resolve()

        if roi_relative_path:
            explicit_roi = self._explicit_roi_path(case, roi_relative_path)
            if self._vascular_output_identity_mismatch(case, explicit_roi):
                raise ValidationError(
                    f"{explicit_roi.name} 的来源指纹不属于当前影像序列，已拒绝载入；请切换到对应动脉期或重新运行腹部动脉分割"
                )
            try:
                roi_hash_before = file_hash(explicit_roi).lower()
                if expected_roi_sha256 and roi_hash_before != expected_roi_sha256.lower():
                    raise ConflictError("ROI 文件已在校验后发生变化，已取消载入；请刷新后重试")
                masks = split_label_map(load_mask(explicit_roi, volume))
                roi_hash_after = file_hash(explicit_roi).lower()
                if roi_hash_after != roi_hash_before:
                    raise ConflictError("ROI 文件在读取过程中发生变化，已取消载入；请刷新后重试")
            except (OSError, ValueError) as exc:
                raise ValidationError(f"ROI 载入失败：{exc}") from exc
            labels = self._default_labels()
            provenance = {"loaded_roi": self._relative_path(explicit_roi, case.patient_dir)}
            primary_roi_path = explicit_roi.resolve()
            case.status = "已完成"
            warnings.append(f"已载入 {explicit_roi.name}，可以继续查看和修改")
        elif integrity_ok and primary_roi_path is None and formal_roi_candidates:
            if len(formal_roi_candidates) > 1:
                warnings.append(
                    f"检测到 {len(formal_roi_candidates)} 份正式 ROI，未自动选择；请在 ROI 文件列表中明确勾选后再编辑"
                )
            else:
                candidate = formal_roi_candidates[0]
                if self._vascular_output_identity_mismatch(case, candidate):
                    blocked_formal_roi = True
                    warnings.append(
                        f"检测到 {candidate.name}，但来源指纹不属于当前影像序列，已阻止自动载入"
                    )
                else:
                    try:
                        masks = split_label_map(load_mask(candidate, volume))
                    except (OSError, ValueError) as exc:
                        warnings.append(f"既有 ROI {self._relative_path(candidate, case.patient_dir)} 无法载入：{exc}")
                    else:
                        labels = self._default_labels()
                        provenance = {
                            "loaded_roi": self._relative_path(candidate, case.patient_dir),
                            "auto_loaded_existing_roi": True,
                        }
                        primary_roi_path = candidate.resolve()
                        case.status = "已完成"
                        warnings.append(f"已自动载入既有 ROI：{self._relative_path(candidate, case.patient_dir)}")
            if len(formal_roi_candidates) == 1 and primary_roi_path is None:
                if blocked_formal_roi:
                    case.status = "未开始"
                else:
                    case.status = "失败"
                    warnings.append("患者文件夹中检测到正式 ROI，但没有一个能与当前影像正确匹配")

        self._add_missing_labels(labels, masks)
        for label in labels:
            masks.setdefault(label.id, np.zeros(volume.array_zyx.shape, dtype=bool))

        baseline_dir = case.output_dir() / "auto_baseline"
        if integrity_ok and baseline_dir.is_dir():
            workspace_files = list(baseline_dir.glob("label_*.workspace.nii.gz"))
            source_files = [path for path in baseline_dir.glob("label_*.nii.gz") if not path.name.endswith(".workspace.nii.gz")]
            for path in [*workspace_files, *source_files]:
                try:
                    label_text = path.name.removeprefix("label_").removesuffix(".nii.gz").removesuffix(".workspace")
                    label_id = int(label_text)
                    auto_baseline.setdefault(label_id, load_mask(path, volume).astype(bool))
                except (ValueError, OSError):
                    continue

        if roi_relative_path:
            recovery = None
        else:
            try:
                recovery = load_recovery(case, volume)
            except (OSError, ValueError, EOFError, zipfile.BadZipFile):
                recovery = None
                warnings.append("自动恢复缓存损坏，已忽略")
        if recovery:
            masks = {label_id: mask.copy() for label_id, mask in recovery.masks.items()}
            if recovery.labels:
                labels = recovery.labels
            provenance = recovery.project_state
            case.status = "修补中"
            warnings.append("已自动恢复上次未保存的ROI缓存")
            self._add_missing_labels(labels, masks)
            for label in labels:
                masks.setdefault(label.id, np.zeros(volume.array_zyx.shape, dtype=bool))

        loaded = LoadedCase(case, volume, labels, masks, auto_baseline=auto_baseline, provenance=provenance, warnings=warnings)
        if primary_roi_path is not None:
            initial_source = self._relative_path(primary_roi_path, case.patient_dir)
            loaded.selected_roi_files = [initial_source]
            loaded.provenance["editable_roi_source"] = initial_source
            loaded.provenance["loaded_roi"] = initial_source
            self._bind_existing_layers(loaded, initial_source, editable=True)
            # Keep legacy comparison layers available in the session inventory,
            # but do not include them in selected_roi_files/display by default.
            output_dir_resolved = output_dir.resolve()
            for candidate in auto_roi_candidates:
                if candidate.resolve() == primary_roi_path or self._roi_file_role(candidate) != "mask":
                    continue
                try:
                    imported_ids = self._append_reference_mask(loaded, candidate)
                    source = self._relative_path(candidate, case.patient_dir)
                    for imported_id, source_label_id in zip(
                        imported_ids,
                        [int(value) for value in loaded.provenance.get("imported_rois", [])[-1].get("source_labels", [])] if loaded.provenance.get("imported_rois") else [],
                    ):
                        loaded.layers[imported_id] = RoiLayer(
                            imported_id, source, source_label_id, self._layer_key(source, source_label_id),
                            role="reference", editable=False,
                        )
                except (OSError, ValueError, ConflictError) as exc:
                    warnings.append(f"对比 ROI {self._relative_path(candidate, case.patient_dir)} 未自动载入：{exc}")
        else:
            # A source-less workspace remains editable for backwards-compatible
            # manual drawing, but it is not presented as a selected patient ROI.
            initial_source = "@working/segmentation_labels.nii.gz"
            self._bind_existing_layers(loaded, initial_source, editable=True)
            loaded.provenance["editable_roi_source"] = initial_source
            for candidate in auto_roi_candidates:
                if self._roi_file_role(candidate) != "mask":
                    continue
                try:
                    imported_ids = self._append_reference_mask(loaded, candidate)
                    source = self._relative_path(candidate, case.patient_dir)
                    items = [item for item in loaded.provenance.get("imported_rois", []) if item.get("relative_path") == source]
                    source_labels = [int(value) for value in items[-1].get("source_labels", [])] if items else []
                    for imported_id, source_label_id in zip(imported_ids, source_labels):
                        loaded.layers[imported_id] = RoiLayer(
                            imported_id, source, source_label_id, self._layer_key(source, source_label_id),
                            role="reference", editable=False,
                        )
                except (OSError, ValueError, ConflictError) as exc:
                    warnings.append(f"对比 ROI {self._relative_path(candidate, case.patient_dir)} 未自动载入：{exc}")
        loaded.available_roi_files = [
            self._file_item(path, case.patient_dir, self._roi_file_role(path))
            for path in self._patient_roi_paths(case)
        ]
        loaded.display_info = self._display_info(loaded)
        loaded.dirty = bool(recovery)
        with self.state.lock:
            if self.state.generation != previous_generation:
                raise ConflictError("病例读取期间数据根目录或病例会话已改变，本次加载已取消")
            if self.state.loaded is not previous_loaded:
                raise ConflictError("病例读取期间当前病例已改变，本次加载已取消")
            if previous_loaded is not None:
                with previous_loaded.lock:
                    if previous_loaded.revision != previous_revision or previous_loaded.dirty != previous_dirty:
                        raise ConflictError("病例读取期间原病例产生了新修改，本次加载已取消")
            self.state.loaded = loaded
            self.state.generation += 1
        if previous_loaded is not None and previous_loaded is not loaded:
            self._cancel_recovery(previous_loaded, clear=bool(previous_loaded.dirty and discard_dirty))
        if loaded.dirty:
            self._schedule_recovery(loaded)
        return self.session_info()

    def require_loaded(
        self,
        expected_case_id: str | None = None,
        expected_session_token: str | None = None,
    ) -> LoadedCase:
        with self.state.lock:
            loaded = self.state.loaded
        if loaded is None:
            raise ConflictError("请先选择并载入一个病例")
        if expected_case_id is not None and loaded.case.case_id != expected_case_id:
            raise ConflictError(
                f"页面仍指向 {expected_case_id}，但服务当前病例已是 {loaded.case.case_id}；请求已阻止，请重新载入病例"
            )
        if expected_session_token is not None and loaded.session_token != expected_session_token:
            raise ConflictError("页面病例会话已过期；请求已阻止，请重新载入病例")
        return loaded

    @staticmethod
    def _orientation_info(shape: tuple[int, int, int], spacing: tuple[float, float, float]) -> dict[str, dict[str, Any]]:
        z, y, x = shape
        sx, sy, sz = spacing
        return {
            "axial": {"count": z, "rows": y, "cols": x, "row_spacing": sy, "col_spacing": sx, "markers": ["A", "P", "R", "L"]},
            "coronal": {"count": y, "rows": z, "cols": x, "row_spacing": sz, "col_spacing": sx, "markers": ["S", "I", "R", "L"]},
            "sagittal": {"count": x, "rows": z, "cols": y, "row_spacing": sz, "col_spacing": sy, "markers": ["S", "I", "A", "P"]},
        }

    def session_info(self, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            # Vascular inference runs outside the loaded editing session and can
            # publish a vascular ROI while the case remains open. Rebuild the
            # lightweight file inventory on every session read so the viewer can
            # offer the new artifact immediately without re-scanning the root.
            loaded.available_roi_files = [
                self._file_item(path, loaded.case.patient_dir, self._roi_file_role(path))
                for path in self._patient_roi_paths(loaded.case)
            ]
            declared = {int(value) for value in loaded.provenance.get("proposal_labels", [])}
            decided = {int(value) for value in loaded.provenance.get("decisions", {})}
            known_label_ids = {label.id for label in loaded.labels}

            def provenance_label_ids(key: str) -> list[int]:
                values: set[int] = set()
                for value in loaded.provenance.get(key, []):
                    try:
                        label_id = int(value)
                    except (TypeError, ValueError):
                        continue
                    if label_id in known_label_ids:
                        values.add(label_id)
                return sorted(values)

            result = {
                "data_root": str(self.state.data_root) if self.state.data_root is not None else "",
                "case_id": loaded.case.case_id,
                "session_token": loaded.session_token,
                "status": loaded.case.status,
                "revision": loaded.revision,
                "dirty": loaded.dirty,
                "shape_zyx": list(loaded.volume.array_zyx.shape),
                "spacing_xyz": list(loaded.volume.geometry.spacing_xyz),
                "reformatted_for_display": loaded.volume.reformatted_for_display,
                "orientations": self._orientation_info(loaded.volume.array_zyx.shape, loaded.volume.geometry.spacing_xyz),
                "labels": [
                    loaded.layers[label.id].to_json(label) if label.id in loaded.layers else label.to_json()
                    for label in loaded.labels
                ],
                "layers": [
                    loaded.layers[label.id].to_json(label) if label.id in loaded.layers else label.to_json()
                    for label in loaded.labels
                ],
                "selected_roi_files": list(loaded.selected_roi_files),
                "auto_baseline_labels": sorted(loaded.auto_baseline),
                "proposal_labels": sorted(set(loaded.ai_proposal) | (declared - decided)),
                "model_output_labels": provenance_label_ids("model_output_labels"),
                "empty_model_output_labels": provenance_label_ids("empty_model_output_labels"),
                "reference_label_ids": provenance_label_ids("reference_label_ids"),
                "editable_roi_source": str(loaded.provenance.get("editable_roi_source", "")),
                "working_layer_kind": str(loaded.provenance.get("working_layer_kind", "")),
                "loaded_roi_source": str(loaded.provenance.get("loaded_roi", "")),
                "interactive_reference": dict(loaded.provenance.get("interactive_reference", {})),
                "interactive_reference_label_ids": provenance_label_ids("interactive_reference_label_ids"),
                "interactive_reference_pending": bool(loaded.provenance.get("interactive_reference_pending", False)),
                "interactive_prompt_source": str(loaded.provenance.get("interactive_prompt_source", "")),
                "prompt_count": len(loaded.prompts),
                "warnings": list(loaded.warnings),
                "models": list(self.models),
                "display": dict(loaded.display_info),
                "available_roi_files": [dict(item) for item in loaded.available_roi_files],
                "range_operation_log": [dict(item) for item in loaded.operation_log],
            }
        if loaded.dirty:
            self._schedule_recovery(loaded)
        return result

    @staticmethod
    def _check_index(loaded: LoadedCase, orientation: str, index: int) -> None:
        count = WorkbenchService._orientation_info(loaded.volume.array_zyx.shape, loaded.volume.geometry.spacing_xyz)[orientation]["count"]
        if not 0 <= index < count:
            raise ValidationError(f"层号超出范围：{index}")

    @staticmethod
    def _parse_hidden_label_ids(value: str) -> set[int]:
        if not value.strip():
            return set()
        result: set[int] = set()
        for token in value.split(","):
            token = token.strip()
            if not token.isdecimal():
                raise ValidationError("ROI 显隐参数无效")
            label_id = int(token)
            if not 1 <= label_id <= 65535:
                raise ValidationError("ROI 显隐标签ID超出范围")
            result.add(label_id)
        return result

    @staticmethod
    def _layer_ids_from_keys(loaded: LoadedCase, value: str) -> set[int]:
        if not value.strip():
            return set()
        by_key = {layer.layer_key: runtime_id for runtime_id, layer in loaded.layers.items()}
        result: set[int] = set()
        for layer_key in value.split(","):
            runtime_id = by_key.get(layer_key.strip())
            if runtime_id is None:
                raise ValidationError("ROI 图层显隐身份已过期")
            result.add(runtime_id)
        return result

    @staticmethod
    def _layer_opacity_map(loaded: LoadedCase, value: str) -> dict[int, float]:
        if not value.strip():
            return {}
        try:
            raw = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValidationError("ROI 图层透明度参数无效") from exc
        if not isinstance(raw, dict) or len(raw) > 256:
            raise ValidationError("ROI 图层透明度参数无效")
        by_key = {layer.layer_key: runtime_id for runtime_id, layer in loaded.layers.items()}
        result: dict[int, float] = {}
        for layer_key, opacity in raw.items():
            runtime_id = by_key.get(str(layer_key))
            numeric = float(opacity)
            if runtime_id is None or not np.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
                raise ValidationError("ROI 图层透明度身份或数值无效")
            result[runtime_id] = numeric
        return result

    def slice_png(self, orientation: str, index: int, level: float, width: float, opacity: float, mode: str, boundary_width: int, baseline: bool, proposal: bool, expected_case_id: str | None = None, expected_session_token: str | None = None, hidden_labels: str = "", hidden_layers: str = "", layer_opacities: str = "") -> bytes:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        self._check_index(loaded, orientation, index)
        if (
            not np.isfinite(level)
            or not np.isfinite(width)
            or width <= 0.0
            or not 0.0 <= opacity <= 1.0
            or mode not in {"fill", "boundary"}
            or not 1 <= boundary_width <= 10
        ):
            raise ValidationError("ROI显示参数无效")
        with loaded.lock:
            hidden_ids = self._parse_hidden_label_ids(hidden_labels)
            hidden_ids.update(self._layer_ids_from_keys(loaded, hidden_layers))
            return render_png(
                loaded.volume.array_zyx, loaded.masks, {label.id: label.color for label in loaded.labels},
                loaded.auto_baseline, loaded.ai_proposal, orientation, index, level, width,
                opacity, mode, boundary_width, baseline, proposal, hidden_ids,
                self._layer_opacity_map(loaded, layer_opacities),
            )

    @staticmethod
    def _display_slice(mask: np.ndarray, orientation: str, index: int) -> np.ndarray:
        if orientation == "axial":
            return mask[index]
        if orientation == "coronal":
            return mask[::-1, index, :]
        return mask[::-1, :, index]

    @staticmethod
    def _replace_display_slice(mask: np.ndarray, orientation: str, index: int, data: np.ndarray) -> None:
        if orientation == "axial":
            mask[index] = data
        elif orientation == "coronal":
            mask[:, index, :] = data[::-1]
        else:
            mask[:, :, index] = data[::-1]

    @staticmethod
    def _label(loaded: LoadedCase, label_id: int, layer_key: str = "") -> LabelDefinition:
        layer = WorkbenchService._resolve_layer(loaded, label_id, layer_key)
        label = next((item for item in loaded.labels if item.id == label_id), None)
        if label is None:
            raise NotFoundError(f"标签 {label_id} 不存在")
        if layer is not None and not layer.editable:
            raise ConflictError(f"{layer.source_file} 的标签 {layer.source_label_id} 是只读图层；请先明确载入并编辑该文件")
        if label.locked:
            raise ConflictError(f"标签 {label_id} 已锁定")
        return label

    @staticmethod
    def _push_edit(loaded: LoadedCase, edit: EditRecord) -> None:
        if not edit.layer_key and edit.label_id in loaded.layers:
            edit.layer_key = loaded.layers[edit.label_id].layer_key
        loaded.undo_stack.append(edit)
        if len(loaded.undo_stack) > 100:
            loaded.undo_stack.pop(0)
        loaded.redo_stack.clear()
        loaded.revision += 1
        loaded.dirty = True
        loaded.case.status = "修补中"

    def stroke(self, orientation: str, index: int, label_id: int, tool: str, radius: int, points: list[tuple[float, float]], expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        self._check_index(loaded, orientation, index)
        with loaded.lock:
            self._label(loaded, label_id, layer_key)
            mask = loaded.masks[label_id]
            target = self._display_slice(mask, orientation, index)
            before = target.copy()
            expanded: list[tuple[float, float]] = []
            for position, point in enumerate(points):
                if position == 0:
                    expanded.append(point)
                    continue
                x0, y0 = points[position - 1]
                x1, y1 = point
                steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0))))
                expanded.extend((x0 + (x1 - x0) * step / steps, y0 + (y1 - y0) * step / steps) for step in range(1, steps + 1))
            value = tool == "brush"
            for x, y in expanded:
                cx, cy = int(round(x)), int(round(y))
                y0, y1 = max(0, cy - radius), min(target.shape[0], cy + radius + 1)
                x0, x1 = max(0, cx - radius), min(target.shape[1], cx + radius + 1)
                yy, xx = np.ogrid[y0:y1, x0:x1]
                disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2
                target[y0:y1, x0:x1][disk] = value
            after = target.copy()
            self._replace_display_slice(mask, orientation, index, after)
            if not np.array_equal(before, after):
                self._push_edit(loaded, EditRecord(label_id, before, after, orientation, index, tool))
        return self.session_info()

    def polygon(self, orientation: str, index: int, label_id: int, points: list[tuple[float, float]], expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        self._check_index(loaded, orientation, index)
        with loaded.lock:
            self._label(loaded, label_id, layer_key)
            target = self._display_slice(loaded.masks[label_id], orientation, index)
            before = target.copy()
            yy, xx = np.mgrid[: target.shape[0], : target.shape[1]]
            inside = MplPath(points).contains_points(np.column_stack([xx.ravel(), yy.ravel()])).reshape(target.shape)
            target[inside] = True
            after = target.copy()
            self._replace_display_slice(loaded.masks[label_id], orientation, index, after)
            self._push_edit(loaded, EditRecord(label_id, before, after, orientation, index, "polygon"))
        return self.session_info()

    def fill(self, orientation: str, index: int, label_id: int, point: tuple[float, float], expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        self._check_index(loaded, orientation, index)
        with loaded.lock:
            self._label(loaded, label_id, layer_key)
            target = self._display_slice(loaded.masks[label_id], orientation, index)
            x, y = int(round(point[0])), int(round(point[1]))
            if not (0 <= y < target.shape[0] and 0 <= x < target.shape[1]):
                raise ValidationError("填充点超出图像")
            before = target.copy()
            components, _ = ndimage.label(~target)
            component = components[y, x]
            if component:
                target[components == component] = True
            after = target.copy()
            self._replace_display_slice(loaded.masks[label_id], orientation, index, after)
            self._push_edit(loaded, EditRecord(label_id, before, after, orientation, index, "fill"))
        return self.session_info()

    def keep_component(self, orientation: str, index: int, label_id: int, point: tuple[float, float], expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        self._check_index(loaded, orientation, index)
        kept_voxels = 0
        removed_voxels = 0
        with loaded.lock:
            self._label(loaded, label_id, layer_key)
            mask = loaded.masks[label_id]
            z, y, x = self._point_to_voxel(loaded, orientation, index, point)
            if not mask[z, y, x]:
                raise ValidationError("请点击当前 ROI 内需要保留的三维连通区域")
            # First resolve the user's choice on the displayed slice. This is
            # important when two separate bowel cross-sections share the same
            # label on one slice: the clicked 2D component is the seed, and
            # only its 3D connected component is eligible to remain.
            displayed_slice = self._display_slice(mask, orientation, index).copy()
            display_x, display_y = int(round(point[0])), int(round(point[1]))
            slice_components, _ = ndimage.label(
                displayed_slice,
                structure=np.ones((3, 3), dtype=np.uint8),
            )
            selected_slice_component = int(slice_components[display_y, display_x])
            if selected_slice_component == 0:
                raise ValidationError("请点击当前 ROI 内需要保留的三维连通区域")
            coordinates = np.argwhere(mask)
            start = np.maximum(coordinates.min(axis=0) - 1, 0)
            stop = np.minimum(coordinates.max(axis=0) + 2, mask.shape)
            region = tuple(slice(int(begin), int(end)) for begin, end in zip(start, stop))
            before = mask[region].copy()
            components, _ = ndimage.label(before, structure=np.ones((3, 3, 3), dtype=np.uint8))
            local_point = (z - int(start[0]), y - int(start[1]), x - int(start[2]))
            selected_component = int(components[local_point])
            if selected_component == 0:
                raise ValidationError("请点击当前 ROI 内需要保留的三维连通区域")
            after = components == selected_component
            # A 3D component can contain more than one 2D island on the seed
            # slice when segmentation bridges them on another slice. Honor the
            # explicit slice-level choice and remove the other islands there.
            mask[region] = after
            selected_slice = slice_components == selected_slice_component
            displayed_after = self._display_slice(mask, orientation, index)
            displayed_after[displayed_slice & ~selected_slice] = False
            self._replace_display_slice(mask, orientation, index, displayed_after)
            after = mask[region].copy()
            kept_voxels = int(np.count_nonzero(after))
            removed_voxels = int(np.count_nonzero(before) - kept_voxels)
            if removed_voxels:
                self._push_edit(loaded, EditRecord(
                    label_id, before, after.copy(), description="keep_component_3d_from_slice", region=region,
                ))
        result = self.session_info(loaded.case.case_id, loaded.session_token)
        result.update({
            "kept_voxels": kept_voxels,
            "removed_voxels": removed_voxels,
            "selected_slice_voxels": int(np.count_nonzero(selected_slice)),
            "scope": "volume",
        })
        return result

    @staticmethod
    def _threshold_selection(values: np.ndarray, minimum: float | None, maximum: float | None) -> np.ndarray:
        selected = np.ones(values.shape, dtype=bool)
        if minimum is not None:
            selected &= values >= minimum
        if maximum is not None:
            selected &= values <= maximum
        return selected

    def exclude_intensity(self, orientation: str, index: int, label_id: int, scope: str, minimum: float | None, maximum: float | None, expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        self._check_index(loaded, orientation, index)
        if scope not in {"slice", "volume"}:
            raise ValidationError("ROI 强度排除范围无效")
        if minimum is None and maximum is None:
            raise ValidationError("请至少设置一个强度阈值")
        if minimum is not None and not np.isfinite(minimum):
            raise ValidationError("最小强度阈值无效")
        if maximum is not None and not np.isfinite(maximum):
            raise ValidationError("最大强度阈值无效")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValidationError("最小强度不能大于最大强度")

        removed_voxels = 0
        with loaded.lock:
            self._label(loaded, label_id, layer_key)
            mask = loaded.masks[label_id]
            if scope == "slice":
                before = self._display_slice(mask, orientation, index).copy()
                values = self._display_slice(loaded.volume.array_zyx, orientation, index)
                after = before & ~self._threshold_selection(values, minimum, maximum)
                removed_voxels = int(np.count_nonzero(before) - np.count_nonzero(after))
                if removed_voxels:
                    self._replace_display_slice(mask, orientation, index, after)
                    self._push_edit(loaded, EditRecord(
                        label_id, before, after.copy(), orientation, index, "exclude_intensity_slice",
                    ))
            else:
                remove = mask & self._threshold_selection(loaded.volume.array_zyx, minimum, maximum)
                removed_voxels = int(np.count_nonzero(remove))
                if removed_voxels:
                    coordinates = np.argwhere(remove)
                    region = tuple(
                        slice(int(coordinates[:, axis].min()), int(coordinates[:, axis].max()) + 1)
                        for axis in range(3)
                    )
                    before = mask[region].copy()
                    after = before & ~remove[region]
                    mask[region] = after
                    self._push_edit(loaded, EditRecord(
                        label_id, before, after.copy(), description="exclude_intensity_volume", region=region,
                    ))
        result = self.session_info(loaded.case.case_id, loaded.session_token)
        result.update({
            "removed_voxels": removed_voxels,
            "scope": scope,
            "minimum": minimum,
            "maximum": maximum,
        })
        return result

    @staticmethod
    def _trim_region(orientation: str, index: int, direction: str) -> tuple[slice, slice, slice]:
        selected = slice(0, index + 1) if direction == "left" else slice(index, None)
        if orientation == "axial":
            return selected, slice(None), slice(None)
        if orientation == "coronal":
            return slice(None), selected, slice(None)
        return slice(None), slice(None), selected

    def trim_roi(self, orientation: str, index: int, label_id: int, direction: str, expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        self._check_index(loaded, orientation, index)
        if direction not in {"left", "right"}:
            raise ValidationError("ROI范围删除方向无效")
        orientation_name = {"axial": "轴位", "coronal": "冠状位", "sagittal": "矢状位"}[orientation]
        direction_name = "当前层及滑动条左侧" if direction == "left" else "当前层及滑动条右侧"
        with loaded.lock:
            label = self._label(loaded, label_id, layer_key)
            mask = loaded.masks[label_id]
            region = self._trim_region(orientation, index, direction)
            before = mask[region].copy()
            removed_voxels = int(np.count_nonzero(before))
            if removed_voxels:
                after = np.zeros_like(before, dtype=bool)
                mask[region] = after
                self._push_edit(loaded, EditRecord(
                    label_id,
                    before,
                    after,
                    description=f"trim_{direction}",
                    region=region,
                ))
            else:
                loaded.revision += 1
            entry = {
                "orientation": orientation,
                "orientation_name": orientation_name,
                "index": index,
                "slice_number": index + 1,
                "label_id": label_id,
                "label_name": label.display_name or label.name,
                "direction": direction,
                "direction_name": direction_name,
                "removed_voxels": removed_voxels,
                "message": f"{orientation_name}第 {index + 1} 层：{direction_name} ROI 已删除",
            }
            loaded.operation_log.append(entry)
            if len(loaded.operation_log) > 100:
                loaded.operation_log.pop(0)
        return self.session_info()

    def undo(self, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            if not loaded.undo_stack:
                return self.session_info()
            edit = loaded.undo_stack.pop()
            if edit.region is not None:
                loaded.masks[edit.label_id][edit.region] = edit.before
            elif edit.orientation is None:
                loaded.masks[edit.label_id] = edit.before.copy()
            else:
                self._replace_display_slice(loaded.masks[edit.label_id], edit.orientation, int(edit.index), edit.before)
            loaded.redo_stack.append(edit)
            loaded.revision += 1
            loaded.dirty = True
            loaded.case.status = "修补中"
        return self.session_info()

    def redo(self, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            if not loaded.redo_stack:
                return self.session_info()
            edit = loaded.redo_stack.pop()
            if edit.region is not None:
                loaded.masks[edit.label_id][edit.region] = edit.after
            elif edit.orientation is None:
                loaded.masks[edit.label_id] = edit.after.copy()
            else:
                self._replace_display_slice(loaded.masks[edit.label_id], edit.orientation, int(edit.index), edit.after)
            loaded.undo_stack.append(edit)
            loaded.revision += 1
            loaded.dirty = True
            loaded.case.status = "修补中"
        return self.session_info()

    def create_label(self, name: str, display_name: str, color: str, hotkey: str, priority: int, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            editable_source = str(loaded.provenance.get("editable_roi_source", ""))
            if not editable_source:
                raise ConflictError("当前没有可编辑 ROI 文件；请先选择“载入并编辑”")
            next_id = max((label.id for label in loaded.labels), default=0) + 1
            if next_id > 65535:
                raise ConflictError("标签ID已达到上限")
            loaded.labels.append(LabelDefinition(next_id, name, display_name or name, color, hotkey, priority))
            loaded.masks[next_id] = np.zeros(loaded.volume.array_zyx.shape, dtype=bool)
            source_ids = {
                layer.source_label_id for layer in loaded.layers.values()
                if layer.source_file == editable_source
            }
            source_label_id = max(source_ids, default=0) + 1
            loaded.layers[next_id] = RoiLayer(
                runtime_id=next_id,
                source_file=editable_source,
                source_label_id=source_label_id,
                layer_key=self._layer_key(editable_source, source_label_id),
                role="editable",
                editable=True,
            )
            loaded.revision += 1
            loaded.dirty = True
            loaded.case.status = "修补中"
        return self.session_info()

    def _replace_roi_selection(
        self,
        loaded: LoadedCase,
        relative_paths: list[str],
        discard_dirty: bool,
        editable_source: str = "",
        interactive_source: str = "",
    ) -> list[int]:
        if loaded.dirty and not discard_dirty:
            raise ConflictError("当前 ROI 有未保存修改；请先保存，或确认放弃后再切换显示文件")

        resolved: list[tuple[str, Path]] = []
        available_paths = {path.resolve() for path in self._patient_roi_paths(loaded.case)}
        for relative_path in relative_paths:
            path = self._explicit_roi_path(loaded.case, relative_path)
            if path.resolve() not in available_paths:
                raise ValidationError("只能选择当前患者文件夹中列出的 Mask/ROI NIfTI")
            if self._vascular_output_identity_mismatch(loaded.case, path):
                raise ValidationError(f"{path.name} 的来源指纹不属于当前影像序列，已拒绝载入")
            canonical = self._relative_path(path, loaded.case.patient_dir)
            if canonical not in {item[0] for item in resolved}:
                resolved.append((canonical, path))

        selected_files = [relative for relative, _path in resolved]
        if editable_source not in selected_files:
            editable_source = ""
        if interactive_source not in selected_files:
            interactive_source = ""

        old_labels = {layer.layer_key: label for label in loaded.labels for layer in [loaded.layers.get(label.id)] if layer is not None}
        new_labels: list[LabelDefinition] = []
        new_masks: dict[int, np.ndarray] = {}
        new_layers: dict[int, RoiLayer] = {}
        used_ids: set[int] = set()
        interactive_runtime_ids: list[int] = []
        palette = ["#ff3b30", "#34c759", "#007aff", "#ff9500", "#af52de", "#00c7be", "#ffd60a"]

        for file_index, (source_file, path) in enumerate(resolved):
            try:
                source_masks = {
                    int(source_label_id): mask.astype(bool, copy=True)
                    for source_label_id, mask in split_label_map(load_mask(path, loaded.volume)).items()
                }
            except (OSError, ValueError) as exc:
                raise ValidationError(f"ROI 载入失败（{source_file}）：{exc}") from exc
            if not source_masks:
                raise ValidationError(f"所选 ROI 为空：{source_file}")
            base_name = nifti_stem(path)
            is_editable = source_file == editable_source
            role = "interactive_reference" if source_file == interactive_source else ("editable" if is_editable else "reference")
            for source_label_id, mask in sorted(source_masks.items()):
                runtime_id = self._next_runtime_label_id(used_ids, source_label_id)
                used_ids.add(runtime_id)
                layer_key = self._layer_key(source_file, source_label_id)
                previous = old_labels.get(layer_key)
                display_name = base_name if len(source_masks) == 1 else f"{base_name} [{source_label_id}]"
                label = LabelDefinition(
                    runtime_id,
                    safe_name(display_name)[:128],
                    display_name[:128],
                    previous.color if previous is not None else palette[(file_index + source_label_id - 1) % len(palette)],
                    previous.hotkey if previous is not None else "",
                    previous.priority if previous is not None else runtime_id,
                    locked=not is_editable,
                )
                new_labels.append(label)
                new_masks[runtime_id] = mask
                new_layers[runtime_id] = RoiLayer(
                    runtime_id=runtime_id,
                    source_file=source_file,
                    source_label_id=source_label_id,
                    layer_key=layer_key,
                    role=role,
                    editable=is_editable,
                )
                if source_file == interactive_source:
                    interactive_runtime_ids.append(runtime_id)

        loaded.labels = new_labels
        loaded.masks = new_masks
        loaded.layers = new_layers
        loaded.selected_roi_files = selected_files
        loaded.auto_baseline = {
            runtime_id: mask.copy() for runtime_id, mask in new_masks.items()
            if new_layers[runtime_id].editable
        }
        loaded.ai_proposal = {}
        loaded.prompts = []
        loaded.prompt_revision += 1
        loaded.undo_stack.clear()
        loaded.redo_stack.clear()
        loaded.operation_log.clear()

        provenance = dict(loaded.provenance)
        for key in (
            "proposal_labels", "model_output_labels", "empty_model_output_labels",
            "decisions", "interactive_prompt_source",
        ):
            provenance.pop(key, None)
        provenance["selected_roi_files"] = list(selected_files)
        provenance["editable_roi_source"] = editable_source
        provenance["loaded_roi"] = editable_source or (selected_files[0] if len(selected_files) == 1 else "")
        reference_ids = sorted(runtime_id for runtime_id, layer in new_layers.items() if not layer.editable)
        provenance["reference_label_ids"] = reference_ids
        if interactive_source:
            provenance["interactive_reference"] = {
                "relative_path": interactive_source,
                "label_ids": list(interactive_runtime_ids),
            }
            provenance["interactive_reference_label_ids"] = list(interactive_runtime_ids)
            provenance["interactive_reference_pending"] = True
        else:
            provenance.pop("interactive_reference", None)
            provenance.pop("interactive_reference_label_ids", None)
            provenance["interactive_reference_pending"] = False
        loaded.provenance = provenance
        loaded.dirty = False
        loaded.revision += 1
        return interactive_runtime_ids

    def select_roi_files(
        self,
        relative_paths: list[str],
        discard_dirty: bool = False,
        expected_case_id: str | None = None,
        expected_session_token: str | None = None,
        request_id: int = 0,
    ) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with self.state.lock:
            if self.state.loaded is not loaded:
                raise ConflictError("切换 ROI 文件期间病例已改变，本次操作已取消")
        with loaded.lock:
            if request_id and request_id < loaded.last_roi_selection_request_id:
                raise ConflictError("ROI 文件选择已被较新的操作替代")
            editable_source = str(loaded.provenance.get("editable_roi_source", ""))
            interactive_reference = loaded.provenance.get("interactive_reference", {})
            interactive_source = str(interactive_reference.get("relative_path", "")) if isinstance(interactive_reference, dict) else ""
            self._replace_roi_selection(
                loaded,
                relative_paths,
                discard_dirty,
                editable_source=editable_source,
                interactive_source=interactive_source,
            )
            if request_id:
                loaded.last_roi_selection_request_id = request_id
        self._cancel_recovery(loaded, clear=discard_dirty)
        return self.session_info(loaded.case.case_id, loaded.session_token)

    @staticmethod
    def _tumor_batch_is_active() -> bool:
        """Whether the external, write-capable tumor batch controller is running.

        The controller is intentionally outside the web process.  Deleting one
        of its output files while it is publishing could otherwise race an
        atomic replace, so this is a fail-closed check for ``roi_tumor`` only.
        """
        marker = "segment_tumor_rois_candidate2_nninteractive_batch.py"
        try:
            for process in psutil.process_iter(("cmdline",)):
                try:
                    command = " ".join(process.info.get("cmdline") or ())
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                    continue
                if marker in command and "--apply" in command:
                    return True
        except (psutil.Error, OSError):
            # A failed audit must not permit a potentially racing tumor delete.
            return True
        return False

    def delete_patient_roi(
        self,
        relative_path: str,
        confirmed: bool,
        expected_case_id: str | None = None,
        expected_session_token: str | None = None,
        request_id: int = 0,
    ) -> dict[str, Any]:
        """Move exactly one listed ROI NIfTI to the operating-system recycle bin."""
        if not confirmed:
            raise ValidationError("请先确认将 ROI 移至回收站")
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with self.state.lock:
            if self.state.loaded is not loaded:
                raise ConflictError("删除 ROI 期间病例已切换，本次操作已取消")
        with loaded.lock:
            if request_id and request_id < loaded.last_roi_selection_request_id:
                raise ConflictError("ROI 文件操作已被较新的选择替代")
            if loaded.dirty:
                raise ConflictError("当前 ROI 有未保存修改；请先保存或放弃修改后再删除文件")
            path = self._explicit_roi_path(loaded.case, relative_path)
            available_paths = {item.resolve() for item in self._patient_roi_paths(loaded.case)}
            if path.resolve() not in available_paths:
                raise ValidationError("只能删除当前患者文件夹中列出的 ROI NIfTI")
            canonical = self._relative_path(path, loaded.case.patient_dir)
            if canonical.casefold() == "roi_tumor.nii.gz" and self._tumor_batch_is_active():
                raise ConflictError("肿瘤批处理仍在写入；为避免竞争，暂时不能删除 roi_tumor.nii.gz")
            try:
                send2trash(str(path))
            except OSError as exc:
                raise ValidationError(f"ROI 移至回收站失败：{exc}") from exc

            selected = [item for item in loaded.selected_roi_files if item != canonical]
            editable_source = str(loaded.provenance.get("editable_roi_source", ""))
            interactive_reference = loaded.provenance.get("interactive_reference", {})
            interactive_source = str(interactive_reference.get("relative_path", "")) if isinstance(interactive_reference, dict) else ""
            self._replace_roi_selection(
                loaded,
                selected,
                False,
                editable_source=editable_source,
                interactive_source=interactive_source,
            )
            if request_id:
                loaded.last_roi_selection_request_id = request_id
            loaded.warnings.append(f"已将 {canonical} 移至系统回收站")
        self._cancel_recovery(loaded, clear=True)
        session = self.session_info(loaded.case.case_id, loaded.session_token)
        session["deleted_relative_path"] = canonical
        session["moved_to_recycle_bin"] = True
        return session

    def _append_reference_mask(self, loaded: LoadedCase, mask_path: Path) -> list[int]:
        relative_path = self._relative_path(mask_path, loaded.case.patient_dir)
        for existing in loaded.provenance.get("imported_rois", []):
            if existing.get("relative_path") == relative_path:
                target_ids = [int(value) for value in existing.get("target_labels", [])]
                if target_ids and all(label_id in loaded.masks for label_id in target_ids):
                    return target_ids
        try:
            imported_masks = split_label_map(load_mask(mask_path, loaded.volume))
        except (OSError, ValueError) as exc:
            raise ValueError(f"Mask 载入失败：{exc}") from exc
        if not imported_masks:
            raise ValueError("所选 Mask 为空，没有可导入的 ROI")

        palette = ["#ff3b30", "#34c759", "#007aff", "#ff9500", "#af52de", "#00c7be", "#ffd60a"]
        base_name = nifti_stem(mask_path)
        if base_name.lower().startswith("roi_"):
            base_name = base_name[4:]
        imported_label_ids: list[int] = []
        used_ids = {label.id for label in loaded.labels}
        next_id = max(max(used_ids, default=0) + 1, 60000)
        assignments: list[tuple[int, int, np.ndarray]] = []
        for source_label_id, mask in sorted(imported_masks.items()):
            while next_id in used_ids:
                next_id += 1
            if next_id > 65535:
                raise ConflictError("标签ID已达到上限，无法继续导入 Mask")
            target_label_id = next_id
            used_ids.add(target_label_id)
            next_id += 1
            assignments.append((source_label_id, target_label_id, mask.astype(bool, copy=True)))

        for source_label_id, target_label_id, mask in assignments:
            display_name = base_name if len(assignments) == 1 else f"{base_name} [{source_label_id}]"
            color = palette[(target_label_id - 1) % len(palette)]
            loaded.labels.append(LabelDefinition(
                target_label_id,
                safe_name(display_name)[:128],
                display_name[:128],
                color,
                priority=target_label_id,
                locked=True,
            ))
            loaded.masks[target_label_id] = mask.copy()
            imported_label_ids.append(target_label_id)

        reference_ids = {int(value) for value in loaded.provenance.get("reference_label_ids", [])}
        reference_ids.update(imported_label_ids)
        loaded.provenance["reference_label_ids"] = sorted(reference_ids)
        imports = loaded.provenance.setdefault("imported_rois", [])
        imports.append({
            "relative_path": relative_path,
            "source_labels": [source for source, _target, _mask in assignments],
            "target_labels": list(imported_label_ids),
        })
        return imported_label_ids

    def import_mask(self, relative_path: str, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            mask_path = self._explicit_roi_path(loaded.case, relative_path)
            try:
                imported_label_ids = self._append_reference_mask(loaded, mask_path)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            source = self._relative_path(mask_path, loaded.case.patient_dir)
            imported_source_labels = []
            for item in loaded.provenance.get("imported_rois", []):
                if item.get("relative_path") == source:
                    imported_source_labels = [int(value) for value in item.get("source_labels", [])]
            for imported_id, source_label_id in zip(imported_label_ids, imported_source_labels):
                loaded.layers[imported_id] = RoiLayer(
                    imported_id, source, source_label_id, self._layer_key(source, source_label_id),
                    role="reference", editable=False,
                )
            loaded.revision += 1

        session = self.session_info(loaded.case.case_id, loaded.session_token)
        session["imported_label_ids"] = imported_label_ids
        return session

    def load_interactive_reference(self, relative_path: str, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        """Load an existing ROI as a locked comparison layer and nnInteractive seed source."""
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            if relative_path == str(loaded.provenance.get("editable_roi_source", "")):
                raise ConflictError("当前可编辑 ROI 不能同时作为锁定参考；它会自动作为本次半自动的可编辑起点")
            selected = list(loaded.selected_roi_files)
            if relative_path not in selected:
                selected.append(relative_path)
            editable_source = str(loaded.provenance.get("editable_roi_source", ""))
            imported_label_ids = self._replace_roi_selection(
                loaded,
                selected,
                False,
                editable_source=editable_source,
                interactive_source=relative_path,
            )

        session = self.session_info(loaded.case.case_id, loaded.session_token)
        session["imported_label_ids"] = imported_label_ids
        return session

    def load_editable_roi(self, relative_path: str, discard_dirty: bool = False, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with self.state.lock:
            if self.state.loaded is not loaded:
                raise ConflictError("载入可编辑 ROI 期间病例已切换，本次操作已取消")

        with loaded.lock:
            selected = [*loaded.selected_roi_files]
            if relative_path not in selected:
                selected.append(relative_path)
            interactive_reference = loaded.provenance.get("interactive_reference", {})
            interactive_source = str(interactive_reference.get("relative_path", "")) if isinstance(interactive_reference, dict) else ""
            self._replace_roi_selection(
                loaded,
                selected,
                discard_dirty,
                editable_source=relative_path,
                interactive_source=interactive_source if interactive_source != relative_path else "",
            )
            roi_path = self._explicit_roi_path(loaded.case, relative_path)
            loaded.case.status = "已完成" if is_completed_roi_path(loaded.case, roi_path) else "待审核"
            warning = f"已将 {relative_path} 载入为唯一可编辑 ROI；其他所选文件保持只读"
            if warning not in loaded.warnings:
                loaded.warnings.append(warning)

        self._cancel_recovery(loaded, clear=discard_dirty)
        return self.session_info(loaded.case.case_id, loaded.session_token)

    def lock_label(self, label_id: int, locked: bool, expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            layer = self._resolve_layer(loaded, label_id, layer_key)
            label = next((item for item in loaded.labels if item.id == label_id), None)
            if label is None:
                raise NotFoundError(f"标签 {label_id} 不存在")
            reference_ids = {int(value) for value in loaded.provenance.get("reference_label_ids", [])}
            if ((layer is not None and not layer.editable) or label_id in reference_ids) and not locked:
                raise ConflictError("既往 ROI 是只读对比图层，不能解锁或写入")
            label.locked = locked
            loaded.revision += 1
            loaded.dirty = True
            loaded.case.status = "修补中"
        return self.session_info()

    def set_label_color(self, label_id: int, color: str, expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            self._resolve_layer(loaded, label_id, layer_key)
            label = next((item for item in loaded.labels if item.id == label_id), None)
            if label is None:
                raise NotFoundError(f"标签 {label_id} 不存在")
            label.color = color.lower()
            loaded.revision += 1
        return self.session_info()

    @staticmethod
    def _point_to_voxel(loaded: LoadedCase, orientation: str, index: int, point: tuple[float, float]) -> tuple[int, int, int]:
        x, y = int(round(point[0])), int(round(point[1]))
        z_count, y_count, x_count = loaded.volume.array_zyx.shape
        if orientation == "axial":
            voxel = (index, y, x)
        elif orientation == "coronal":
            voxel = (z_count - 1 - y, index, x)
        else:
            voxel = (z_count - 1 - y, x, index)
        z, vy, vx = voxel
        if not (0 <= z < z_count and 0 <= vy < y_count and 0 <= vx < x_count):
            raise ValidationError("提示点超出图像")
        return voxel

    def add_prompt(self, orientation: str, index: int, kind: str, points: list[tuple[float, float]], radius: int = 1, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        self._check_index(loaded, orientation, index)
        if not 1 <= int(radius) <= 50:
            raise ValidationError("提示点半径必须在 1 到 50 像素之间")
        with loaded.lock:
            self._invalidate_interactive_proposal(loaded, "prompt_changed")
            voxels = [self._point_to_voxel(loaded, orientation, index, point) for point in points]
            if kind in {"positive", "negative"}:
                prompt = {
                    "kind": "point",
                    "voxel_zyx": list(voxels[0]),
                    "orientation": orientation,
                    "radius": int(radius),
                    "include": kind == "positive",
                }
            elif kind == "box":
                if len(voxels) < 2:
                    raise ValidationError("框提示需要起点和终点")
                prompt = {"kind": "box", "start_zyx": list(voxels[0]), "end_zyx": list(voxels[-1]), "include": True}
            elif kind in {"scribble_positive", "scribble_negative"}:
                prompt = {"kind": "scribble", "voxels_zyx": [list(value) for value in dict.fromkeys(voxels)], "include": kind == "scribble_positive"}
            else:
                if len(voxels) < 3:
                    raise ValidationError("套索至少需要三个点")
                prompt = {"kind": "lasso", "orientation": orientation, "points_zyx": [list(value) for value in voxels], "include": True}
            loaded.prompts.append(prompt)
            loaded.prompt_revision += 1
            loaded.revision += 1
        return self.session_info()

    @staticmethod
    def _invalidate_interactive_proposal(loaded: LoadedCase, decision: str) -> None:
        """Discard only stale nnInteractive output, never an automatic baseline proposal."""
        model_id = str(loaded.provenance.get("model_id", "")).lower()
        if not model_id.startswith("nninteractive"):
            return
        declared = {int(label_id) for label_id in loaded.provenance.get("proposal_labels", [])}
        decisions = loaded.provenance.setdefault("decisions", {})
        for label_id in declared | set(loaded.ai_proposal):
            decisions[str(label_id)] = decision
        loaded.ai_proposal = {}

    def undo_prompt(self, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            if loaded.prompts:
                loaded.prompts.pop()
            self._invalidate_interactive_proposal(loaded, "prompt_undone")
            loaded.prompt_revision += 1
            loaded.revision += 1
        return self.session_info()

    def reset_prompts(self, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            loaded.prompts = []
            self._invalidate_interactive_proposal(loaded, "interaction_reset")
            loaded.prompt_revision += 1
            loaded.revision += 1
        return self.session_info()

    @staticmethod
    def _apply_prediction(loaded: LoadedCase, result: PredictionResult, interactive: bool) -> None:
        reference_label_ids: list[int] = []
        for value in loaded.provenance.get("reference_label_ids", []):
            try:
                reference_label_ids.append(int(value))
            except (TypeError, ValueError):
                continue
        imported_rois = [
            dict(item) for item in loaded.provenance.get("imported_rois", [])
            if isinstance(item, dict)
        ]
        interactive_reference = dict(loaded.provenance.get("interactive_reference", {}))
        interactive_reference_label_ids = [
            int(value) for value in loaded.provenance.get("interactive_reference_label_ids", [])
            if str(value).isdigit()
        ]
        interactive_reference_pending = bool(loaded.provenance.get("interactive_reference_pending", False))
        interactive_prompt_source = str(loaded.provenance.get("interactive_prompt_source", ""))
        prepared_masks: dict[int, np.ndarray] = {}
        editable_layers_by_source = {
            layer.source_label_id: layer for layer in loaded.layers.values() if layer.editable
        }
        editable_source = str(loaded.provenance.get("editable_roi_source", ""))
        if loaded.layers and not editable_layers_by_source:
            raise ConflictError("当前没有可编辑 ROI 文件；模型结果未写入任何只读图层")
        expected_shape = loaded.volume.array_zyx.shape
        for raw_label_id, raw_mask in result.masks.items():
            source_label_id = int(raw_label_id)
            mask = np.asarray(raw_mask)
            if mask.shape != expected_shape:
                raise ValueError(f"模型标签 {source_label_id} 的 shape {mask.shape} 与影像 {expected_shape} 不一致")
            target_layer = editable_layers_by_source.get(source_label_id)
            if target_layer is None and loaded.layers:
                used_ids = set(loaded.masks)
                runtime_id = WorkbenchService._next_runtime_label_id(used_ids, source_label_id)
                target_layer = RoiLayer(
                    runtime_id=runtime_id,
                    source_file=editable_source,
                    source_label_id=source_label_id,
                    layer_key=WorkbenchService._layer_key(editable_source, source_label_id),
                    role="result",
                    editable=True,
                )
                loaded.layers[runtime_id] = target_layer
                editable_layers_by_source[source_label_id] = target_layer
            runtime_id = target_layer.runtime_id if target_layer is not None else source_label_id
            prepared_masks[runtime_id] = mask.astype(bool, copy=True)

        model_labels = result.provenance.get("labels", [])
        if model_labels:
            definitions = {label.id: label for label in labels_from_rows(model_labels)}
            reconciled = []
            for label in loaded.labels:
                layer = loaded.layers.get(label.id)
                source_label_id = layer.source_label_id if layer is not None else label.id
                replacement = definitions.get(source_label_id) if layer is None or layer.editable else None
                if replacement is not None:
                    replacement.id = label.id
                    replacement.locked = label.locked
                    reconciled.append(replacement)
                else:
                    reconciled.append(label)
            loaded.labels = reconciled
        for label_id, mask in prepared_masks.items():
            if not any(label.id == label_id for label in loaded.labels):
                layer = loaded.layers.get(label_id)
                source_label_id = layer.source_label_id if layer is not None else label_id
                loaded.labels.append(LabelDefinition(label_id, f"label_{source_label_id}", f"Label {source_label_id}"))
            loaded.masks.setdefault(label_id, np.zeros_like(mask, dtype=bool))

        locked_ids = {label.id for label in loaded.labels if label.locked}
        applied: dict[int, np.ndarray] = {}
        empty_outputs: list[int] = []
        changed = False
        for label_id, mask in prepared_masks.items():
            if label_id in locked_ids:
                loaded.warnings.append(f"标签 {label_id} 已锁定，模型结果未写入")
                continue
            after = mask.copy()
            if not np.any(after):
                empty_outputs.append(int(label_id))
                warning = f"模型标签 {label_id} 返回空 ROI，未覆盖当前可编辑 ROI"
                if warning not in loaded.warnings:
                    loaded.warnings.append(warning)
                continue
            before = loaded.masks[label_id].copy()
            loaded.masks[label_id] = after.copy()
            applied[label_id] = after.copy()
            if label_id in loaded.layers:
                loaded.layers[label_id].role = "result"
            if not np.array_equal(before, after):
                WorkbenchService._push_edit(
                    loaded,
                    EditRecord(label_id, before, after.copy(), description="interactive_model" if interactive else "automatic_model"),
                )
                changed = True

        if interactive:
            for label_id, mask in applied.items():
                loaded.auto_baseline.setdefault(label_id, mask.copy())
        elif applied:
            loaded.auto_baseline = applied
        loaded.ai_proposal = {}
        for warning in result.warnings:
            if warning not in loaded.warnings:
                loaded.warnings.append(warning)
        working_layer_kind = str(loaded.provenance.get("working_layer_kind", ""))
        loaded.provenance = {
            **result.provenance,
            "model_id": result.model_id,
            "model_version": result.model_version,
            "warnings": list(result.warnings),
            "proposal_labels": [],
            "model_output_labels": sorted(int(label_id) for label_id in applied),
            "empty_model_output_labels": sorted(empty_outputs),
            "selected_roi_files": list(loaded.selected_roi_files),
            "editable_roi_source": editable_source,
            "loaded_roi": editable_source,
        }
        if working_layer_kind:
            loaded.provenance["working_layer_kind"] = working_layer_kind
        if reference_label_ids:
            loaded.provenance["reference_label_ids"] = sorted(set(reference_label_ids))
        if imported_rois:
            loaded.provenance["imported_rois"] = imported_rois
        if interactive_reference:
            loaded.provenance["interactive_reference"] = interactive_reference
        if interactive_reference_label_ids:
            loaded.provenance["interactive_reference_label_ids"] = interactive_reference_label_ids
            loaded.provenance["interactive_reference_pending"] = (
                False if interactive else interactive_reference_pending
            )
        if interactive_prompt_source:
            loaded.provenance["interactive_prompt_source"] = interactive_prompt_source
        loaded.case.status = "修补中"
        if not changed:
            loaded.revision += 1

    def start_auto(self, model_name: str, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        engine = self.models.get(model_name)
        if engine is None:
            raise NotFoundError("自动模型不存在")
        with loaded.lock:
            if not any(layer.editable for layer in loaded.layers.values()):
                self._create_new_working_layer(loaded, 1, "new_auto")

        def operation(entry: TaskEntry) -> None:
            result = engine.predict(loaded.case, loaded.volume)
            with self.state.lock:
                if self.state.loaded is not loaded:
                    entry.status = "cancelled"
                    entry.message = "病例已切换，结果已安全丢弃"
                    return
            with loaded.lock:
                if entry.status in {"cancelled", "cancelling"}:
                    entry.message = "推理已取消，结果已安全丢弃"
                    return
                self._apply_prediction(loaded, result, False)

        return self.state.tasks.submit("auto", loaded.case.case_id, engine, operation).to_json()

    def _create_new_working_layer(self, loaded: LoadedCase, requested_label_id: int, kind: str) -> RoiLayer:
        """Create an in-memory target without assigning it to a patient ROI file.

        This layer deliberately has no patient-file source.  It becomes a NIfTI
        only after the user explicitly saves, so automatic or semi-automatic
        tumor work can never overwrite an existing ROI.
        """
        if kind not in {"new_auto", "new_interactive"}:
            raise ValueError(f"未知的新建工作层类型：{kind}")
        runtime_id = self._next_runtime_label_id(set(loaded.masks), requested_label_id)
        source_file = f"@working/{kind}-{uuid.uuid4().hex}.nii.gz"
        source_label_id = int(requested_label_id)
        display_name = "新建自动肿瘤 ROI" if kind == "new_auto" else "新建半自动肿瘤 ROI"
        label = LabelDefinition(runtime_id, "ROI", display_name, "#ff3b30", "1")
        layer = RoiLayer(
            runtime_id=runtime_id,
            source_file=source_file,
            source_label_id=source_label_id,
            layer_key=self._layer_key(source_file, source_label_id),
            role=kind,
            editable=True,
        )
        # Reference layers are deliberately retained.  A new semi-automatic
        # result must coexist with them, never replace them or inherit their
        # label identity.
        loaded.labels.append(label)
        loaded.masks[runtime_id] = np.zeros(loaded.volume.array_zyx.shape, dtype=bool)
        loaded.layers[runtime_id] = layer
        loaded.auto_baseline = {
            existing_id: mask for existing_id, mask in loaded.auto_baseline.items()
            if existing_id in loaded.layers and loaded.layers[existing_id].editable
        }
        loaded.ai_proposal = {}
        loaded.undo_stack.clear()
        loaded.redo_stack.clear()
        loaded.operation_log.clear()
        provenance = dict(loaded.provenance)
        provenance["selected_roi_files"] = list(loaded.selected_roi_files)
        provenance["editable_roi_source"] = source_file
        provenance["loaded_roi"] = ""
        provenance["reference_label_ids"] = sorted(
            existing_id for existing_id, existing_layer in loaded.layers.items()
            if not existing_layer.editable
        )
        provenance["working_layer_kind"] = kind
        loaded.provenance = provenance
        loaded.revision += 1
        operation_name = "自动肿瘤分割" if kind == "new_auto" else "半自动肿瘤分割"
        notice = f"未选择可编辑 ROI：已新建{operation_name}工作层；保存前不会写入任何患者 ROI 文件"
        if notice not in loaded.warnings:
            loaded.warnings.append(notice)
        return layer

    def _create_new_interactive_working_layer(self, loaded: LoadedCase, requested_label_id: int) -> RoiLayer:
        return self._create_new_working_layer(loaded, requested_label_id, "new_interactive")

    def start_interactive(self, label_id: int, expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            editable_layers = [layer for layer in loaded.layers.values() if layer.editable]
            if not editable_layers:
                if layer_key:
                    raise ConflictError("ROI 图层身份已变化；请刷新后重新运行半自动分割")
                target_layer = self._create_new_interactive_working_layer(loaded, label_id)
                label_id = target_layer.runtime_id
            else:
                target_layer = self._resolve_layer(loaded, label_id, layer_key)
            self._label(loaded, label_id, layer_key)
            prompts = list(loaded.prompts)
            prompt_revision = loaded.prompt_revision
            prompt_source = "explicit_prompt"
            initial_mask: np.ndarray | None = None
            reference_ids: set[int] = set()
            for value in loaded.provenance.get("interactive_reference_label_ids", []):
                try:
                    reference_id = int(value)
                except (TypeError, ValueError):
                    continue
                if reference_id in loaded.masks:
                    reference_ids.add(reference_id)
            combined_reference = None
            if reference_ids:
                combined_reference = np.zeros_like(next(iter(loaded.masks.values())), dtype=bool)
                for reference_id in reference_ids:
                    combined_reference |= loaded.masks[reference_id]
                if not np.any(combined_reference):
                    combined_reference = None
            seed_mask = loaded.masks.get(label_id)
            use_fresh_reference = bool(loaded.provenance.get("interactive_reference_pending", False))
            if use_fresh_reference and combined_reference is not None:
                initial_mask = combined_reference
                prompt_source = "interactive_reference"
            elif seed_mask is not None and np.any(seed_mask):
                initial_mask = seed_mask.astype(bool, copy=True)
                prompt_source = "editable_roi"
            elif combined_reference is not None:
                initial_mask = combined_reference
                prompt_source = "interactive_reference"
            if initial_mask is not None:
                loaded.provenance["interactive_prompt_source"] = prompt_source
                loaded.revision += 1
        if not prompts and initial_mask is None:
            raise ValidationError("当前没有可用于 nnInteractive 的 ROI 或提示；请先载入可编辑 ROI、载入参考 ROI，或使用 AI 套索/框提示")
        model_label_id = target_layer.source_label_id if target_layer is not None else label_id
        if initial_mask is None:
            engine = NnInteractivePromptEngine(NnInteractiveClient(project_root=self.state.project_root), prompts, model_label_id)
        else:
            engine = NnInteractivePromptEngine(NnInteractiveClient(project_root=self.state.project_root), prompts, model_label_id, initial_mask)

        def operation(entry: TaskEntry) -> None:
            result = engine.predict(loaded.case, loaded.volume)
            with self.state.lock:
                if self.state.loaded is not loaded:
                    entry.status = "cancelled"
                    entry.message = "病例已切换，结果已安全丢弃"
                    return
            with loaded.lock:
                if entry.status in {"cancelled", "cancelling"} or loaded.prompt_revision != prompt_revision:
                    entry.status = "cancelled"
                    entry.message = "提示已改变，旧推理结果已安全丢弃"
                    return
                self._apply_prediction(loaded, result, True)

        return self.state.tasks.submit("interactive", loaded.case.case_id, engine, operation).to_json()

    def task(self, task_id: str, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        self.require_loaded(expected_case_id, expected_session_token)
        entry = self.state.tasks.get(task_id)
        if entry is None:
            raise NotFoundError("任务不存在")
        if expected_case_id is not None and entry.case_id != expected_case_id:
            raise ConflictError("任务不属于当前页面病例")
        return entry.to_json()

    def cancel_task(self, task_id: str, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        self.require_loaded(expected_case_id, expected_session_token)
        entry = self.state.tasks.get(task_id)
        if entry is None:
            raise NotFoundError("任务不存在")
        if expected_case_id is not None and entry.case_id != expected_case_id:
            raise ConflictError("任务不属于当前页面病例")
        entry = self.state.tasks.cancel(task_id)
        return entry.to_json()

    def merge_proposal(self, label_id: int, operation: str, expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            self._resolve_layer(loaded, label_id, layer_key)
            label = next((item for item in loaded.labels if item.id == label_id), None)
            if label is None:
                raise NotFoundError(f"标签 {label_id} 不存在")
            if label.locked and operation != "reject":
                raise ConflictError("当前标签已锁定，不能合并AI候选")
            decisions = loaded.provenance.setdefault("decisions", {})
            if operation == "reject":
                declared = {int(value) for value in loaded.provenance.get("proposal_labels", [])}
                if label_id not in loaded.ai_proposal and label_id not in declared:
                    raise NotFoundError("当前标签没有待处理候选")
                loaded.ai_proposal.pop(label_id, None)
                decisions[str(label_id)] = "rejected"
                loaded.revision += 1
                return self.session_info()
            if operation == "restore_baseline":
                proposal = loaded.auto_baseline.get(label_id)
                if proposal is None:
                    raise NotFoundError(f"标签 {label_id} 没有自动基线")
            else:
                proposal = loaded.ai_proposal.get(label_id)
                if proposal is None:
                    raise NotFoundError(f"标签 {label_id} 没有可合并的AI候选")
            current = loaded.masks[label.id]
            before = current.copy()
            if operation == "add":
                current |= proposal
            elif operation == "remove":
                current &= ~proposal
            elif operation == "local_replace":
                coordinates = np.argwhere(proposal)
                if not len(coordinates):
                    raise ValidationError("候选为空，不能局部替换")
                start = np.maximum(coordinates.min(axis=0) - 3, 0)
                stop = np.minimum(coordinates.max(axis=0) + 4, proposal.shape)
                region = tuple(slice(int(a), int(b)) for a, b in zip(start, stop))
                current[region] = proposal[region]
            else:
                current[:] = proposal
            loaded.ai_proposal.pop(label_id, None)
            decisions[str(label_id)] = operation
            self._push_edit(loaded, EditRecord(label_id, before, current.copy(), description=operation))
        return self.session_info()

    def roi_slices(self, orientation: str, label_id: int, expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> list[int]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            self._resolve_layer(loaded, label_id, layer_key)
            mask = loaded.masks.get(label_id)
            if mask is None:
                raise NotFoundError("标签不存在")
            if orientation == "axial":
                active = np.any(mask, axis=(1, 2))
            elif orientation == "coronal":
                active = np.any(mask, axis=(0, 2))
            else:
                active = np.any(mask, axis=(0, 1))
            return [int(value) for value in np.flatnonzero(active)]

    def roi_mesh(self, label_id: int, expected_case_id: str | None = None, expected_session_token: str | None = None, layer_key: str = "") -> dict[str, Any]:
        """Return a read-only physical-space surface snapshot of the current label mask."""
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            layer = self._resolve_layer(loaded, label_id, layer_key)
            label = next((item for item in loaded.labels if item.id == label_id), None)
            if label is None:
                raise NotFoundError(f"标签 {label_id} 不存在")
            mask = loaded.masks.get(label_id)
            if mask is None:
                raise ValidationError("当前标签没有可渲染的 ROI；请先勾画或载入 ROI")
            occupied_z = np.flatnonzero(mask.any(axis=(1, 2)))
            if not len(occupied_z):
                raise ValidationError("当前标签没有可渲染的 ROI；请先勾画或载入 ROI")
            occupied_y = np.flatnonzero(mask.any(axis=(0, 2)))
            occupied_x = np.flatnonzero(mask.any(axis=(0, 1)))
            z0, z1 = int(occupied_z[0]), int(occupied_z[-1]) + 1
            y0, y1 = int(occupied_y[0]), int(occupied_y[-1]) + 1
            x0, x1 = int(occupied_x[0]), int(occupied_x[-1]) + 1
            cropped = np.asarray(mask[z0:z1, y0:y1, x0:x1], dtype=bool).copy()
            revision = int(loaded.revision)
            spacing_xyz = tuple(float(value) for value in loaded.volume.geometry.spacing_xyz)
            label_name = label.display_name or label.name
            label_color = label.color

        voxel_count = int(np.count_nonzero(cropped))
        padded = np.pad(cropped.astype(np.uint8, copy=False), 1, mode="constant")
        spacing_zyx = (spacing_xyz[2], spacing_xyz[1], spacing_xyz[0])
        # Vascular masks are sparse even when their bounding boxes are large.
        # Starting from a bbox-derived coarse step made thin branches jagged or
        # disappear in 3D. First render at native voxel sampling; only fall back
        # to coarser steps when the actual triangle count exceeds the cap.
        step_size = 1
        maximum_step = min(self.MAX_MESH_STEP, max(1, min(padded.shape) - 1))
        step_size = min(step_size, maximum_step)

        while True:
            try:
                vertices_zyx, faces, normals_zyx, _values = measure.marching_cubes(
                    padded,
                    level=0.5,
                    spacing=spacing_zyx,
                    step_size=step_size,
                    allow_degenerate=False,
                    method="lewiner",
                )
            except ValueError as exc:
                raise ValidationError(f"当前 ROI 无法生成三维表面：{exc}") from exc
            if len(faces) <= self.MAX_MESH_TRIANGLES or step_size >= maximum_step:
                break
            step_size += 1

        if len(faces) > self.MAX_MESH_TRIANGLES:
            raise ValidationError("当前 ROI 表面过于复杂；请先清理小碎片或缩小 ROI 后重试")

        offset_zyx = np.asarray((z0 - 1, y0 - 1, x0 - 1), dtype=np.float32) * np.asarray(spacing_zyx, dtype=np.float32)
        vertices_zyx = vertices_zyx + offset_zyx
        vertices_xyz = vertices_zyx[:, [2, 1, 0]].astype(np.float32, copy=False)
        normals_xyz = normals_zyx[:, [2, 1, 0]].astype(np.float32, copy=False)
        bounds_min = vertices_xyz.min(axis=0)
        bounds_max = vertices_xyz.max(axis=0)
        return {
            "label_id": int(label_id),
            "layer_key": layer.layer_key if layer is not None else "",
            "source_file": layer.source_file if layer is not None else "",
            "source_label_id": layer.source_label_id if layer is not None else int(label_id),
            "label_name": label_name,
            "label_color": label_color,
            "revision": revision,
            "coordinate_system": "display_physical_xyz",
            "spacing_xyz": [round(value, 6) for value in spacing_xyz],
            "voxel_count": voxel_count,
            "vertex_count": int(len(vertices_xyz)),
            "triangle_count": int(len(faces)),
            "mesh_step": int(step_size),
            "downsampled": bool(step_size > 1),
            "bounds_mm": {
                "min": np.round(bounds_min, 4).tolist(),
                "max": np.round(bounds_max, 4).tolist(),
            },
            "vertices": np.round(vertices_xyz, 4).reshape(-1).tolist(),
            "normals": np.round(normals_xyz, 5).reshape(-1).tolist(),
            "indices": faces.astype(np.uint32, copy=False).reshape(-1).tolist(),
        }


    @classmethod
    def _vascular_model_spec(cls, model_key: str) -> dict[str, Any]:
        key = str(model_key or cls.VASCULAR_HEPATIC_MODEL).strip().lower()
        specs: dict[str, dict[str, Any]] = {
            cls.VASCULAR_HEPATIC_MODEL: {
                "model_key": cls.VASCULAR_HEPATIC_MODEL,
                "model_name": "肝动脉分割（原功能）",
                "algorithm": "HA专用nnU-Net → 条件式厚层轴位恢复 → 三平面MIP远端修补 → 肝脏约束HU生长 → 连续性平滑",
                "pipeline_version": HepaticArteryPipeline.PIPELINE_VERSION,
                "output_filename": HepaticArteryPipeline.OUTPUT_FILENAME,
                "model_scope": "肝动脉及肝内可见分支的专用二值分割",
                "input_contract": "腹部动脉期增强 CT；厚层数据会启用恢复策略并要求重点复核",
                "total_stages": HepaticArteryPipeline.TOTAL_STAGES,
                "completion_label": "肝动脉分割",
            },
            cls.VASCULAR_ABDOMINAL_MODEL: {
                "model_key": cls.VASCULAR_ABDOMINAL_MODEL,
                "model_name": "全腹动脉分割（新增）",
                "algorithm": "BVM 2026 SkeletonRecall nnU-Net → 五折 ensemble + TTA → 二值/几何/连通性/骨架 QC",
                "pipeline_version": AbdominalArteryPipeline.PIPELINE_VERSION,
                "output_filename": AbdominalArteryPipeline.OUTPUT_FILENAME,
                "model_scope": "全腹动脉二值树（主动脉、腹腔干、SMA、IMA及可见分支）",
                "input_contract": "薄层动脉期腹部增强 CT；非动脉期或厚层结果必须重点复核",
                "total_stages": AbdominalArteryPipeline.TOTAL_STAGES,
                "completion_label": "全腹动脉分割",
            },
        }
        if key not in specs:
            raise ValidationError(f"未知血管模型：{model_key}")
        return specs[key]

    def _vascular_pipeline_for(self, model_key: str):
        spec = self._vascular_model_spec(model_key)
        if spec["model_key"] == self.VASCULAR_HEPATIC_MODEL:
            return self._vascular_pipeline_factory()
        return self._abdominal_vascular_pipeline_factory()

    @staticmethod
    def _hepatic_output_is_protected(case: CaseRecord, pipeline: Any, spec: dict[str, Any]) -> bool:
        """Protect a legacy roi.nii.gz unless the real HA pipeline can verify it."""
        if spec.get("model_key") != WorkbenchService.VASCULAR_HEPATIC_MODEL:
            return False
        destination = case.patient_dir / str(spec["output_filename"])
        if not destination.is_file() or not isinstance(pipeline, HepaticArteryPipeline):
            return False
        return not pipeline._is_verified_pipeline_output(case, destination)

    @staticmethod
    def _hepatic_output_protection_message(case: CaseRecord) -> str:
        return (
            f"{case.patient_dir.name} 存在未验证的 roi.nii.gz；为保护人工或肿瘤 ROI，已跳过肝动脉覆盖。"
            "请保留/改名该文件，或确认其为本管线当前 CT 的结果后再重试。"
        )

    @staticmethod
    def _vascular_patient_groups(cases: list[CaseRecord]) -> list[tuple[Path, list[CaseRecord]]]:
        groups: dict[str, tuple[Path, list[CaseRecord]]] = {}
        for case in cases:
            patient_dir = case.patient_dir.resolve()
            key = str(patient_dir).casefold()
            if key not in groups:
                groups[key] = (patient_dir, [])
            groups[key][1].append(case)
        return sorted(groups.values(), key=lambda item: str(item[0]).casefold())

    def _active_vascular_task(self) -> TaskEntry | None:
        with self._vascular_lock:
            task_id = self._vascular_active_task_id
            entry = self.state.tasks.get(task_id) if task_id else None
            if entry is None or entry.status in {"completed", "completed_with_failures", "failed", "cancelled"}:
                self._vascular_active_task_id = ""
                return None
            return entry

    def _claim_vascular_slot(self) -> None:
        with self._vascular_lock:
            if self._vascular_root_switch_reserved:
                raise ConflictError("数据根目录正在切换；请扫描完成后再启动血管任务")
            if self._vascular_slot_reserved:
                raise ConflictError("已有血管任务正在启动")
            task_id = self._vascular_active_task_id
            active = self.state.tasks.get(task_id) if task_id else None
            if active is not None and active.status not in {
                "completed", "completed_with_failures", "failed", "cancelled",
            }:
                raise ConflictError(f"已有血管任务正在运行：{active.message}")
            self._vascular_active_task_id = ""
            self._vascular_slot_reserved = True

    def _activate_vascular_slot(self, task_id: str) -> None:
        with self._vascular_lock:
            self._vascular_active_task_id = task_id
            self._vascular_slot_reserved = False

    def _abort_vascular_claim(self) -> None:
        with self._vascular_lock:
            self._vascular_slot_reserved = False

    def _release_vascular_slot(self, task_id: str) -> None:
        with self._vascular_lock:
            if self._vascular_active_task_id == task_id:
                self._vascular_active_task_id = ""

    @staticmethod
    def _matching_vascular_manifest(
        case: CaseRecord,
        output_path: Path,
        *,
        allow_legacy_without_source: bool = False,
    ) -> dict[str, Any]:
        if not output_path.is_file():
            return {}
        manifest_dir = case.patient_dir / ".roi-workbench" / "vascular_runs"
        if not manifest_dir.is_dir():
            return {}
        try:
            candidates = sorted(
                (path for path in manifest_dir.glob("*.json") if path.is_file()),
                key=lambda path: path.stat().st_mtime_ns,
                reverse=True,
            )
            output_hash = file_hash(output_path).lower()
            expected_output = str(output_path.resolve()).casefold()
            expected_patient = str(case.patient_dir.resolve()).casefold()
        except OSError:
            return {}
        current_source_hash: str | None = None
        for manifest_path in candidates:
            try:
                if manifest_path.stat().st_size > 10 * 1024 * 1024:
                    continue
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest_output = Path(str(payload.get("output_path", ""))).resolve()
                if str(manifest_output).casefold() != expected_output:
                    continue
                manifest_patient = Path(str(payload.get("patient_dir", ""))).resolve()
                if str(manifest_patient).casefold() != expected_patient:
                    continue
                if str(payload.get("output_sha256", "")).lower() != output_hash:
                    continue
                manifest_source_hash = str(payload.get("source_image_sha256", "")).lower()
                if manifest_source_hash:
                    if current_source_hash is None:
                        current_source_hash = case_image_hash(case).lower()
                    if not current_source_hash or manifest_source_hash != current_source_hash:
                        continue
                elif not allow_legacy_without_source:
                    continue
                quality_status = str(payload.get("quality_status", "standard"))
                review_required = bool(payload.get("review_required", False))
                quality_note = str(payload.get("quality_note", ""))
                if not manifest_source_hash:
                    review_required = True
                    if quality_status == "standard":
                        quality_status = "legacy_unverified"
                    legacy_note = "该 ROI 的旧版运行清单缺少输入影像指纹，需重点复核。"
                    quality_note = f"{quality_note} {legacy_note}".strip()
                return {
                    "processing_mode": str(payload.get("processing_mode", "standard")),
                    "quality_status": quality_status,
                    "review_required": review_required,
                    "quality_note": quality_note,
                    "backup_path": str(payload.get("backup_path", "")),
                    "manifest_path": str(manifest_path),
                    "source_identity_verified": bool(manifest_source_hash),
                    "source_identity_status": (
                        "verified" if manifest_source_hash else "legacy_unverified"
                    ),
                    "output_identity_mismatch": False,
                    "output_sha256": output_hash,
                }
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        return {}

    @staticmethod
    def _vascular_manifest_has_conflicting_source(case: CaseRecord, output_path: Path) -> bool:
        """Return true only for a modern manifest that proves the ROI came from another CT."""
        if not output_path.is_file():
            return False
        manifest_dir = case.patient_dir / ".roi-workbench" / "vascular_runs"
        if not manifest_dir.is_dir():
            return False
        try:
            candidates = [path for path in manifest_dir.glob("*.json") if path.is_file()]
            output_hash = file_hash(output_path).lower()
            expected_output = str(output_path.resolve()).casefold()
            expected_patient = str(case.patient_dir.resolve()).casefold()
            current_source_hash = case_image_hash(case).lower()
        except OSError:
            return False
        for manifest_path in candidates:
            try:
                if manifest_path.stat().st_size > 10 * 1024 * 1024:
                    continue
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    continue
                manifest_output = Path(str(payload.get("output_path", ""))).resolve()
                manifest_patient = Path(str(payload.get("patient_dir", ""))).resolve()
                if str(manifest_output).casefold() != expected_output:
                    continue
                if str(manifest_patient).casefold() != expected_patient:
                    continue
                if str(payload.get("output_sha256", "")).lower() != output_hash:
                    continue
                manifest_source_hash = str(payload.get("source_image_sha256", "")).lower()
                if manifest_source_hash and manifest_source_hash != current_source_hash:
                    return True
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        return False

    def vascular_status(self, model_key: str = VASCULAR_HEPATIC_MODEL) -> dict[str, Any]:
        spec = self._vascular_model_spec(model_key)
        with self.state.lock:
            cases = list(self.state.cases)
            loaded = self.state.loaded
            data_root = self.state.data_root
        groups = self._vascular_patient_groups(cases)
        ambiguous = [
            {"patient_dir": str(patient_dir), "case_ids": [case.case_id for case in patient_cases]}
            for patient_dir, patient_cases in groups if len(patient_cases) != 1
        ]
        active = self._active_vascular_task()
        current_output = None
        target_output = None
        if loaded is not None:
            target_output = loaded.case.patient_dir / str(spec["output_filename"])
            current_output = target_output
        loaded_patient_case_count = (
            sum(
                case.patient_dir.resolve() == loaded.case.patient_dir.resolve()
                for case in cases
            )
            if loaded is not None else 0
        )
        current_quality = (
            self._matching_vascular_manifest(
                loaded.case,
                current_output,
                allow_legacy_without_source=loaded_patient_case_count == 1,
            )
            if loaded is not None and current_output is not None else {}
        )
        current_output_exists = bool(current_output and current_output.is_file())
        try:
            current_output_sha256 = file_hash(current_output).lower() if current_output_exists else ""
        except OSError:
            current_output_sha256 = ""
        if loaded is not None and current_output_exists and not current_quality:
            multiple_series = loaded_patient_case_count > 1
            conflicting_source = self._vascular_manifest_has_conflicting_source(loaded.case, current_output)
            identity_mismatch = multiple_series or conflicting_source
            current_quality = {
                "processing_mode": "unknown",
                "quality_status": "source_unverified",
                "review_required": True,
                "quality_note": (
                    f"{current_output.name} 的运行清单指向另一份 CT，已阻止载入；请重新运行{spec['completion_label']}。"
                    if conflicting_source else
                    f"患者目录存在 {current_output.name}，但无法确认它属于当前影像序列；请勿直接视为当前序列结果，需复核或重新运行{spec['completion_label']}。"
                    if multiple_series else
                    f"当前 {current_output.name} 缺少与本影像匹配的运行指纹，需重点复核。"
                ),
                "source_identity_verified": False,
                "source_identity_status": (
                    "source_hash_mismatch" if conflicting_source else
                    "multiple_series_mismatch" if multiple_series else "unverified"
                ),
                "output_identity_mismatch": identity_mismatch,
            }
        with self._vascular_lock:
            slot_reserved = self._vascular_slot_reserved or self._vascular_root_switch_reserved
        return {
            "model_key": spec["model_key"],
            "model_name": spec["model_name"],
            "algorithm": spec["algorithm"],
            "pipeline_version": spec["pipeline_version"],
            "output_filename": spec["output_filename"],
            "model_scope": spec["model_scope"],
            "input_contract": spec["input_contract"],
            "available_models": [
                {"model_key": self.VASCULAR_HEPATIC_MODEL, "model_name": "肝动脉分割（原功能）"},
                {"model_key": self.VASCULAR_ABDOMINAL_MODEL, "model_name": "全腹动脉分割（新增）"},
            ],
            "data_root": str(data_root) if data_root is not None else "",
            "patient_count": len(groups),
            "eligible_patient_count": sum(len(patient_cases) == 1 for _patient_dir, patient_cases in groups),
            "ambiguous_patient_count": len(ambiguous),
            "ambiguous_patients": ambiguous,
            "current": {
                "case_id": loaded.case.case_id if loaded is not None else "",
                "patient_dir": str(loaded.case.patient_dir) if loaded is not None else "",
                "target_output_path": str(target_output) if target_output is not None else "",
                "target_output_exists": bool(target_output and target_output.is_file()),
                "output_path": str(current_output) if current_output is not None else "",
                "output_exists": current_output_exists,
                "output_sha256": current_output_sha256,
                "dirty": bool(loaded and loaded.dirty),
                "ready": bool(loaded and not loaded.dirty and active is None and not slot_reserved),
                **current_quality,
            },
            "active_task": active.to_json() if active is not None else None,
        }

    @staticmethod
    def _progress_payload(
        *, model_key: str, model_name: str, output_filename: str,
        mode: str, current: int, total: int, patient: str, case_id: str,
        stage: str, stage_index: int, stage_total: int, message: str,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        completed = sum(item.get("status") == "completed" for item in results)
        failed = sum(item.get("status") == "failed" for item in results)
        skipped = sum(item.get("status") == "skipped" for item in results)
        return {
            "model_key": model_key,
            "model_name": model_name,
            "output_filename": output_filename,
            "mode": mode,
            "progress": {
                "current": current,
                "total": total,
                "percent": round((current - 1 + stage_index / max(stage_total, 1)) / max(total, 1) * 100, 1),
                "patient": patient,
                "case_id": case_id,
                "stage": stage,
                "stage_index": stage_index,
                "stage_total": stage_total,
                "message": message,
            },
            "counts": {"completed": completed, "failed": failed, "skipped": skipped, "total": total},
            "results": list(results),
        }

    def start_vascular_current(
        self,
        expected_case_id: str | None = None,
        expected_session_token: str | None = None,
        model_key: str = VASCULAR_HEPATIC_MODEL,
    ) -> dict[str, Any]:
        spec = self._vascular_model_spec(model_key)
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            if loaded.dirty:
                raise ConflictError("当前病例有未保存修改；请先保存或放弃修改，再运行血管分割")
            case = loaded.case
        self._claim_vascular_slot()
        try:
            pipeline = self._vascular_pipeline_for(str(spec["model_key"]))
            pipeline.reset_cancel()
            if self._hepatic_output_is_protected(case, pipeline, spec):
                raise ConflictError(self._hepatic_output_protection_message(case))
        except Exception:
            self._abort_vascular_claim()
            raise

        def operation(entry: TaskEntry) -> None:
            results: list[dict[str, Any]] = []

            def progress(stage: str, stage_index: int, stage_total: int, message: str) -> None:
                entry.message = message
                entry.details = self._progress_payload(
                    model_key=str(spec["model_key"]), model_name=str(spec["model_name"]),
                    output_filename=str(spec["output_filename"]),
                    mode="current", current=1, total=1, patient=case.patient_dir.name,
                    case_id=case.case_id, stage=stage, stage_index=stage_index,
                    stage_total=stage_total, message=message, results=results,
                )

            try:
                result = pipeline.run_case(case, entry.id, progress)
                results.append({"status": "completed", **result.to_json()})
                case.status = "已完成"
                entry.details = self._progress_payload(
                    model_key=str(spec["model_key"]), model_name=str(spec["model_name"]),
                    output_filename=str(spec["output_filename"]),
                    mode="current", current=1, total=1, patient=case.patient_dir.name,
                    case_id=case.case_id, stage="completed", stage_index=int(spec["total_stages"]),
                    stage_total=int(spec["total_stages"]),
                    message=f"{spec['completion_label']}完成，已保存 {spec['output_filename']}", results=results,
                )
                entry.details["result"] = result.to_json()
                entry.message = f"{spec['completion_label']}完成，已保存 {spec['output_filename']}"
            except PipelineCancelled:
                return
            except Exception:
                case.status = "失败"
                raise
            finally:
                self._release_vascular_slot(entry.id)

        try:
            entry = self.state.tasks.submit("vascular_case", case.case_id, pipeline, operation)
            self._activate_vascular_slot(entry.id)
        except Exception:
            self._abort_vascular_claim()
            raise
        return entry.to_json()

    def start_vascular_batch(self, model_key: str = VASCULAR_HEPATIC_MODEL) -> dict[str, Any]:
        spec = self._vascular_model_spec(model_key)
        with self.state.lock:
            cases = list(self.state.cases)
            loaded = self.state.loaded
        if loaded is not None:
            with loaded.lock:
                if loaded.dirty:
                    raise ConflictError("当前病例有未保存修改；请先保存或放弃修改，再启动批量血管分割")
        groups = self._vascular_patient_groups(cases)
        if not groups:
            raise ValidationError("当前总文件夹没有可处理的患者")
        self._claim_vascular_slot()
        try:
            pipeline = self._vascular_pipeline_for(str(spec["model_key"]))
            pipeline.reset_cancel()
        except Exception:
            self._abort_vascular_claim()
            raise

        def operation(entry: TaskEntry) -> None:
            results: list[dict[str, Any]] = []
            total = len(groups)
            try:
                for patient_index, (patient_dir, patient_cases) in enumerate(groups, start=1):
                    if entry.status in {"cancelled", "cancelling"}:
                        return
                    if len(patient_cases) != 1:
                        results.append({
                            "status": "skipped",
                            "patient_dir": str(patient_dir),
                            "case_ids": [case.case_id for case in patient_cases],
                            "error": "该患者发现多个影像序列；为避免覆盖错误期相，未自动选择",
                            "recovery": "保留唯一动脉期影像后重新扫描，或载入目标序列后使用单例血管分割",
                        })
                        entry.details = self._progress_payload(
                            model_key=str(spec["model_key"]), model_name=str(spec["model_name"]),
                            output_filename=str(spec["output_filename"]),
                            mode="batch", current=patient_index, total=total, patient=patient_dir.name,
                            case_id="", stage="skipped",
                            stage_index=int(spec["total_stages"]),
                            stage_total=int(spec["total_stages"]),
                            message="发现多个影像序列，已安全跳过", results=results,
                        )
                        if patient_index < total:
                            pipeline.prepare_next_case()
                        continue
                    case = patient_cases[0]
                    if self._hepatic_output_is_protected(case, pipeline, spec):
                        results.append({
                            "status": "skipped",
                            "patient_dir": str(patient_dir),
                            "case_id": case.case_id,
                            "error": self._hepatic_output_protection_message(case),
                            "recovery": "不覆盖既有 roi.nii.gz；请明确保留/改名人工 ROI，或验证原文件来源后再运行。",
                        })
                        entry.details = self._progress_payload(
                            model_key=str(spec["model_key"]), model_name=str(spec["model_name"]),
                            output_filename=str(spec["output_filename"]),
                            mode="batch", current=patient_index, total=total, patient=patient_dir.name,
                            case_id=case.case_id, stage="skipped",
                            stage_index=int(spec["total_stages"]), stage_total=int(spec["total_stages"]),
                            message="既有 roi.nii.gz 未验证，已安全跳过", results=results,
                        )
                        if patient_index < total:
                            pipeline.prepare_next_case()
                        continue

                    def progress(stage: str, stage_index: int, stage_total: int, message: str) -> None:
                        entry.message = f"{patient_index}/{total} · {case.patient_dir.name} · {message}"
                        entry.details = self._progress_payload(
                            model_key=str(spec["model_key"]), model_name=str(spec["model_name"]),
                            output_filename=str(spec["output_filename"]),
                            mode="batch", current=patient_index, total=total, patient=case.patient_dir.name,
                            case_id=case.case_id, stage=stage, stage_index=stage_index,
                            stage_total=stage_total, message=message, results=results,
                        )

                    try:
                        result = pipeline.run_case(case, f"{entry.id}-{patient_index:04d}", progress)
                        results.append({"status": "completed", **result.to_json()})
                        case.status = "已完成"
                    except PipelineCancelled:
                        return
                    except Exception as exc:
                        case.status = "失败"
                        results.append({
                            "status": "failed",
                            "patient_dir": str(patient_dir),
                            "case_id": case.case_id,
                            "error": f"{type(exc).__name__}: {exc}",
                            "recovery": "检查该患者是否为动脉期CT及运行日志后，可单独重试；其余患者已继续处理",
                        })
                    entry.details = self._progress_payload(
                        model_key=str(spec["model_key"]), model_name=str(spec["model_name"]),
                        output_filename=str(spec["output_filename"]),
                        mode="batch", current=patient_index, total=total, patient=case.patient_dir.name,
                        case_id=case.case_id, stage="case_complete",
                        stage_index=int(spec["total_stages"]),
                        stage_total=int(spec["total_stages"]),
                        message="当前患者处理结束", results=results,
                    )
                    if patient_index < total:
                        pipeline.prepare_next_case()

                counts = entry.details.get("counts", {})
                if counts.get("failed", 0) or counts.get("skipped", 0):
                    entry.status = "completed_with_failures"
                    entry.message = (
                        f"批量结束：成功 {counts.get('completed', 0)}，"
                        f"失败 {counts.get('failed', 0)}，跳过 {counts.get('skipped', 0)}"
                    )
                else:
                    entry.message = (
                        f"批量完成：{counts.get('completed', 0)} 个患者均已保存 "
                        f"{spec['output_filename']}"
                    )
            finally:
                self._release_vascular_slot(entry.id)

        try:
            entry = self.state.tasks.submit("vascular_batch", "__batch__", pipeline, operation)
            self._activate_vascular_slot(entry.id)
        except Exception:
            self._abort_vascular_claim()
            raise
        return entry.to_json()

    def vascular_task(self, task_id: str) -> dict[str, Any]:
        entry = self.state.tasks.get(task_id)
        if entry is None or not entry.kind.startswith("vascular_"):
            raise NotFoundError("血管任务不存在")
        return entry.to_json()

    def cancel_vascular_task(self, task_id: str) -> dict[str, Any]:
        entry = self.state.tasks.get(task_id)
        if entry is None or not entry.kind.startswith("vascular_"):
            raise NotFoundError("血管任务不存在")
        cancelled = self.state.tasks.cancel(task_id)
        if cancelled is None:
            raise NotFoundError("血管任务不存在")
        return cancelled.to_json()

    @staticmethod
    def _single_roi_filename(roi_name: str) -> str:
        stem = roi_name.strip()
        lower = stem.lower()
        if lower.endswith(".nii.gz"):
            stem = stem[:-7]
        elif lower.endswith(".nii"):
            stem = stem[:-4]
        if stem.lower().startswith("roi_"):
            stem = stem[4:]
        return f"roi_{safe_name(stem)}.nii.gz"

    @staticmethod
    def _editable_output_layers(loaded: LoadedCase) -> tuple[dict[int, np.ndarray], list[LabelDefinition], dict[int, np.ndarray]]:
        if loaded.layers:
            editable_runtime_ids = {
                runtime_id for runtime_id, layer in loaded.layers.items() if layer.editable
            }
            if not editable_runtime_ids:
                raise ConflictError("当前没有可编辑 ROI 文件，不能保存只读对比图层")
            masks: dict[int, np.ndarray] = {}
            labels: list[LabelDefinition] = []
            baseline: dict[int, np.ndarray] = {}
            labels_by_runtime = {label.id: label for label in loaded.labels}
            for runtime_id in sorted(editable_runtime_ids):
                layer = loaded.layers[runtime_id]
                source_label_id = layer.source_label_id
                if source_label_id in masks:
                    raise ConflictError("当前编辑目标包含重复源标签，已阻止保存")
                masks[source_label_id] = loaded.masks[runtime_id]
                label = labels_by_runtime[runtime_id]
                labels.append(LabelDefinition(
                    source_label_id, label.name, label.display_name, label.color,
                    label.hotkey, label.priority, label.locked,
                ))
                if runtime_id in loaded.auto_baseline:
                    baseline[source_label_id] = loaded.auto_baseline[runtime_id]
            return masks, labels, baseline

        reference_ids = {int(value) for value in loaded.provenance.get("reference_label_ids", [])}
        return (
            {label_id: mask for label_id, mask in loaded.masks.items() if label_id not in reference_ids},
            [label for label in loaded.labels if label.id not in reference_ids],
            {label_id: mask for label_id, mask in loaded.auto_baseline.items() if label_id not in reference_ids},
        )

    def export_single_nifti(
        self,
        roi_name: str,
        reviewed: bool,
        expected_case_id: str | None = None,
        expected_session_token: str | None = None,
    ) -> dict[str, Any]:
        """Export the current reviewed layer as exactly one combined label-map NIfTI."""
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            declared = {int(value) for value in loaded.provenance.get("proposal_labels", [])}
            decided = {int(value) for value in loaded.provenance.get("decisions", {})}
            pending = set(loaded.ai_proposal) | (declared - decided)
            if reviewed and pending:
                raise ConflictError(f"仍有未处理的AI候选标签：{', '.join(str(value) for value in sorted(pending))}")

            filename = self._single_roi_filename(roi_name)
            output = loaded.case.patient_dir / filename
            staging = loaded.case.patient_dir / f"roi_.{filename}.{uuid.uuid4().hex}.stage.nii.gz"
            editable_masks, editable_labels, _editable_baseline = self._editable_output_layers(loaded)
            combined, overlap_count = combine_masks(
                editable_masks,
                loaded.volume.array_zyx.shape,
                editable_labels,
            )
            source_nifti = loaded.case.image_path if loaded.case.kind == "nifti" else None
            try:
                write_mask_on_source_grid(loaded.volume, combined, staging, source_nifti)
                staging.replace(output)
            finally:
                staging.unlink(missing_ok=True)

            relative_output = self._relative_path(output, loaded.case.patient_dir)
            if str(loaded.provenance.get("working_layer_kind", "")).startswith("new_"):
                # Promote the explicitly saved in-memory layer to its real file.
                # This only changes session metadata; reference layers are not written.
                for layer in loaded.layers.values():
                    if not layer.editable:
                        continue
                    layer.source_file = relative_output
                    layer.layer_key = self._layer_key(relative_output, layer.source_label_id)
                    layer.role = "editable"
                if relative_output not in loaded.selected_roi_files:
                    loaded.selected_roi_files.append(relative_output)
                loaded.provenance["selected_roi_files"] = list(loaded.selected_roi_files)
                loaded.provenance["editable_roi_source"] = relative_output
                loaded.provenance["loaded_roi"] = relative_output
                loaded.provenance.pop("working_layer_kind", None)

            # Saving the single NIfTI is the completion action in the simplified
            # workflow; a successful write must end the repairing state.
            status = "已完成"
            loaded.case.status = status
            loaded.dirty = False
            loaded.revision += 1
            revision = loaded.revision
            loaded.available_roi_files = [
                self._file_item(path, loaded.case.patient_dir, self._roi_file_role(path))
                for path in self._patient_roi_paths(loaded.case)
            ]
        self._cancel_recovery(loaded, clear=True)
        return {
            "output": str(output),
            "relative_path": self._relative_path(output, loaded.case.patient_dir),
            "filename": filename,
            "status": status,
            "revision": revision,
            "overlap_count": overlap_count,
            "sha256": file_hash(output),
        }

    def save(self, reviewed: bool, expected_case_id: str | None = None, expected_session_token: str | None = None) -> dict[str, Any]:
        loaded = self.require_loaded(expected_case_id, expected_session_token)
        with loaded.lock:
            declared = {int(value) for value in loaded.provenance.get("proposal_labels", [])}
            decided = {int(value) for value in loaded.provenance.get("decisions", {})}
            pending = set(loaded.ai_proposal) | (declared - decided)
            if reviewed and pending:
                raise ConflictError(f"仍有未处理的AI候选标签：{', '.join(str(value) for value in sorted(pending))}")
            status = "已完成"
            editable_masks, editable_labels, editable_baseline = self._editable_output_layers(loaded)
            output = save_case(
                loaded.case, loaded.volume, editable_masks, editable_labels, status,
                editable_baseline, loaded.provenance,
            )
            loaded.case.status = status
            loaded.dirty = False
            loaded.revision += 1
            loaded.available_roi_files = [
                self._file_item(path, loaded.case.patient_dir, self._roi_file_role(path))
                for path in self._patient_roi_paths(loaded.case)
            ]
        self._cancel_recovery(loaded, clear=True)
        return {"output": str(output), "status": status, "revision": loaded.revision}
