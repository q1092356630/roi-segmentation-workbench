from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage

from .core import CaseRecord, PredictionResult, VolumeData
from .imaging import load_mask, write_like


class ModelError(RuntimeError):
    pass


class ModelCancelled(ModelError):
    pass


def _hidden_console_process_kwargs(platform: str | None = None) -> dict[str, Any]:
    """Keep Windows console processes background-only without detaching their pipes."""
    if (platform or sys.platform) != "win32":
        return {}
    options: dict[str, Any] = {
        "creationflags": int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)),
    }
    startupinfo_factory = getattr(subprocess, "STARTUPINFO", None)
    if startupinfo_factory is not None:
        startupinfo = startupinfo_factory()
        startupinfo.dwFlags |= int(getattr(subprocess, "STARTF_USESHOWWINDOW", 0))
        startupinfo.wShowWindow = int(getattr(subprocess, "SW_HIDE", 0))
        options["startupinfo"] = startupinfo
    return options


class AutoSegmentationEngine:
    model_id = ""

    def predict(self, case: CaseRecord, volume: VolumeData) -> PredictionResult:
        raise NotImplementedError

    def cancel(self) -> None:
        """Cancel an in-flight prediction when the backend supports it."""


class ExternalPowerShellModel(AutoSegmentationEngine):
    def __init__(
        self,
        model_id: str,
        runner: Path,
        extra_args: list[str] | None = None,
        manifest: dict[str, Any] | None = None,
    ):
        self.model_id = model_id
        self.runner = runner
        self.extra_args = extra_args or []
        self.manifest = manifest or {}
        self._process: subprocess.Popen[str] | None = None
        self._cancelled = False
        self._process_lock = threading.Lock()

    def cancel(self) -> None:
        self._cancelled = True
        with self._process_lock:
            if self._process is not None and self._process.poll() is None:
                self._process.terminate()

    def predict(self, case: CaseRecord, volume: VolumeData) -> PredictionResult:
        if not self.runner.is_file():
            raise ModelError(f"Model runner not found: {self.runner}")
        with tempfile.TemporaryDirectory(prefix="roi-workbench-") as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            staged = input_dir / f"{case.case_id.replace('/', '_')}.nii.gz"
            source_reference = volume.source_reference_image if volume.source_reference_image is not None else volume.reference_image
            source_array = volume.source_array_zyx if volume.source_array_zyx is not None else volume.array_zyx
            write_like(source_reference, source_array, staged, case.image_path if case.kind == "nifti" else None)
            command = [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(self.runner),
                "-InputDir", str(input_dir),
                "-OutputDir", str(output_dir),
                *self.extra_args,
            ]
            self._cancelled = False
            with self._process_lock:
                self._process = subprocess.Popen(
                    command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    encoding="utf-8", errors="replace",
                )
            stdout, stderr = self._process.communicate()
            returncode = self._process.returncode
            with self._process_lock:
                self._process = None
            if self._cancelled:
                raise ModelCancelled(f"{self.model_id} inference cancelled")
            if returncode != 0:
                raise ModelError(stderr.strip() or stdout.strip() or f"exit {returncode}")
            outputs = list(output_dir.rglob("*.nii.gz"))
            outputs = [p for p in outputs if p.name != staged.name]
            if not outputs:
                raise ModelError(f"No NIfTI prediction returned by {self.model_id}\n{stdout}")
            prediction = outputs[0]
            mask = load_mask(prediction, volume)
            labels = {int(v) for v in np.unique(mask) if int(v) != 0}
            label_mapping = {int(key): int(value) for key, value in self.manifest.get("label_mapping", {}).items()}
            warnings = []
            if not labels:
                labels = {1}
                warnings.append("Model returned an empty mask")
            qc: dict[str, Any] = {}
            output_masks: dict[int, np.ndarray] = {}
            minimum_component = int(self.manifest.get("postprocessing", {}).get("min_component_voxels", 0))
            for label in sorted(labels):
                binary = mask == label
                if minimum_component > 0 and binary.any():
                    components, component_count = ndimage.label(binary)
                    sizes = np.bincount(components.ravel())
                    keep = np.flatnonzero(sizes >= minimum_component)
                    keep = keep[keep != 0]
                    binary = np.isin(components, keep)
                component_count = int(ndimage.label(binary)[1]) if binary.any() else 0
                active_slices = np.flatnonzero(np.any(binary, axis=(1, 2)))
                qc[str(label)] = {
                    "foreground_voxels": int(binary.sum()),
                    "connected_components": component_count,
                    "slice_range_zyx": [int(active_slices[0]), int(active_slices[-1])] if len(active_slices) else [],
                }
                if component_count > 50:
                    warnings.append(f"Label {label} has {component_count} connected components")
                target_label = label_mapping.get(label, label)
                output_masks[target_label] = output_masks.get(target_label, np.zeros_like(binary)) | binary
            for definition in self.manifest.get("labels", []):
                label_id = int(definition["id"])
                output_masks.setdefault(label_id, np.zeros(mask.shape, dtype=bool))
            return PredictionResult(
                masks=output_masks,
                model_id=self.model_id,
                model_version=str(self.manifest.get("version", "")),
                warnings=warnings,
                provenance={
                    "runner": str(self.runner),
                    "stdout": stdout[-2000:],
                    "qc": qc,
                    "license": self.manifest.get("license", ""),
                    "modality": self.manifest.get("modality", ""),
                    "phase": self.manifest.get("phase", ""),
                    "label_mapping": label_mapping,
                    "labels": self.manifest.get("labels", []),
                },
            )


def discover_models(project_root: Path) -> dict[str, AutoSegmentationEngine]:
    """The public build exposes only the interactive model pathway."""
    return {}


class NnInteractiveClient:
    """Optional WSL bridge. The UI stays usable when the package is not installed."""

    def __init__(
        self,
        distro: str | None = None,
        python_path: str | None = None,
        model_path: str | None = None,
        project_root: Path | None = None,
    ):
        config: dict[str, Any] = {}
        config_path = os.environ.get("ROI_MODEL_CONFIG", "")
        if not config_path and project_root is not None:
            config_path = str(project_root / "config" / "model_paths.json")
        if config_path:
            try:
                config = json.loads(Path(config_path).expanduser().read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                config = {}
        self.distro = distro or os.environ.get("ROI_WSL_DISTRO") or str(config.get("wsl_distro", "Ubuntu-22.04"))
        self.python_path = python_path or os.environ.get("ROI_NNINTERACTIVE_PYTHON") or str(
            config.get("python_path", "/home/your-user/.venvs/nninteractive/bin/python")
        )
        self.model_path = model_path or os.environ.get("ROI_NNINTERACTIVE_MODEL_PATH") or str(
            config.get("model_path", "")
        )
        self._process: subprocess.Popen[str] | None = None
        self._cancelled = False
        self._process_lock = threading.Lock()

    def cancel(self) -> None:
        self._cancelled = True
        with self._process_lock:
            if self._process is not None and self._process.poll() is None:
                self._process.terminate()

    def availability(self) -> tuple[bool, str]:
        command = [
            "wsl.exe", "-d", self.distro, "--",
            self.python_path, "-c", "import nnInteractive; print('ok')",
        ]
        try:
            result = subprocess.run(
                command,
                text=True,
                capture_output=True,
                timeout=15,
                encoding="utf-8",
                errors="replace",
                **_hidden_console_process_kwargs(),
            )
        except Exception as exc:
            return False, str(exc)
        if result.returncode != 0:
            return False, result.stderr.strip() or "nnInteractive is not installed in WSL"
        return True, result.stdout.strip()

    @staticmethod
    def _wsl_path(path: Path) -> str:
        value = str(path.resolve())
        match = re.match(r"^([A-Za-z]):[\\/](.*)$", value)
        if not match:
            raise ModelError(f"Only local Windows drive paths are supported: {value}")
        tail = match.group(2).replace("\\", "/")
        return f"/mnt/{match.group(1).lower()}/{tail}"

    @classmethod
    def _configured_path(cls, value: str) -> str:
        if value.startswith("/"):
            return value
        return cls._wsl_path(Path(value).expanduser())

    def run(
        self,
        image_path: Path,
        prompts: list[dict[str, Any]],
        output_path: Path,
        initial_mask_path: Path | None = None,
    ) -> Path:
        if not prompts and initial_mask_path is None:
            raise ModelError("Add a prompt or provide an initial ROI mask first")
        worker = Path(__file__).resolve().parent / "nninteractive_worker.py"
        prompt_path = output_path.with_suffix(".prompts.json")
        prompt_path.write_text(json.dumps(prompts, ensure_ascii=False), encoding="utf-8")
        command = [
            "wsl.exe", "-d", self.distro, "--",
            self.python_path, self._wsl_path(worker),
            "--image", self._wsl_path(image_path),
            "--prompts", self._wsl_path(prompt_path),
            "--output", self._wsl_path(output_path),
        ]
        if self.model_path:
            command.extend(["--model-path", self._configured_path(self.model_path)])
        if initial_mask_path is not None:
            command.extend(["--initial-mask", self._wsl_path(initial_mask_path)])
        self._cancelled = False
        with self._process_lock:
            self._process = subprocess.Popen(
                command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8", errors="replace",
                **_hidden_console_process_kwargs(),
            )
        stdout, stderr = self._process.communicate()
        returncode = self._process.returncode
        with self._process_lock:
            self._process = None
        try:
            prompt_path.unlink(missing_ok=True)
        except OSError:
            pass
        if self._cancelled:
            raise ModelCancelled("nnInteractive inference cancelled")
        if returncode != 0:
            raise ModelError(stderr.strip() or stdout.strip() or f"exit {returncode}")
        if not output_path.is_file():
            raise ModelError("nnInteractive completed without an output mask")
        return output_path


class NnInteractivePromptEngine(AutoSegmentationEngine):
    model_id = "nnInteractive v1.0"

    def __init__(
        self,
        client: NnInteractiveClient,
        prompts: list[dict[str, Any]],
        label_id: int,
        initial_mask: np.ndarray | None = None,
    ):
        self.client = client
        self.prompts = prompts
        self.label_id = int(label_id)
        self.initial_mask = None if initial_mask is None else np.asarray(initial_mask, dtype=bool).copy()

    def predict(self, case: CaseRecord, volume: VolumeData) -> PredictionResult:
        with tempfile.TemporaryDirectory(prefix="roi-nninteractive-") as tmp:
            tmp_path = Path(tmp)
            image_path = tmp_path / "image.nii.gz"
            output_path = tmp_path / "proposal.nii.gz"
            initial_mask_path = None
            write_like(volume.reference_image, volume.array_zyx, image_path)
            if self.initial_mask is not None:
                if self.initial_mask.shape != volume.array_zyx.shape:
                    raise ModelError(
                        f"Initial ROI shape {self.initial_mask.shape} does not match image {volume.array_zyx.shape}"
                    )
                initial_mask_path = tmp_path / "initial_mask.nii.gz"
                write_like(volume.reference_image, self.initial_mask.astype(np.uint8), initial_mask_path)
            result_path = self.client.run(image_path, self.prompts, output_path, initial_mask_path)
            mask = load_mask(result_path, volume).astype(bool)
            warnings = ["nnInteractive returned an empty mask"] if not mask.any() else []
            return PredictionResult(
                masks={self.label_id: mask},
                model_id=self.model_id,
                model_version="2.5.1 backend / v1.0 checkpoint",
                warnings=warnings,
                provenance={"prompt_count": len(self.prompts), "model_license": "CC BY-NC-SA 4.0"},
            )

    def cancel(self) -> None:
        self.client.cancel()
