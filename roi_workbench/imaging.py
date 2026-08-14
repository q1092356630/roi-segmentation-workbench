from __future__ import annotations

import hashlib
import itertools
import math
import csv
import json
import shutil
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import SimpleITK as sitk

from .core import CaseRecord, VolumeData, VolumeGeometry, normalize_case_status


SUPPORTED_NIFTI = (".nii", ".nii.gz")
IGNORED_DIRS = {"roi", "_history", ".roi-workbench", "__pycache__"}
ROI_NAME_PREFIXES = ("mask.", "mask_", "roi_", "segmentation", "workspace_labels", "label_")
OBVIOUS_IMAGE_STEMS = {"image", "img", "ct", "mr", "mri", "pet", "t1", "t2", "adc", "dwi"}
ROI_SCAN_IGNORED_DIRS = {"_history", ".roi-workbench", "__pycache__"}
MAX_AUTODETECTED_LABELS = 64


def _contains_non_ascii(path: Path | str) -> bool:
    try:
        str(path).encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


def _nifti_suffix(path: Path) -> str:
    return ".nii.gz" if path.name.lower().endswith(".nii.gz") else path.suffix


def _sitk_read_file(path: Path) -> sitk.Image:
    if not _contains_non_ascii(path):
        return sitk.ReadImage(str(path))
    if not path.is_file():
        raise FileNotFoundError(path)
    with tempfile.TemporaryDirectory(prefix="roi-itk-read-") as temporary:
        staged = Path(temporary) / f"image{_nifti_suffix(path)}"
        shutil.copy2(path, staged)
        return sitk.ReadImage(str(staged))


def _sitk_write_file(image: sitk.Image, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not _contains_non_ascii(destination):
        sitk.WriteImage(image, str(destination), useCompression=True)
        return
    with tempfile.TemporaryDirectory(prefix="roi-itk-write-") as temporary:
        staged = Path(temporary) / f"output{_nifti_suffix(destination)}"
        sitk.WriteImage(image, str(staged), useCompression=True)
        shutil.copy2(staged, destination)


def is_nifti(path: Path) -> bool:
    return path.name.lower().endswith(SUPPORTED_NIFTI)


def is_probable_roi_file(path: Path) -> bool:
    name = path.name.lower()
    stem = nifti_stem(path).lower()
    return (
        any(name.startswith(prefix) for prefix in ROI_NAME_PREFIXES)
        or stem == "roi"
        or stem.endswith(("_roi", "-roi"))
    )


def _is_explicit_image_file(path: Path) -> bool:
    return is_nifti(path) and nifti_stem(path).lower() == "image"


def _is_obvious_image_file(path: Path) -> bool:
    stem = nifti_stem(path).lower()
    return stem in OBVIOUS_IMAGE_STEMS or any(
        stem.startswith(f"{prefix}_") or stem.startswith(f"{prefix}-")
        for prefix in OBVIOUS_IMAGE_STEMS
    )


@lru_cache(maxsize=4096)
def _nifti_label_profile_cached(path_text: str, size_bytes: int, modified_ns: int) -> tuple[bool, tuple[int, ...], tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    del size_bytes, modified_ns
    image = _sitk_read_file(Path(path_text))
    geometry = (
        tuple(int(value) for value in image.GetSize()),
        tuple(float(value) for value in image.GetSpacing()),
        tuple(float(value) for value in image.GetOrigin()),
        tuple(float(value) for value in image.GetDirection()),
    )
    if image.GetDimension() != 3 or image.GetNumberOfComponentsPerPixel() != 1:
        return False, *geometry

    values = np.asarray(sitk.GetArrayViewFromImage(image)).reshape(-1)
    if values.size == 0:
        return False, *geometry
    discovered: set[int] = set()
    chunk_size = 1_000_000
    for start in range(0, values.size, chunk_size):
        chunk = values[start:start + chunk_size]
        if not np.isfinite(chunk).all():
            return False, *geometry
        rounded = np.rint(chunk)
        if not np.allclose(chunk, rounded, atol=1e-6):
            return False, *geometry
        if float(rounded.min()) < 0 or float(rounded.max()) > np.iinfo(np.uint16).max:
            return False, *geometry
        discovered.update(int(value) for value in np.unique(rounded))
        if len(discovered) > MAX_AUTODETECTED_LABELS:
            return False, *geometry
    is_label_map = 0 in discovered and any(value > 0 for value in discovered)
    return is_label_map, *geometry


def _nifti_label_profile(path: Path) -> tuple[bool, tuple[int, ...], tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    try:
        stat = path.stat()
        return _nifti_label_profile_cached(str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    except (OSError, RuntimeError, ValueError):
        return False, (), (), (), ()


def is_mask_like_nifti(path: Path) -> bool:
    """Return True for a non-empty finite integer label map, independent of filename."""
    if not path.is_file() or not is_nifti(path):
        return False
    return _nifti_label_profile(path)[0]


def _read_nifti_header(path: Path) -> tuple[tuple[int, ...], tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    def read_information(staged_path: Path) -> tuple[tuple[int, ...], tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
        reader = sitk.ImageFileReader()
        reader.SetFileName(str(staged_path))
        reader.ReadImageInformation()
        return (
            tuple(int(value) for value in reader.GetSize()),
            tuple(float(value) for value in reader.GetSpacing()),
            tuple(float(value) for value in reader.GetOrigin()),
            tuple(float(value) for value in reader.GetDirection()),
        )

    if not _contains_non_ascii(path):
        return read_information(path)
    with tempfile.TemporaryDirectory(prefix="roi-itk-info-") as temporary:
        staged = Path(temporary) / f"header{_nifti_suffix(path)}"
        shutil.copy2(path, staged)
        return read_information(staged)


@lru_cache(maxsize=4096)
def _nifti_header_cached(path_text: str, size_bytes: int, modified_ns: int) -> tuple[tuple[int, ...], tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    del size_bytes, modified_ns
    return _read_nifti_header(Path(path_text))


def _nifti_header(path: Path) -> tuple[tuple[int, ...], tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    try:
        stat = path.stat()
        return _nifti_header_cached(str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    except (OSError, RuntimeError, ValueError):
        return (), (), (), ()


def _nifti_geometry_matches_files(reference: Path, candidate: Path, tolerance: float = 1e-4) -> bool:
    reference_geometry = _nifti_header(reference)
    candidate_geometry = _nifti_header(candidate)
    if not reference_geometry[0] or not candidate_geometry[0]:
        return False
    return (
        reference_geometry[0] == candidate_geometry[0]
        and np.allclose(reference_geometry[1], candidate_geometry[1], atol=tolerance)
        and np.allclose(reference_geometry[2], candidate_geometry[2], atol=tolerance)
        and np.allclose(reference_geometry[3], candidate_geometry[3], atol=tolerance)
    )


def nifti_stem(path: Path) -> str:
    name = path.name
    return name[:-7] if name.lower().endswith(".nii.gz") else path.stem


def file_hash(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def case_image_hash(case: CaseRecord, chunk_size: int = 1024 * 1024) -> str:
    if case.image_path.is_file():
        return file_hash(case.image_path, chunk_size)
    digest = hashlib.sha256()
    selected = next((item for item in dicom_series(case.image_path) if item[0] == case.series_uid), None)
    files = selected[2] if selected is not None else []
    for filename in files:
        path = Path(filename)
        digest.update(path.name.encode("utf-8", errors="replace"))
        with path.open("rb") as handle:
            while chunk := handle.read(chunk_size):
                digest.update(chunk)
    return digest.hexdigest() if files else ""


def case_source_stat_signature(case: CaseRecord) -> dict:
    if case.image_path.is_file():
        stat = case.image_path.stat()
        return {"path": str(case.image_path.resolve()), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    selected = next((item for item in dicom_series(case.image_path) if item[0] == case.series_uid), None)
    files = selected[2] if selected is not None else []
    entries = []
    for filename in files:
        path = Path(filename)
        stat = path.stat()
        entries.append((path.name, stat.st_size, stat.st_mtime_ns))
    return {"path": str(case.image_path.resolve()), "series_uid": case.series_uid, "files": entries}


def _geometry(image: sitk.Image, source: Path, modality: str = "", series_uid: str = "") -> VolumeGeometry:
    shape = tuple(int(v) for v in reversed(image.GetSize()))
    spacing = tuple(float(v) for v in image.GetSpacing())
    origin = tuple(float(v) for v in image.GetOrigin())
    direction = tuple(float(v) for v in image.GetDirection())
    matrix = np.asarray(direction, dtype=float).reshape(3, 3) @ np.diag(spacing)
    affine = np.eye(4, dtype=float)
    affine[:3, :3] = matrix
    affine[:3, 3] = origin
    return VolumeGeometry(
        shape_zyx=shape,
        spacing_xyz=spacing,
        origin_xyz=origin,
        direction=direction,
        source_path=str(source),
        modality=modality,
        series_uid=series_uid,
        affine=affine.tolist(),
    )


def _canonical_image(image: sitk.Image) -> tuple[sitk.Image, bool]:
    if image.GetDimension() != 3:
        raise ValueError(f"Only 3D images are supported, got {image.GetDimension()}D")
    oriented = sitk.DICOMOrient(image, "LPS")
    direction = np.asarray(oriented.GetDirection(), dtype=float).reshape(3, 3)
    changed = (
        oriented.GetSize() != image.GetSize()
        or not np.allclose(oriented.GetOrigin(), image.GetOrigin(), atol=1e-5)
        or not np.allclose(oriented.GetDirection(), image.GetDirection(), atol=1e-5)
    )
    if np.allclose(direction, np.eye(3), atol=1e-5):
        return oriented, changed

    # Oblique acquisitions need an orthogonal LPS grid for correctly named
    # axial/coronal/sagittal planes. Masks are resampled back to the untouched
    # source grid with nearest-neighbour interpolation when saved.
    corners = [
        oriented.TransformIndexToPhysicalPoint(tuple(int(v) for v in index))
        for index in itertools.product(*[(0, size - 1) for size in oriented.GetSize()])
    ]
    bounds = np.asarray(corners, dtype=float)
    origin = bounds.min(axis=0)
    extent = bounds.max(axis=0) - origin
    spacing = np.asarray(oriented.GetSpacing(), dtype=float)
    size = [max(1, int(math.ceil(extent[i] / spacing[i])) + 1) for i in range(3)]
    source_array = sitk.GetArrayViewFromImage(oriented)
    default_value = float(np.nanmin(source_array)) if source_array.size else 0.0
    canonical = sitk.Resample(
        oriented,
        size,
        sitk.Transform(),
        sitk.sitkLinear,
        tuple(float(v) for v in origin),
        tuple(float(v) for v in spacing),
        tuple(float(v) for v in np.eye(3).ravel()),
        default_value,
        oriented.GetPixelID(),
    )
    return canonical, True


def _volume_from_image(image: sitk.Image, source: Path, modality: str = "", series_uid: str = "") -> VolumeData:
    source_array = np.asarray(sitk.GetArrayFromImage(image))
    source_geometry = _geometry(image, source, modality, series_uid)
    working, reformatted = _canonical_image(image)
    return VolumeData(
        array_zyx=np.asarray(sitk.GetArrayFromImage(working)),
        geometry=_geometry(working, source, modality, series_uid),
        reference_image=working,
        source_array_zyx=source_array,
        source_geometry=source_geometry,
        source_reference_image=image,
        reformatted_for_display=reformatted,
    )


def read_nifti(path: Path) -> VolumeData:
    image = _sitk_read_file(path)
    return _volume_from_image(image, path)


def dicom_series(path: Path) -> list[tuple[str, str, list[str]]]:
    if _contains_non_ascii(path):
        from pydicom import dcmread

        grouped: dict[str, tuple[str, list[tuple[tuple[float, float, str], str]]]] = {}
        for candidate in sorted(item for item in path.iterdir() if item.is_file()):
            try:
                header = dcmread(
                    str(candidate), stop_before_pixels=True,
                    specific_tags=[
                        "SeriesInstanceUID", "SeriesDescription", "InstanceNumber",
                        "ImagePositionPatient", "ImageOrientationPatient",
                    ],
                )
                uid = str(header.SeriesInstanceUID)
                description = str(getattr(header, "SeriesDescription", ""))
                position = getattr(header, "ImagePositionPatient", None)
                orientation = getattr(header, "ImageOrientationPatient", None)
                instance = float(getattr(header, "InstanceNumber", 0))
                if position is not None and len(position) >= 3 and orientation is not None and len(orientation) >= 6:
                    row = np.asarray(orientation[:3], dtype=float)
                    column = np.asarray(orientation[3:6], dtype=float)
                    normal = np.cross(row, column)
                    norm = float(np.linalg.norm(normal))
                    if norm > 1e-8:
                        distance = float(np.dot(np.asarray(position[:3], dtype=float), normal / norm))
                    else:
                        distance = instance
                elif position is not None and len(position) >= 3:
                    distance = float(position[2])
                else:
                    distance = instance
                order = (distance, instance, candidate.name)
                grouped.setdefault(uid, (description, []))[1].append((order, str(candidate)))
            except Exception:
                continue
        return [
            (uid, description, [filename for _order, filename in sorted(files, key=lambda item: item[0])])
            for uid, (description, files) in sorted(grouped.items())
        ]

    series_ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(path)) or []
    result: list[tuple[str, str, list[str]]] = []
    for uid in series_ids:
        files = list(sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(path), uid))
        if not files:
            continue
        description = ""
        try:
            first = _sitk_read_file(Path(files[0]))
            description = first.GetMetaData("0008|103e") if first.HasMetaDataKey("0008|103e") else ""
        except Exception:
            pass
        result.append((uid, description, files))
    return result


def read_dicom_series(directory: Path, series_uid: str | None = None) -> VolumeData:
    series = dicom_series(directory)
    if not series:
        raise FileNotFoundError(f"No DICOM series found under {directory}")
    if series_uid:
        selected = next((item for item in series if item[0] == series_uid), None)
        if selected is None:
            raise FileNotFoundError(f"DICOM series UID {series_uid} is no longer present under {directory}")
    else:
        selected = series[0]
    uid, _description, files = selected
    modality = "DICOM"
    try:
        from pydicom import dcmread
        header = dcmread(files[0], stop_before_pixels=True, specific_tags=["Modality"])
        candidate_modality = str(getattr(header, "Modality", "")).upper()
        if candidate_modality:
            modality = candidate_modality
    except Exception:
        pass
    reader = sitk.ImageSeriesReader()
    if any(_contains_non_ascii(filename) for filename in files):
        with tempfile.TemporaryDirectory(prefix="roi-dicom-read-") as temporary:
            staged_files = []
            for index, filename in enumerate(files):
                staged = Path(temporary) / f"{index:06d}.dcm"
                shutil.copy2(filename, staged)
                staged_files.append(str(staged))
            reader.SetFileNames(staged_files)
            image = reader.Execute()
    else:
        reader.SetFileNames(files)
        image = reader.Execute()
    return _volume_from_image(image, directory, modality=modality, series_uid=uid)


def read_volume(case: CaseRecord) -> VolumeData:
    if case.kind == "dicom":
        return read_dicom_series(case.image_path, case.series_uid)
    return read_nifti(case.image_path)


def _nifti_in(directory: Path) -> list[Path]:
    candidates = sorted(
        path for path in directory.iterdir()
        if path.is_file()
        and is_nifti(path)
        and not is_probable_roi_file(path)
    )
    explicit_images = [path for path in candidates if _is_explicit_image_file(path)]
    if explicit_images:
        return explicit_images
    return [path for path in candidates if _is_obvious_image_file(path) or not is_mask_like_nifti(path)]


def _recursive_nifti(directory: Path) -> list[Path]:
    candidates = []
    for path in directory.rglob("*"):
        if not path.is_file() or not is_nifti(path) or is_probable_roi_file(path):
            continue
        if any(part.lower() in IGNORED_DIRS for part in path.relative_to(directory).parts[:-1]):
            continue
        candidates.append(path)
    explicit_images = sorted(path for path in candidates if _is_explicit_image_file(path))
    if explicit_images:
        return explicit_images
    return sorted(
        path for path in candidates
        if _is_obvious_image_file(path) or not is_mask_like_nifti(path)
    )


def _case_uses_explicit_image_contract(case: CaseRecord) -> bool:
    return case.kind == "nifti" and case.image_path.is_file() and _is_explicit_image_file(case.image_path)


def patient_roi_paths(case: CaseRecord) -> list[Path]:
    patient_dir = case.patient_dir.resolve()
    explicit_image_contract = _case_uses_explicit_image_contract(case)
    candidate_directories: set[Path] = {patient_dir}
    if case.image_path.is_file():
        candidate_directories.add(case.image_path.parent.resolve())
    try:
        for child in patient_dir.iterdir():
            if child.is_dir() and any(token in child.name.lower() for token in ("roi", "mask", "seg")):
                candidate_directories.add(child.resolve())
    except OSError:
        pass

    paths: set[Path] = set()
    for directory in candidate_directories:
        try:
            candidates = directory.iterdir() if directory == patient_dir else directory.rglob("*")
            for path in candidates:
                if not path.is_file() or not is_nifti(path):
                    continue
                resolved = path.resolve()
                if case.image_path.is_file() and resolved == case.image_path.resolve():
                    continue
                try:
                    relative = resolved.relative_to(patient_dir)
                except ValueError:
                    continue
                if any(part.lower() in ROI_SCAN_IGNORED_DIRS for part in relative.parts[:-1]):
                    continue
                in_named_roi_directory = directory != patient_dir
                if (
                    not in_named_roi_directory
                    and not explicit_image_contract
                    and not is_probable_roi_file(resolved)
                    and not is_mask_like_nifti(resolved)
                ):
                    continue
                paths.add(resolved)
        except OSError:
            continue
    return sorted(paths, key=lambda path: path.relative_to(patient_dir).as_posix().lower())


def is_completed_roi_path(case: CaseRecord, path: Path) -> bool:
    """Recognize a final ROI by label content and geometry, not by filename."""
    name = path.name.lower()
    if not is_nifti(path) or name in {"mask.nii", "mask.nii.gz", "workspace_labels.nii.gz"}:
        return False
    if name.startswith("roi_.") or ".stage." in name or name.startswith("."):
        return False
    try:
        relative = path.resolve().relative_to(case.patient_dir.resolve())
    except ValueError:
        return False
    if case.image_path.is_file() and path.resolve() == case.image_path.resolve():
        return False
    if any(part.lower() in ROI_SCAN_IGNORED_DIRS or part.lower() == "auto_baseline" for part in relative.parts[:-1]):
        return False
    in_formal_location = len(relative.parts) == 1 or any(part.lower() == "roi" for part in relative.parts[:-1])
    if not in_formal_location:
        return False
    explicit_image_contract = _case_uses_explicit_image_contract(case)
    known_label_name = is_probable_roi_file(path) or explicit_image_contract
    if not known_label_name and not is_mask_like_nifti(path):
        return False
    if explicit_image_contract:
        return True
    if case.kind == "nifti" and case.image_path.is_file():
        return _nifti_geometry_matches_files(case.image_path, path)
    return True


def _may_contain_dicom(directory: Path) -> bool:
    try:
        files = [path for path in directory.iterdir() if path.is_file()]
    except OSError:
        return False
    for path in files:
        if is_nifti(path):
            continue
        if path.suffix.lower() in {".dcm", ".dicom", ".ima", ""}:
            return True
        try:
            with path.open("rb") as handle:
                header = handle.read(132)
            if len(header) >= 132 and header[128:132] == b"DICM":
                return True
        except OSError:
            continue
    return False


def scan_cases(root: Path) -> list[CaseRecord]:
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    cases: list[CaseRecord] = []
    direct_images = _nifti_in(root)
    if direct_images:
        for image in direct_images:
            cases.append(CaseRecord(nifti_stem(image), root, image, "nifti", dataset_root=root))

    for patient_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name.lower() not in IGNORED_DIRS):
        images = _recursive_nifti(patient_dir)
        if images:
            for image in images:
                relative = image.relative_to(patient_dir)
                relative_id = (relative.parent / nifti_stem(image)).as_posix()
                case_id = f"{patient_dir.name}/{relative_id}"
                cases.append(CaseRecord(case_id, patient_dir, image, "nifti", dataset_root=root))
        seen_uids: set[str] = set()
        for dicom_dir in [patient_dir, *(p for p in patient_dir.rglob("*") if p.is_dir())]:
            if any(part.lower() in IGNORED_DIRS for part in dicom_dir.relative_to(patient_dir).parts):
                continue
            if not _may_contain_dicom(dicom_dir):
                continue
            for uid, description, _files in dicom_series(dicom_dir):
                if uid in seen_uids:
                    continue
                seen_uids.add(uid)
                stable_uid = hashlib.sha256(uid.encode("utf-8")).hexdigest()[:10]
                case_id = f"{patient_dir.name}/series-{stable_uid}"
                cases.append(CaseRecord(case_id, patient_dir, dicom_dir, "dicom", uid, description, dataset_root=root))
    _hydrate_case_statuses(cases, root)
    return cases


def _hydrate_case_statuses(cases: list[CaseRecord], root: Path) -> None:
    statuses: dict[str, str] = {}
    manifest = root / "roi_manifest.csv"
    if manifest.is_file():
        try:
            with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
                statuses = {
                    row["case_id"]: normalize_case_status(row.get("status", "未开始"))
                    for row in csv.DictReader(handle)
                    if row.get("case_id")
                }
        except (OSError, KeyError, csv.Error):
            statuses = {}
    for case in cases:
        case.status = statuses.get(case.case_id, case.status)
        project = case.output_dir() / "roi_project.json"
        if project.is_file():
            try:
                project_status = json.loads(project.read_text(encoding="utf-8")).get("status", case.status)
                case.status = normalize_case_status(project_status, case.status)
            except (OSError, ValueError):
                pass
        safe_case = case.case_id.replace("/", "__").replace("\\", "__")
        recovery = case.patient_dir / ".roi-workbench" / "recovery" / f"{safe_case}.npz"
        if recovery.is_file():
            case.status = "修补中"
        elif case.status != "失败":
            has_formal_roi = any(is_completed_roi_path(case, path) for path in patient_roi_paths(case))
            if has_formal_roi:
                case.status = "已完成"
            elif case.status == "已完成":
                case.status = "未开始"


def geometry_matches(a: VolumeGeometry, b: VolumeGeometry, tolerance: float = 1e-4) -> bool:
    if a.shape_zyx != b.shape_zyx:
        return False
    return (
        np.allclose(a.spacing_xyz, b.spacing_xyz, atol=tolerance)
        and np.allclose(a.origin_xyz, b.origin_xyz, atol=tolerance)
        and np.allclose(a.direction, b.direction, atol=tolerance)
    )


def write_like(
    reference: sitk.Image,
    array_zyx: np.ndarray,
    destination: Path,
    source_nifti: Path | None = None,
) -> None:
    image = sitk.GetImageFromArray(np.asarray(array_zyx))
    image.CopyInformation(reference)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _sitk_write_file(image, destination)
    if source_nifti is not None and source_nifti.is_file() and is_nifti(source_nifti):
        # SimpleITK preserves the physical grid. Copy the original NIfTI qform/
        # sform matrices and codes as well, including the uncommon case where
        # they intentionally differ.
        import nibabel as nib

        source = nib.load(str(source_nifti))
        written = nib.load(str(destination))
        qform, qcode = source.get_qform(coded=True)
        sform, scode = source.get_sform(coded=True)
        if qform is not None:
            written.set_qform(qform, int(qcode))
        if sform is not None:
            written.set_sform(sform, int(scode))
        nib.save(written, str(destination))


def write_mask_on_source_grid(
    volume: VolumeData,
    array_zyx: np.ndarray,
    destination: Path,
    source_nifti: Path | None = None,
) -> None:
    working = sitk.GetImageFromArray(np.asarray(array_zyx))
    working.CopyInformation(volume.reference_image)
    source_reference = volume.source_reference_image if volume.source_reference_image is not None else volume.reference_image
    if volume.source_geometry is not None and not geometry_matches(volume.geometry, volume.source_geometry):
        output = sitk.Resample(
            working,
            source_reference,
            sitk.Transform(),
            sitk.sitkNearestNeighbor,
            0,
            working.GetPixelID(),
        )
    else:
        output = working
    destination.parent.mkdir(parents=True, exist_ok=True)
    _sitk_write_file(output, destination)
    if source_nifti is not None and source_nifti.is_file() and is_nifti(source_nifti):
        import nibabel as nib

        source = nib.load(str(source_nifti))
        written = nib.load(str(destination))
        qform, qcode = source.get_qform(coded=True)
        sform, scode = source.get_sform(coded=True)
        if qform is not None:
            written.set_qform(qform, int(qcode))
        if sform is not None:
            written.set_sform(sform, int(scode))
        nib.save(written, str(destination))


def load_mask(path: Path, reference: VolumeData) -> np.ndarray:
    mask_image = _sitk_read_file(path)
    mask = np.asarray(sitk.GetArrayFromImage(mask_image))
    mask_geometry = _geometry(mask_image, path)
    if not np.isfinite(mask).all():
        raise ValueError(f"Mask contains NaN or infinite values: {path}")
    if np.any(mask < 0) or np.any(mask > np.iinfo(np.uint16).max):
        raise ValueError(f"Mask label is outside uint16 range: {path}")
    if not np.allclose(mask, np.rint(mask), atol=1e-6):
        raise ValueError(f"Mask contains non-integer label values: {path}")
    if geometry_matches(mask_geometry, reference.geometry):
        return mask.astype(np.uint16, copy=False)
    if reference.source_geometry is not None and geometry_matches(mask_geometry, reference.source_geometry):
        resampled = sitk.Resample(
            mask_image,
            reference.reference_image,
            sitk.Transform(),
            sitk.sitkNearestNeighbor,
            0,
            sitk.sitkUInt16,
        )
        return np.asarray(sitk.GetArrayFromImage(resampled), dtype=np.uint16)
    raise ValueError(f"Mask geometry does not match source or display grid: {path}")
