"""Persistent nnInteractive initial-mask worker executed inside WSL.

The Windows controller owns publication and reference cleanup. This worker only
writes per-case staging NIfTI files and reports JSON-lines progress so a failed
case cannot overwrite an existing reviewed ROI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch

from nnInteractive.inference.inference_session import nnInteractiveInferenceSession
from nnInteractive.model_management import ensure_model_available


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--model", default="nnInteractive_v1.0")
    return parser.parse_args()


def emit(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=False), flush=True)


def geometry(image: sitk.Image) -> tuple[tuple[int, ...], ...]:
    return (
        tuple(int(value) for value in image.GetSize()),
        tuple(float(value) for value in image.GetSpacing()),
        tuple(float(value) for value in image.GetOrigin()),
        tuple(float(value) for value in image.GetDirection()),
    )


def geometry_matches(reference: sitk.Image, candidate: sitk.Image, tolerance: float = 1e-4) -> bool:
    reference_geometry = geometry(reference)
    candidate_geometry = geometry(candidate)
    return (
        reference_geometry[0] == candidate_geometry[0]
        and all(
            np.allclose(reference_values, candidate_values, atol=tolerance)
            for reference_values, candidate_values in zip(reference_geometry[1:], candidate_geometry[1:])
        )
    )


def load_manifest(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Batch manifest must contain a non-empty cases list")
    required = {"index", "image", "initial_mask", "stage_output"}
    for case in cases:
        if not isinstance(case, dict) or not required.issubset(case):
            raise ValueError(f"Invalid case entry in batch manifest: {case!r}")
    return cases


def run_case(session: nnInteractiveInferenceSession, case: dict[str, Any]) -> int:
    source = sitk.ReadImage(str(case["image"]))
    initial_source = sitk.ReadImage(str(case["initial_mask"]))
    if source.GetDimension() != 3 or initial_source.GetDimension() != 3:
        raise ValueError("Image and initial ROI must both be three-dimensional")
    if not geometry_matches(source, initial_source):
        raise ValueError("Initial ROI geometry does not match the arterial image")

    array_zyx = np.asarray(sitk.GetArrayFromImage(source))
    initial_zyx = np.asarray(sitk.GetArrayFromImage(initial_source))
    if not np.isfinite(array_zyx).all():
        raise ValueError("Image contains NaN or infinite values")
    if not np.isfinite(initial_zyx).all():
        raise ValueError("Initial ROI contains NaN or infinite values")
    initial_xyz = np.ascontiguousarray(
        np.transpose(initial_zyx != 0, (2, 1, 0)),
        dtype=np.uint8,
    )
    if not np.any(initial_xyz):
        raise ValueError("Initial ROI is empty")

    image_xyz = np.transpose(array_zyx, (2, 1, 0))[None]
    session.set_image(image_xyz)
    target = torch.zeros(image_xyz.shape[1:], dtype=torch.uint8, device=session.device)
    session.set_target_buffer(target)
    session.add_initial_seg_interaction(initial_xyz, run_prediction=True)

    result_xyz = target.detach().cpu().numpy().astype(np.uint8)
    result_zyx = np.transpose(result_xyz, (2, 1, 0))
    voxel_count = int(np.count_nonzero(result_zyx))
    if voxel_count == 0:
        raise ValueError("nnInteractive returned an empty mask")

    output = sitk.GetImageFromArray(result_zyx)
    output.CopyInformation(source)
    stage_output = Path(str(case["stage_output"]))
    stage_output.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(output, str(stage_output), useCompression=True)
    return voxel_count


def run() -> None:
    args = parse_args()
    cases = load_manifest(Path(args.manifest))
    model_path = ensure_model_available(args.model)
    session = nnInteractiveInferenceSession(
        device=torch.device("cuda:0" if torch.cuda.is_available() else "cpu"),
        use_torch_compile=False,
        verbose=False,
        do_autozoom=True,
    )
    session.initialize_from_trained_model_folder(str(model_path))
    emit("ready", case_count=len(cases), device=str(session.device))

    succeeded = 0
    failed = 0
    for case in cases:
        index = int(case["index"])
        emit("case_started", index=index)
        try:
            voxel_count = run_case(session, case)
        except Exception as exc:  # isolate a bad patient and continue the batch
            failed += 1
            emit("case_failed", index=index, error=f"{type(exc).__name__}: {exc}")
            continue
        succeeded += 1
        emit("case_completed", index=index, voxel_count=voxel_count)
    emit("batch_completed", succeeded=succeeded, failed=failed, total=len(cases))


if __name__ == "__main__":
    run()
