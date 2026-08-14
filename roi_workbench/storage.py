from __future__ import annotations

import csv
import json
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from .core import CaseRecord, LabelDefinition, VolumeData, combine_masks, normalize_case_status
from .imaging import case_image_hash, case_source_stat_signature, file_hash, write_like, write_mask_on_source_grid


def safe_name(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z一-龥._-]+", "_", value).strip("._")
    return value or "label"


def load_labels(path: Path) -> list[LabelDefinition]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("labels", payload) if isinstance(payload, dict) else payload
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    return labels_from_rows(rows)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是"}


def labels_from_rows(rows: list[dict[str, Any]]) -> list[LabelDefinition]:
    if not rows:
        raise ValueError("Label schema must contain at least one label")
    labels = []
    for row in rows:
        label_id = int(row["id"])
        if not 1 <= label_id <= np.iinfo(np.uint16).max:
            raise ValueError(f"Label ID must be in 1..65535, got {label_id}")
        labels.append(
            LabelDefinition(
                id=label_id,
                name=str(row.get("name", row.get("display_name", f"label_{row['id']}"))),
                display_name=str(row.get("display_name", row.get("name", ""))),
                color=str(row.get("color", "#ff3b30")),
                hotkey=str(row.get("hotkey", "")),
                priority=int(row.get("priority", 0)),
                locked=_as_bool(row.get("locked", False)),
            )
        )
    if len({label.id for label in labels}) != len(labels):
        raise ValueError("Label IDs must be unique")
    return labels


def labels_json(labels: list[LabelDefinition]) -> list[dict[str, Any]]:
    return [label.to_json() for label in labels]


def _adopt_history_and_snapshot(previous: Path, current: Path) -> None:
    old_history = previous / "_history"
    new_history = current / "_history"
    if old_history.is_dir():
        old_history.rename(new_history)
    else:
        new_history.mkdir(parents=True, exist_ok=True)
    current_items = list(previous.iterdir())
    if not current_items:
        return
    snapshot = new_history / f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{uuid.uuid4().hex}"
    snapshot.mkdir(parents=True, exist_ok=False)
    for item in current_items:
        destination = snapshot / item.name
        item.rename(destination)


def _remove_private_tree(path: Path, parent: Path) -> None:
    resolved = path.resolve()
    if resolved.parent != parent.resolve() or not resolved.name.startswith("."):
        raise RuntimeError(f"Refusing to remove unexpected temporary directory: {resolved}")
    if resolved.is_dir():
        shutil.rmtree(resolved)


def save_case(
    case: CaseRecord,
    volume: VolumeData,
    masks: dict[int, np.ndarray],
    labels: list[LabelDefinition],
    status: str,
    auto_baseline: dict[int, np.ndarray] | None = None,
    provenance: dict[str, Any] | None = None,
) -> Path:
    status = normalize_case_status(status)
    # Validate again at the persistence boundary even when labels originated
    # from model manifests or UI state rather than a schema file.
    labels_from_rows(labels_json(labels))
    output_dir = case.output_dir()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    staging = output_dir.parent / f".{output_dir.name}.stage-{token}"
    displaced = output_dir.parent / f".{output_dir.name}.old-{token}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        combined, overlap_count = combine_masks(masks, volume.array_zyx.shape, labels)
        source_nifti = case.image_path if case.kind == "nifti" else None
        write_mask_on_source_grid(volume, combined, staging / "segmentation_labels.nii.gz", source_nifti)
        if volume.reformatted_for_display:
            write_like(volume.reference_image, combined, staging / "workspace_labels.nii.gz")
        for label in labels:
            mask = masks.get(label.id)
            if mask is None:
                continue
            write_mask_on_source_grid(
                volume,
                np.asarray(mask, dtype=np.uint8),
                staging / f"roi_{label.id}_{safe_name(label.name)}.nii.gz",
                source_nifti,
            )
        if auto_baseline:
            baseline_dir = staging / "auto_baseline"
            baseline_dir.mkdir(exist_ok=True)
            for label_id, mask in auto_baseline.items():
                write_mask_on_source_grid(
                    volume,
                    np.asarray(mask, dtype=np.uint8),
                    baseline_dir / f"label_{label_id}.nii.gz",
                    source_nifti,
                )
                if volume.reformatted_for_display:
                    write_like(
                        volume.reference_image,
                        np.asarray(mask, dtype=np.uint8),
                        baseline_dir / f"label_{label_id}.workspace.nii.gz",
                    )
        if not case.source_sha256:
            case.source_sha256 = case_image_hash(case)
        metadata = {
            "schema_version": 1,
            "case_id": case.case_id,
            "status": status,
            "source_image": str(case.image_path),
            "source_sha256": case.source_sha256,
            "roi_sha256": file_hash(staging / "segmentation_labels.nii.gz"),
            "workspace_roi_sha256": file_hash(staging / "workspace_labels.nii.gz") if (staging / "workspace_labels.nii.gz").is_file() else "",
            "geometry": volume.geometry.to_json(),
            "source_geometry": volume.source_geometry.to_json() if volume.source_geometry is not None else volume.geometry.to_json(),
            "reformatted_for_display": volume.reformatted_for_display,
            "labels": labels_json(labels),
            "overlap_voxel_count": overlap_count,
            "provenance": provenance or {},
            "saved_at": datetime.now().isoformat(timespec="microseconds"),
        }
        (staging / "roi_project.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        if output_dir.exists():
            output_dir.rename(displaced)
        try:
            staging.rename(output_dir)
        except Exception:
            if displaced.exists() and not output_dir.exists():
                displaced.rename(output_dir)
            raise
        if displaced.exists():
            _adopt_history_and_snapshot(displaced, output_dir)
            _remove_private_tree(displaced, output_dir.parent)
        update_manifest(case.dataset_root or case.patient_dir, case, output_dir, status, metadata)
    finally:
        if staging.exists():
            _remove_private_tree(staging, output_dir.parent)
    return output_dir


def update_manifest(patient_dir: Path, case: CaseRecord, output_dir: Path, status: str, metadata: dict[str, Any]) -> None:
    manifest = patient_dir / "roi_manifest.csv"
    fields = [
        "case_id", "image_path", "roi_dir", "status", "schema_version",
        "source_sha256", "roi_sha256", "model_id", "model_version", "saved_at",
    ]
    rows: list[dict[str, str]] = []
    if manifest.exists():
        with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    rows = [row for row in rows if row.get("case_id") != case.case_id]
    rows.append({
        "case_id": case.case_id,
        "image_path": str(case.image_path),
        "roi_dir": str(output_dir),
        "status": status,
        "schema_version": str(metadata.get("schema_version", "")),
        "source_sha256": str(metadata.get("source_sha256", "")),
        "roi_sha256": str(metadata.get("roi_sha256", "")),
        "model_id": str(metadata.get("provenance", {}).get("model_id", metadata.get("provenance", {}).get("model", ""))),
        "model_version": str(metadata.get("provenance", {}).get("model_version", "")),
        "saved_at": str(metadata.get("saved_at", "")),
    })
    temporary = manifest.with_name(f".{manifest.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(manifest)


def recovery_path(case: CaseRecord) -> Path:
    safe_case = case.case_id.replace("/", "__").replace("\\", "__")
    return case.patient_dir / ".roi-workbench" / "recovery" / f"{safe_case}.npz"


@dataclass
class RecoveryState:
    masks: dict[int, np.ndarray]
    labels: list[LabelDefinition]
    project_state: dict[str, Any]

    def __bool__(self) -> bool:
        return bool(self.masks)


def _source_signature(case: CaseRecord) -> dict[str, Any]:
    if not case.source_sha256:
        case.source_sha256 = case_image_hash(case)
    signature = case_source_stat_signature(case)
    signature["sha256"] = case.source_sha256
    return signature


def save_recovery(
    case: CaseRecord,
    masks: dict[int, np.ndarray],
    volume: VolumeData | None = None,
    labels: list[LabelDefinition] | None = None,
    project_state: dict[str, Any] | None = None,
) -> Path:
    path = recovery_path(case)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp.npz")
    metadata = {
        "source": _source_signature(case),
        "geometry": volume.geometry.to_json() if volume is not None else None,
        "labels": labels_json(labels or []),
        "project_state": project_state or {},
    }
    arrays = {f"label_{label_id}": np.asarray(mask, dtype=np.uint8) for label_id, mask in masks.items()}
    arrays["__metadata__"] = np.asarray(json.dumps(metadata, ensure_ascii=False))
    np.savez_compressed(temp, **arrays)
    temp.replace(path)
    return path


def load_recovery(case: CaseRecord, volume: VolumeData | None = None) -> RecoveryState:
    path = recovery_path(case)
    if not path.is_file():
        return RecoveryState({}, [], {})
    with np.load(path, allow_pickle=False) as payload:
        if "__metadata__" not in payload.files:
            return RecoveryState({}, [], {})
        metadata = json.loads(str(payload["__metadata__"].item()))
        if metadata.get("source") != _source_signature(case):
            return RecoveryState({}, [], {})
        result = {int(key.split("_", 1)[1]): payload[key].astype(bool) for key in payload.files if key.startswith("label_")}
        if volume is not None:
            expected_shape = volume.array_zyx.shape
            if metadata.get("geometry") != volume.geometry.to_json():
                return RecoveryState({}, [], {})
            if any(mask.shape != expected_shape for mask in result.values()):
                return RecoveryState({}, [], {})
        recovered_labels = labels_from_rows(metadata.get("labels", [])) if metadata.get("labels") else []
        return RecoveryState(result, recovered_labels, dict(metadata.get("project_state", {})))


def clear_recovery(case: CaseRecord) -> None:
    try:
        recovery_path(case).unlink(missing_ok=True)
    except OSError:
        pass
