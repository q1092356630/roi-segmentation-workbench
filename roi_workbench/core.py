from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


CASE_STATUSES = ("未开始", "待审核", "修补中", "已完成", "失败")
LEGACY_CASE_STATUS_ALIASES = {"已审核": "已完成"}


def normalize_case_status(status: object, default: str = "未开始") -> str:
    value = LEGACY_CASE_STATUS_ALIASES.get(str(status), str(status))
    return value if value in CASE_STATUSES else default


@dataclass
class VolumeGeometry:
    shape_zyx: tuple[int, int, int]
    spacing_xyz: tuple[float, float, float]
    origin_xyz: tuple[float, float, float]
    direction: tuple[float, ...]
    source_path: str
    modality: str = ""
    series_uid: str = ""
    affine: list[list[float]] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "shape_zyx": list(self.shape_zyx),
            "spacing_xyz": list(self.spacing_xyz),
            "origin_xyz": list(self.origin_xyz),
            "direction": list(self.direction),
            "source_path": self.source_path,
            "modality": self.modality,
            "series_uid": self.series_uid,
            "affine": self.affine,
        }


@dataclass
class VolumeData:
    array_zyx: np.ndarray
    geometry: VolumeGeometry
    reference_image: Any = field(repr=False, default=None)
    source_array_zyx: np.ndarray | None = field(repr=False, default=None)
    source_geometry: VolumeGeometry | None = None
    source_reference_image: Any = field(repr=False, default=None)
    reformatted_for_display: bool = False


@dataclass
class LabelDefinition:
    id: int
    name: str
    display_name: str = ""
    color: str = "#ff3b30"
    hotkey: str = ""
    priority: int = 0
    locked: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name or self.name,
            "color": self.color,
            "hotkey": self.hotkey,
            "priority": self.priority,
            "locked": self.locked,
        }


@dataclass
class CaseRecord:
    case_id: str
    patient_dir: Path
    image_path: Path
    kind: str = "nifti"
    series_uid: str = ""
    series_description: str = ""
    status: str = "未开始"
    roi_dir: Path | None = None
    dataset_root: Path | None = None
    source_sha256: str = ""

    def output_dir(self) -> Path:
        safe_case = self.case_id.replace("/", "__").replace("\\", "__")
        return self.roi_dir or (self.patient_dir / "ROI" / safe_case)


@dataclass
class PredictionResult:
    masks: dict[int, np.ndarray]
    model_id: str
    model_version: str = ""
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)


def normalize_label_array(mask: np.ndarray, shape: tuple[int, int, int]) -> np.ndarray:
    arr = np.asarray(mask)
    if arr.shape != shape:
        raise ValueError(f"Mask shape {arr.shape} does not match image shape {shape}")
    if not np.isfinite(arr).all():
        raise ValueError("Mask contains NaN or infinite values")
    return arr.astype(np.uint16, copy=False)


def split_label_map(mask: np.ndarray) -> dict[int, np.ndarray]:
    labels = [int(v) for v in np.unique(mask) if int(v) != 0]
    return {label: (mask == label) for label in labels}


def combine_masks(
    masks: dict[int, np.ndarray],
    shape: tuple[int, int, int],
    labels: list[LabelDefinition],
) -> tuple[np.ndarray, int]:
    result = np.zeros(shape, dtype=np.uint16)
    overlaps = np.zeros(shape, dtype=np.uint8)
    priority = {item.id: (item.priority, item.id) for item in labels}
    for label_id in sorted(masks, key=lambda x: priority.get(x, (0, x))):
        mask = np.asarray(masks[label_id], dtype=bool)
        if mask.shape != shape:
            raise ValueError(f"Label {label_id} shape {mask.shape} does not match {shape}")
        overlaps += mask.astype(np.uint8)
        result[mask] = np.uint16(label_id)
    return result, int(np.count_nonzero(overlaps > 1))
