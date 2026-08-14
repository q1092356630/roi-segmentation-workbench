from __future__ import annotations

import io

import numpy as np
from PIL import Image


def image_slice(array: np.ndarray, orientation: str, index: int) -> np.ndarray:
    if orientation == "axial":
        return array[index]
    if orientation == "coronal":
        return array[::-1, index, :]
    return array[::-1, :, index]


def mask_slice(mask: np.ndarray, orientation: str, index: int) -> np.ndarray:
    return image_slice(mask, orientation, index).astype(bool, copy=False)


def boundary(layer: np.ndarray, thickness: int = 1) -> np.ndarray:
    source = layer.astype(bool, copy=False)
    interior = source.copy()
    for _ in range(max(1, int(thickness))):
        padded = np.pad(interior, 1, mode="constant", constant_values=False)
        interior = (
            padded[1:-1, 1:-1]
            & padded[:-2, 1:-1]
            & padded[2:, 1:-1]
            & padded[1:-1, :-2]
            & padded[1:-1, 2:]
        )
        if not np.any(interior):
            break
    return source & ~interior


def hex_color(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def blend(rgb: np.ndarray, layer: np.ndarray, color: tuple[int, int, int], alpha: float) -> None:
    if not np.any(layer):
        return
    source = rgb[layer].astype(np.float32)
    target = np.asarray(color, dtype=np.float32)
    rgb[layer] = np.clip(source * (1.0 - alpha) + target * alpha, 0, 255).astype(np.uint8)


def render_png(
    array: np.ndarray,
    masks: dict[int, np.ndarray],
    colors: dict[int, str],
    auto_baseline: dict[int, np.ndarray],
    ai_proposal: dict[int, np.ndarray],
    orientation: str,
    index: int,
    level: float,
    width: float,
    opacity: float,
    overlay_mode: str,
    boundary_width: int,
    show_baseline: bool,
    show_proposal: bool,
    hidden_label_ids: set[int] | None = None,
    label_opacities: dict[int, float] | None = None,
) -> bytes:
    data = image_slice(array, orientation, index).astype(np.float32, copy=False)
    low = float(level) - max(float(width), 1.0) / 2.0
    high = float(level) + max(float(width), 1.0) / 2.0
    gray = np.clip((data - low) / max(high - low, 1e-6), 0.0, 1.0)
    rgb = np.repeat((gray * 255).astype(np.uint8)[..., None], 3, axis=2)
    hidden_label_ids = hidden_label_ids or set()
    label_opacities = label_opacities or {}
    for label_id, mask in masks.items():
        if label_id in hidden_label_ids:
            continue
        layer = mask_slice(mask, orientation, index)
        if overlay_mode == "boundary":
            layer = boundary(layer, boundary_width)
        blend(rgb, layer, hex_color(colors.get(label_id, "#ff3b30")), label_opacities.get(label_id, opacity))
    if show_baseline:
        for mask in auto_baseline.values():
            layer = mask_slice(mask, orientation, index)
            if overlay_mode == "boundary":
                layer = boundary(layer, boundary_width)
            blend(rgb, layer, (0, 199, 190), min(opacity, 0.55))
    if show_proposal:
        for mask in ai_proposal.values():
            layer = mask_slice(mask, orientation, index)
            if overlay_mode == "boundary":
                layer = boundary(layer, boundary_width)
            blend(rgb, layer, (255, 214, 10), min(max(opacity, 0.35), 0.7))
    output = io.BytesIO()
    Image.fromarray(rgb).save(output, format="PNG", optimize=False)
    return output.getvalue()
