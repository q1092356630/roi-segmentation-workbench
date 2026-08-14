"""One-shot nnInteractive worker, executed inside a configured WSL/Linux environment.

The Windows UI sends raw NIfTI plus JSON prompts. The worker keeps the model
and geometry handling out of the PyQt process and writes one binary NIfTI
proposal. The process is intentionally stateless in v0.1; a future model
package can replace it with a persistent session without changing the UI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import SimpleITK as sitk
import torch
from skimage.draw import polygon

from nnInteractive.inference.inference_session import nnInteractiveInferenceSession
from nnInteractive.model_management import ensure_model_available


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--prompts", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--initial-mask")
    parser.add_argument("--model", default="nnInteractive_v1.0")
    parser.add_argument("--model-path", help="Path to a downloaded nnInteractive model directory")
    return parser.parse_args()


def bbox_from_points(start: list[int], end: list[int]) -> list[list[int]]:
    # UI voxel order is z,y,x; nnInteractive uses x,y,z half-open boxes.
    z0, y0, x0 = start
    z1, y1, x1 = end
    return [
        [min(x0, x1), max(x0, x1) + 1],
        [min(y0, y1), max(y0, y1) + 1],
        [min(z0, z1), max(z0, z1) + 1],
    ]


def point_scribble_xyz(
    shape_xyz: tuple[int, int, int],
    voxel_zyx: tuple[int, int, int],
    orientation: str,
    radius: int,
) -> np.ndarray:
    """Create a circular prompt on the displayed plane for a sized point."""
    x_count, y_count, z_count = shape_xyz
    z, y, x = voxel_zyx
    radius = max(1, int(radius))
    scribble = np.zeros(shape_xyz, dtype=np.uint8)
    if orientation == "coronal":
        z0, z1 = max(0, z - radius), min(z_count, z + radius + 1)
        x0, x1 = max(0, x - radius), min(x_count, x + radius + 1)
        zz, xx = np.ogrid[z0:z1, x0:x1]
        disk = (zz - z) ** 2 + (xx - x) ** 2 <= radius ** 2
        scribble[x0:x1, y, z0:z1] = disk.T
    elif orientation == "sagittal":
        z0, z1 = max(0, z - radius), min(z_count, z + radius + 1)
        y0, y1 = max(0, y - radius), min(y_count, y + radius + 1)
        zz, yy = np.ogrid[z0:z1, y0:y1]
        disk = (zz - z) ** 2 + (yy - y) ** 2 <= radius ** 2
        scribble[x, y0:y1, z0:z1] = disk.T
    else:
        y0, y1 = max(0, y - radius), min(y_count, y + radius + 1)
        x0, x1 = max(0, x - radius), min(x_count, x + radius + 1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        disk = (yy - y) ** 2 + (xx - x) ** 2 <= radius ** 2
        scribble[x0:x1, y0:y1, z] = disk.T
    return scribble


def run() -> None:
    args = parse_args()
    source = sitk.ReadImage(args.image)
    array_zyx = np.asarray(sitk.GetArrayFromImage(source))
    # Use semantic x,y,z coordinates for the prompt API and transpose back on save.
    image_xyz = np.transpose(array_zyx, (2, 1, 0))[None]
    model_path = Path(args.model_path) if args.model_path else ensure_model_available(args.model)
    session = nnInteractiveInferenceSession(
        device=torch.device("cuda:0" if torch.cuda.is_available() else "cpu"),
        use_torch_compile=False,
        verbose=False,
        do_autozoom=True,
    )
    session.initialize_from_trained_model_folder(str(model_path))
    session.set_image(image_xyz)
    target = torch.zeros(image_xyz.shape[1:], dtype=torch.uint8, device=session.device)
    session.set_target_buffer(target)
    prompts = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    initial_xyz = None
    if args.initial_mask:
        initial_source = sitk.ReadImage(args.initial_mask)
        initial_zyx = np.asarray(sitk.GetArrayFromImage(initial_source))
        if initial_zyx.shape != array_zyx.shape:
            raise ValueError(
                f"Initial mask shape {initial_zyx.shape} does not match image shape {array_zyx.shape}"
            )
        if not np.isfinite(initial_zyx).all():
            raise ValueError("Initial mask contains NaN or infinite values")
        initial_xyz = np.ascontiguousarray(
            np.transpose(initial_zyx != 0, (2, 1, 0)),
            dtype=np.uint8,
        )
        session.add_initial_seg_interaction(initial_xyz, run_prediction=not prompts)
    if not prompts and initial_xyz is None:
        raise ValueError("At least one prompt or an initial mask is required")
    for prompt in prompts:
        kind = prompt["kind"]
        include = bool(prompt.get("include", True))
        if kind == "point":
            z, y, x = [int(v) for v in prompt["voxel_zyx"]]
            radius = max(1, int(prompt.get("radius", 1)))
            if radius <= 1:
                session.add_point_interaction((x, y, z), include_interaction=include)
            else:
                point_scribble = point_scribble_xyz(
                    tuple(int(value) for value in image_xyz.shape[1:]),
                    (z, y, x),
                    str(prompt.get("orientation", "axial")),
                    radius,
                )
                session.add_scribble_interaction(point_scribble, include_interaction=include)
        elif kind == "box":
            session.add_bbox_interaction(
                bbox_from_points(prompt["start_zyx"], prompt["end_zyx"]),
                include_interaction=include,
            )
        elif kind == "scribble":
            scribble_xyz = np.zeros(image_xyz.shape[1:], dtype=np.uint8)
            for z, y, x in prompt["voxels_zyx"]:
                if 0 <= x < scribble_xyz.shape[0] and 0 <= y < scribble_xyz.shape[1] and 0 <= z < scribble_xyz.shape[2]:
                    scribble_xyz[x, y, z] = 1
            session.add_scribble_interaction(scribble_xyz, include_interaction=include)
        elif kind == "lasso":
            points = np.asarray(prompt["points_zyx"], dtype=int)
            if points.shape[0] < 3:
                raise ValueError("Lasso needs at least three points")
            orientation = prompt["orientation"]
            lasso_xyz = np.zeros(image_xyz.shape[1:], dtype=np.uint8)
            if orientation == "axial":
                rr, cc = polygon(points[:, 1], points[:, 2], shape=(image_xyz.shape[2], image_xyz.shape[1]))
                lasso_xyz[cc, rr, int(points[0, 0])] = 1
            elif orientation == "coronal":
                rr, cc = polygon(points[:, 0], points[:, 2], shape=(image_xyz.shape[3], image_xyz.shape[1]))
                lasso_xyz[cc, int(points[0, 1]), rr] = 1
            else:
                rr, cc = polygon(points[:, 0], points[:, 1], shape=(image_xyz.shape[3], image_xyz.shape[2]))
                lasso_xyz[int(points[0, 2]), cc, rr] = 1
            session.add_lasso_interaction(lasso_xyz, include_interaction=include)
        else:
            raise ValueError(f"Unsupported prompt kind in v0.1: {kind}")
    result_xyz = target.detach().cpu().numpy().astype(np.uint8)
    result_zyx = np.transpose(result_xyz, (2, 1, 0))
    output = sitk.GetImageFromArray(result_zyx)
    output.CopyInformation(source)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(output, args.output, useCompression=True)


if __name__ == "__main__":
    run()
