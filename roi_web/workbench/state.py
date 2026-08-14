from __future__ import annotations

import copy
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from roi_workbench.core import CaseRecord, LabelDefinition, VolumeData


@dataclass
class EditRecord:
    label_id: int
    before: np.ndarray
    after: np.ndarray
    orientation: str | None = None
    index: int | None = None
    description: str = "edit"
    region: tuple[slice, slice, slice] | None = None
    layer_key: str = ""


@dataclass
class RoiLayer:
    """Session-local mask binding with a stable file-scoped external identity."""

    runtime_id: int
    source_file: str
    source_label_id: int
    layer_key: str
    role: str = "reference"
    editable: bool = False

    def to_json(self, label: LabelDefinition) -> dict[str, Any]:
        payload = label.to_json()
        payload.update({
            "id": self.runtime_id,
            "runtime_label_id": self.runtime_id,
            "source_file": self.source_file,
            "source_label_id": self.source_label_id,
            "layer_key": self.layer_key,
            "role": self.role,
            "editable": self.editable,
        })
        return payload


@dataclass
class LoadedCase:
    case: CaseRecord
    volume: VolumeData
    labels: list[LabelDefinition]
    masks: dict[int, np.ndarray]
    layers: dict[int, RoiLayer] = field(default_factory=dict)
    selected_roi_files: list[str] = field(default_factory=list)
    last_roi_selection_request_id: int = 0
    available_roi_files: list[dict[str, Any]] = field(default_factory=list)
    session_token: str = field(default_factory=lambda: uuid.uuid4().hex)
    auto_baseline: dict[int, np.ndarray] = field(default_factory=dict)
    ai_proposal: dict[int, np.ndarray] = field(default_factory=dict)
    prompts: list[dict[str, Any]] = field(default_factory=list)
    prompt_revision: int = 0
    provenance: dict[str, Any] = field(default_factory=dict)
    display_info: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    undo_stack: list[EditRecord] = field(default_factory=list)
    redo_stack: list[EditRecord] = field(default_factory=list)
    operation_log: list[dict[str, Any]] = field(default_factory=list)
    revision: int = 0
    dirty: bool = False
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)


@dataclass
class TaskEntry:
    id: str
    kind: str
    case_id: str
    status: str = "queued"
    message: str = "等待运行"
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    engine: Any = field(default=None, repr=False)

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "case_id": self.case_id,
            "status": self.status,
            "message": self.message,
            "error": self.error,
            "details": copy.deepcopy(self.details),
        }


class TaskManager:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="roi-web-model")
        self._tasks: dict[str, TaskEntry] = {}
        self._lock = threading.RLock()

    def submit(self, kind: str, case_id: str, engine: Any, operation: Callable[[TaskEntry], None]) -> TaskEntry:
        entry = TaskEntry(uuid.uuid4().hex, kind, case_id, engine=engine)
        with self._lock:
            self._tasks[entry.id] = entry

        def runner() -> None:
            with self._lock:
                if entry.status == "cancelled":
                    return
                entry.status = "running"
                entry.message = {
                    "vascular_case": "正在处理当前患者的全腹动脉树",
                    "vascular_batch": "正在按患者串行处理全腹动脉树",
                }.get(entry.kind, "模型运行中")
            try:
                operation(entry)
                with self._lock:
                    if entry.status == "running":
                        entry.status = "completed"
                        entry.message = {
                            "vascular_case": "全腹动脉分割完成，已保存 abdominal_arteries_roi.nii.gz",
                            "vascular_batch": "全部患者处理完成",
                        }.get(entry.kind, "模型结果已写入可编辑 ROI")
                    elif entry.status == "cancelling":
                        entry.status = "cancelled"
                        entry.message = "已取消"
            except Exception as exc:
                with self._lock:
                    if entry.status == "cancelling":
                        entry.status = "cancelled"
                        entry.message = "已取消"
                        entry.error = ""
                    elif entry.status != "cancelled":
                        entry.status = "failed"
                        entry.error = f"{type(exc).__name__}: {exc}"
                        entry.message = "模型运行失败"

        self._executor.submit(runner)
        return entry

    def get(self, task_id: str) -> TaskEntry | None:
        with self._lock:
            return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> TaskEntry | None:
        with self._lock:
            entry = self._tasks.get(task_id)
            if entry is None:
                return None
            if entry.status == "queued":
                entry.status = "cancelled"
                entry.message = "已取消排队任务"
            elif entry.status == "running":
                # Keep the manager lock while the engine decides whether the
                # final publish boundary has already started. The worker cannot
                # report a terminal state between this decision and transition.
                accepted = entry.engine.cancel()
                if accepted is False:
                    entry.message = "最终 ROI 正在原子提交，当前取消未生效"
                else:
                    entry.status = "cancelling"
                    entry.message = "正在取消；等待当前进程安全退出"
        return entry


@dataclass
class WorkbenchState:
    project_root: Path
    data_root: Path | None = None
    cases: list[CaseRecord] = field(default_factory=list)
    loaded: LoadedCase | None = None
    generation: int = 0
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    tasks: TaskManager = field(default_factory=TaskManager, repr=False)
