from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


Orientation = Literal["axial", "coronal", "sagittal"]


class RootRequest(BaseModel):
    path: str = Field(min_length=1, max_length=4096)
    discard_dirty: bool = False


class LoadCaseRequest(BaseModel):
    case_id: str = Field(min_length=1, max_length=1024)
    discard_dirty: bool = False
    roi_relative_path: str = Field(default="", max_length=4096)
    expected_roi_sha256: str = Field(default="", max_length=64, pattern=r"^$|^[0-9a-fA-F]{64}$")


class ImportMaskRequest(BaseModel):
    relative_path: str = Field(min_length=1, max_length=4096)


class LoadEditableRoiRequest(BaseModel):
    relative_path: str = Field(min_length=1, max_length=4096)
    discard_dirty: bool = False


class RoiSelectionRequest(BaseModel):
    relative_paths: list[str] = Field(default_factory=list, max_length=256)
    discard_dirty: bool = False
    request_id: int = Field(default=0, ge=0, le=2_147_483_647)

    @field_validator("relative_paths")
    @classmethod
    def validate_paths(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            path = value.strip()
            if not path or len(path) > 4096:
                raise ValueError("ROI relative path is invalid")
            if path not in seen:
                result.append(path)
                seen.add(path)
        return result


class DeleteRoiFileRequest(BaseModel):
    """A deliberately explicit request for a recoverable patient ROI deletion."""

    relative_path: str = Field(min_length=1, max_length=4096)
    confirm: bool = False
    request_id: int = Field(default=0, ge=0, le=2_147_483_647)


class Point2D(BaseModel):
    x: float
    y: float


class StrokeRequest(BaseModel):
    orientation: Orientation
    index: int = Field(ge=0)
    label_id: int = Field(ge=1, le=65535)
    layer_key: str = Field(default="", max_length=8192)
    tool: Literal["brush", "eraser"]
    radius: int = Field(default=3, ge=1, le=100)
    points: list[Point2D] = Field(min_length=1, max_length=10000)


class PolygonRequest(BaseModel):
    orientation: Orientation
    index: int = Field(ge=0)
    label_id: int = Field(ge=1, le=65535)
    layer_key: str = Field(default="", max_length=8192)
    points: list[Point2D] = Field(min_length=3, max_length=10000)


class FillRequest(BaseModel):
    orientation: Orientation
    index: int = Field(ge=0)
    label_id: int = Field(ge=1, le=65535)
    layer_key: str = Field(default="", max_length=8192)
    point: Point2D


class TrimRoiRequest(BaseModel):
    orientation: Orientation
    index: int = Field(ge=0)
    label_id: int = Field(ge=1, le=65535)
    layer_key: str = Field(default="", max_length=8192)
    direction: Literal["left", "right"]


class KeepComponentRequest(BaseModel):
    orientation: Orientation
    index: int = Field(ge=0)
    label_id: int = Field(ge=1, le=65535)
    layer_key: str = Field(default="", max_length=8192)
    point: Point2D


class ExcludeIntensityRequest(BaseModel):
    orientation: Orientation
    index: int = Field(ge=0)
    label_id: int = Field(ge=1, le=65535)
    layer_key: str = Field(default="", max_length=8192)
    scope: Literal["slice", "volume"] = "volume"
    minimum: Optional[float] = Field(default=None, allow_inf_nan=False)
    maximum: Optional[float] = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_range(self):
        if self.minimum is None and self.maximum is None:
            raise ValueError("minimum and maximum cannot both be empty")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum cannot exceed maximum")
        return self


class LabelCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    display_name: str = Field(default="", max_length=128)
    color: str = "#ff3b30"
    hotkey: str = Field(default="", max_length=16)
    priority: int = Field(default=0, ge=-10000, le=10000)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("color must use #RRGGBB")
        int(value[1:], 16)
        return value.lower()


class LabelLockRequest(BaseModel):
    label_id: int = Field(ge=1, le=65535)
    layer_key: str = Field(default="", max_length=8192)
    locked: bool


class LabelColorRequest(BaseModel):
    label_id: int = Field(ge=1, le=65535)
    layer_key: str = Field(default="", max_length=8192)
    color: str = "#ff3b30"

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError("color must use #RRGGBB")
        int(value[1:], 16)
        return value.lower()


class PromptRequest(BaseModel):
    orientation: Orientation
    index: int = Field(ge=0)
    kind: Literal["positive", "negative", "box", "scribble_positive", "scribble_negative", "lasso"]
    points: list[Point2D] = Field(min_length=1, max_length=10000)
    radius: int = Field(default=1, ge=1, le=50)


class InteractiveTaskRequest(BaseModel):
    label_id: int = Field(ge=1, le=65535)
    layer_key: str = Field(default="", max_length=8192)


class ProposalMergeRequest(BaseModel):
    label_id: int = Field(ge=1, le=65535)
    layer_key: str = Field(default="", max_length=8192)
    operation: Literal["add", "remove", "local_replace", "replace", "reject", "restore_baseline"]


class SaveRequest(BaseModel):
    reviewed: bool = False


class ExportRequest(BaseModel):
    reviewed: bool = False
    roi_name: str = Field(default="ROI", min_length=1, max_length=80)

    @field_validator("roi_name")
    @classmethod
    def validate_roi_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("ROI name cannot be blank")
        return value
