from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import nibabel as nib
import SimpleITK as sitk
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom import dcmread
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from roi_workbench.core import CaseRecord, LabelDefinition, combine_masks
from roi_workbench.imaging import (
    case_image_hash,
    is_probable_roi_file,
    load_mask,
    patient_roi_paths,
    read_nifti,
    read_volume,
    scan_cases,
)
from roi_workbench.models import (
    NnInteractiveClient,
    NnInteractivePromptEngine,
    _hidden_console_process_kwargs,
    discover_models,
)
from roi_workbench.storage import labels_from_rows, load_recovery, save_case, save_recovery


class RoiWorkbenchTests(unittest.TestCase):
    def make_image(self, directory: Path, name: str = "ct.nii.gz") -> Path:
        array = np.arange(12 * 16 * 20, dtype=np.int16).reshape(12, 16, 20)
        image = sitk.GetImageFromArray(array)
        image.SetSpacing((0.75, 0.8, 2.5))
        image.SetOrigin((11.0, -7.0, 42.0))
        path = directory / name
        sitk.WriteImage(image, str(path), useCompression=True)
        return path

    def make_dicom_series(self, directory: Path, series_uid: str, value: int) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        study_uid = generate_uid()
        for index in range(3):
            meta = FileMetaDataset()
            meta.MediaStorageSOPClassUID = CTImageStorage
            meta.MediaStorageSOPInstanceUID = generate_uid()
            meta.TransferSyntaxUID = ExplicitVRLittleEndian
            dataset = FileDataset(str(directory / f"{index:03d}.dcm"), {}, file_meta=meta, preamble=b"\0" * 128)
            dataset.SOPClassUID = CTImageStorage
            dataset.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
            dataset.StudyInstanceUID = study_uid
            dataset.SeriesInstanceUID = series_uid
            dataset.Modality = "CT"
            dataset.SeriesDescription = "Test CT"
            dataset.PatientName = "Test"
            dataset.PatientID = "P001"
            dataset.Rows = 8
            dataset.Columns = 10
            dataset.InstanceNumber = index + 1
            dataset.ImagePositionPatient = [0.0, 0.0, float(index) * 2.5]
            dataset.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
            dataset.PixelSpacing = [0.8, 0.9]
            dataset.SliceThickness = 2.5
            dataset.SamplesPerPixel = 1
            dataset.PhotometricInterpretation = "MONOCHROME2"
            dataset.BitsAllocated = 16
            dataset.BitsStored = 16
            dataset.HighBit = 15
            dataset.PixelRepresentation = 1
            dataset.RescaleIntercept = 0
            dataset.RescaleSlope = 1
            pixels = np.full((8, 10), value + index, dtype=np.int16)
            dataset.PixelData = pixels.tobytes()
            dataset.save_as(directory / f"{index:03d}.dcm", write_like_original=False)

    def test_scan_patient_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patient = root / "P001"
            patient.mkdir()
            self.make_image(patient)
            cases = scan_cases(root)
            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0].patient_dir, patient)

    def test_explicit_image_contract_treats_every_other_nifti_as_roi_without_voxel_profiling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patient = root / "P001"
            patient.mkdir()
            source_path = self.make_image(patient, "image.nii.gz")
            source = sitk.ReadImage(str(source_path))
            for name, value in (("roi.nii.gz", 1), ("abdominal_arteries_roi.nii.gz", 2)):
                mask = sitk.GetImageFromArray(np.full((12, 16, 20), value, dtype=np.uint8))
                mask.CopyInformation(source)
                sitk.WriteImage(mask, str(patient / name), useCompression=True)

            with patch(
                "roi_workbench.imaging.is_mask_like_nifti",
                side_effect=AssertionError("明确 image/ROI 目录不应在扫描阶段读取完整体素"),
            ), patch(
                "roi_workbench.imaging._nifti_geometry_matches_files",
                side_effect=AssertionError("明确 image/ROI 目录应在实际载入时再校验几何"),
            ):
                cases = scan_cases(root)
                self.assertEqual(len(cases), 1)
                self.assertEqual(cases[0].image_path, source_path)
                self.assertEqual(
                    {path.name for path in patient_roi_paths(cases[0])},
                    {"roi.nii.gz", "abdominal_arteries_roi.nii.gz"},
                )

            self.assertTrue(is_probable_roi_file(Path("roi.nii.gz")))
            self.assertTrue(is_probable_roi_file(Path("abdominal_arteries_roi.nii.gz")))

    def test_legacy_completed_status_without_formal_roi_resets_to_not_started(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patient = root / "P001"
            patient.mkdir()
            self.make_image(patient)
            (root / "roi_manifest.csv").write_text(
                "case_id,status\nP001/ct,已审核\n",
                encoding="utf-8",
            )
            cases = scan_cases(root)
            self.assertEqual(cases[0].status, "未开始")

    def test_nested_same_named_series_have_unique_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patient = root / "P001"
            (patient / "arterial").mkdir(parents=True)
            (patient / "venous").mkdir(parents=True)
            self.make_image(patient / "arterial")
            self.make_image(patient / "venous")
            cases = scan_cases(root)
            self.assertEqual(len(cases), 2)
            self.assertEqual(len({case.case_id for case in cases}), 2)
            self.assertTrue(any("arterial" in case.case_id for case in cases))
            self.assertTrue(any("venous" in case.case_id for case in cases))

    def test_dicom_multiseries_scan_is_stable_and_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patient = root / "P001"
            self.make_dicom_series(patient / "arterial", generate_uid(), 10)
            self.make_dicom_series(patient / "venous", generate_uid(), 20)
            first = scan_cases(root)
            second = scan_cases(root)
            self.assertEqual(len(first), 2)
            self.assertEqual([case.case_id for case in first], [case.case_id for case in second])
            volume = read_volume(first[0])
            self.assertEqual(volume.array_zyx.shape, (3, 8, 10))
            self.assertEqual(volume.source_geometry.modality, "CT")
            self.assertTrue(case_image_hash(first[0]))

    def test_unicode_sagittal_dicom_is_sorted_along_slice_normal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "中文数据"
            patient = root / "P001"
            series = patient / "矢状位"
            uid = generate_uid()
            self.make_dicom_series(series, uid, 10)
            datasets = []
            for index, path in enumerate(sorted(series.glob("*.dcm"))):
                dataset = dcmread(str(path))
                dataset.ImageOrientationPatient = [0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
                dataset.ImagePositionPatient = [float(index) * 2.5, 0.0, 0.0]
                datasets.append(dataset)
                path.unlink()
            for index, dataset in enumerate(datasets):
                dataset.save_as(series / f"{2 - index:03d}.dcm", write_like_original=False)

            cases = scan_cases(root)
            self.assertEqual(len(cases), 1)
            volume = read_volume(cases[0])
            np.testing.assert_array_equal(volume.source_array_zyx[:, 0, 0], np.array([10, 11, 12]))
            np.testing.assert_allclose(volume.source_geometry.origin_xyz, (0.0, 0.0, 0.0), atol=1e-6)

    def test_save_and_reload_preserves_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            patient = Path(tmp) / "P001"
            patient.mkdir()
            source = self.make_image(patient)
            volume = read_nifti(source)
            mask = np.zeros(volume.array_zyx.shape, dtype=bool)
            mask[3:6, 4:8, 5:10] = True
            case = CaseRecord("P001", patient, source)
            output = save_case(
                case,
                volume,
                {1: mask},
                [LabelDefinition(1, "tumor")],
                "已完成",
            )
            restored = load_mask(output / "segmentation_labels.nii.gz", volume)
            np.testing.assert_array_equal(restored, mask.astype(np.uint16))
            self.assertEqual(sitk.ReadImage(str(output / "segmentation_labels.nii.gz")).GetSpacing(), volume.reference_image.GetSpacing())

    def test_oblique_display_is_canonical_and_final_mask_returns_to_source_grid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            patient = Path(tmp) / "P001"
            patient.mkdir()
            source = patient / "oblique.nii.gz"
            image = sitk.GetImageFromArray(np.zeros((10, 12, 14), dtype=np.int16))
            angle = np.deg2rad(15.0)
            image.SetDirection((np.cos(angle), -np.sin(angle), 0.0, np.sin(angle), np.cos(angle), 0.0, 0.0, 0.0, 1.0))
            image.SetSpacing((0.8, 1.1, 2.5))
            image.SetOrigin((3.0, -9.0, 22.0))
            sitk.WriteImage(image, str(source), True)
            volume = read_nifti(source)
            self.assertTrue(volume.reformatted_for_display)
            np.testing.assert_allclose(np.asarray(volume.reference_image.GetDirection()).reshape(3, 3), np.eye(3), atol=1e-6)
            mask = np.zeros(volume.array_zyx.shape, dtype=bool)
            mask[2:5, 3:7, 4:9] = True
            case = CaseRecord("P001/oblique", patient, source)
            output = save_case(case, volume, {1: mask}, [LabelDefinition(1, "roi")], "已完成")
            final_image = sitk.ReadImage(str(output / "segmentation_labels.nii.gz"))
            self.assertEqual(final_image.GetSize(), image.GetSize())
            np.testing.assert_allclose(final_image.GetSpacing(), image.GetSpacing())
            np.testing.assert_allclose(final_image.GetOrigin(), image.GetOrigin())
            np.testing.assert_allclose(final_image.GetDirection(), image.GetDirection())
            workspace = load_mask(output / "workspace_labels.nii.gz", volume)
            np.testing.assert_array_equal(workspace, mask.astype(np.uint16))

    def test_save_preserves_distinct_nifti_qform_and_sform(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            patient = Path(tmp) / "P001"
            patient.mkdir()
            source = patient / "forms.nii.gz"
            data = np.zeros((8, 9, 10), dtype=np.int16)
            qform = np.diag([0.8, 0.9, 2.0, 1.0])
            sform = qform.copy()
            sform[:3, 3] = [10.0, -4.0, 7.0]
            nifti = nib.Nifti1Image(data, sform)
            nifti.set_qform(qform, 1)
            nifti.set_sform(sform, 2)
            nib.save(nifti, str(source))
            volume = read_nifti(source)
            mask = np.zeros(volume.array_zyx.shape, dtype=bool)
            case = CaseRecord("P001/forms", patient, source)
            output = save_case(case, volume, {1: mask}, [LabelDefinition(1, "roi")], "待审核")
            restored = nib.load(str(output / "segmentation_labels.nii.gz"))
            np.testing.assert_allclose(restored.get_qform(), qform)
            np.testing.assert_allclose(restored.get_sform(), sform)
            self.assertEqual(int(restored.header["qform_code"]), 1)
            self.assertEqual(int(restored.header["sform_code"]), 2)

    def test_overlap_priority(self) -> None:
        shape = (4, 4, 4)
        first = np.zeros(shape, dtype=bool)
        second = np.zeros(shape, dtype=bool)
        first[1, 1, 1] = True
        second[1, 1, 1] = True
        second[2, 2, 2] = True
        combined, overlaps = combine_masks(
            {1: first, 2: second},
            shape,
            [LabelDefinition(1, "one", priority=0), LabelDefinition(2, "two", priority=1)],
        )
        self.assertEqual(overlaps, 1)
        self.assertEqual(int(combined[1, 1, 1]), 2)

    def test_rapid_saves_keep_distinct_history_and_remove_stale_label_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            patient = root / "P001"
            patient.mkdir()
            source = self.make_image(patient)
            volume = read_nifti(source)
            case = CaseRecord("P001/ct", patient, source, dataset_root=root)
            mask = np.zeros(volume.array_zyx.shape, dtype=bool)
            mask[1, 1, 1] = True
            with patch("roi_workbench.storage.datetime") as mocked_datetime:
                mocked_datetime.now.return_value = datetime(2026, 8, 5, 12, 0, 0, 123456)
                save_case(case, volume, {1: mask}, [LabelDefinition(1, "old_name")], "待审核")
                mask[2, 2, 2] = True
                save_case(case, volume, {1: mask}, [LabelDefinition(1, "new_name")], "修补中")
                mask[3, 3, 3] = True
                output = save_case(case, volume, {1: mask}, [LabelDefinition(1, "final_name")], "已完成")
            snapshots = list((output / "_history").iterdir())
            self.assertEqual(len(snapshots), 2)
            self.assertFalse((output / "roi_1_old_name.nii.gz").exists())
            self.assertFalse((output / "roi_1_new_name.nii.gz").exists())
            self.assertTrue((output / "roi_1_final_name.nii.gz").exists())
            self.assertTrue((root / "roi_manifest.csv").is_file())
            rescanned = scan_cases(root)
            self.assertEqual(rescanned[0].status, "已完成")

    def test_recovery_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            patient = Path(tmp) / "P001"
            patient.mkdir()
            source = self.make_image(patient)
            case = CaseRecord("P001/ct", patient, source)
            mask = np.zeros((12, 16, 20), dtype=bool)
            mask[2:4, 3:6, 5:9] = True
            volume = read_nifti(source)
            labels = [LabelDefinition(7, "tumor", "肿瘤", "#00ff00", "7", locked=True)]
            save_recovery(case, {7: mask}, volume, labels, {"proposal_labels": [7]})
            restored = load_recovery(case, volume)
            np.testing.assert_array_equal(restored.masks[7], mask)
            self.assertEqual(restored.labels[0].display_name, "肿瘤")
            self.assertTrue(restored.labels[0].locked)
            self.assertEqual(restored.project_state["proposal_labels"], [7])

    def test_label_ids_must_fit_uint16_and_exclude_background(self) -> None:
        with self.assertRaises(ValueError):
            labels_from_rows([])
        for invalid in (0, -1, 65536):
            with self.assertRaises(ValueError):
                labels_from_rows([{"id": invalid, "name": "invalid"}])

    def test_wsl_path_conversion(self) -> None:
        path = NnInteractiveClient._wsl_path(Path(r"C:\workspace\image.nii.gz"))
        self.assertEqual(path, "/mnt/c/workspace/image.nii.gz")

    def test_hidden_console_kwargs_are_windows_only(self) -> None:
        self.assertEqual(_hidden_console_process_kwargs("linux"), {})
        windows_kwargs = _hidden_console_process_kwargs("win32")
        self.assertEqual(windows_kwargs["creationflags"] & 0x08000000, 0x08000000)

    def test_nninteractive_forwards_hidden_console_options_to_probe_and_inference(self) -> None:
        hidden_options = {"creationflags": 0x08000000}
        probe_result = Mock(returncode=0, stdout="ok\n", stderr="")
        client = NnInteractiveClient()
        with patch(
            "roi_workbench.models._hidden_console_process_kwargs",
            return_value=hidden_options,
        ), patch("roi_workbench.models.subprocess.run", return_value=probe_result) as mocked_run:
            self.assertEqual(client.availability(), (True, "ok"))
        self.assertEqual(mocked_run.call_args.kwargs["creationflags"], 0x08000000)

        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            image_path = temporary / "image.nii.gz"
            output_path = temporary / "proposal.nii.gz"
            image_path.write_bytes(b"image")
            process = Mock()
            process.communicate.return_value = ("worker output", "")
            process.returncode = 0

            def launch_process(*_args, **_kwargs):
                output_path.write_bytes(b"mask")
                return process

            with patch.object(
                NnInteractiveClient,
                "_wsl_path",
                side_effect=lambda path: f"/mnt/m/{Path(path).name}",
            ), patch(
                "roi_workbench.models._hidden_console_process_kwargs",
                return_value=hidden_options,
            ), patch(
                "roi_workbench.models.subprocess.Popen",
                side_effect=launch_process,
            ) as mocked_popen:
                self.assertEqual(client.run(image_path, [{"kind": "point"}], output_path), output_path)
            self.assertEqual(mocked_popen.call_args.kwargs["creationflags"], 0x08000000)

    def test_nninteractive_engine_stages_3d_initial_mask(self) -> None:
        captured: dict[str, object] = {}

        class CapturingClient:
            def run(self, image_path, prompts, output_path, initial_mask_path=None):
                captured["prompts"] = list(prompts)
                captured["initial_mask_path"] = initial_mask_path
                staged = sitk.GetArrayFromImage(sitk.ReadImage(str(initial_mask_path)))
                captured["staged_mask"] = staged.copy()
                output_path.write_bytes(initial_mask_path.read_bytes())
                return output_path

            def cancel(self):
                return None

        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            image_path = self.make_image(temporary)
            volume = read_nifti(image_path)
            initial = np.zeros(volume.array_zyx.shape, dtype=bool)
            initial[2:7, 4:10, 5:12] = True
            case = CaseRecord("P001/ct", temporary, image_path)
            engine = NnInteractivePromptEngine(CapturingClient(), [], 1, initial)
            result = engine.predict(case, volume)

        self.assertEqual(captured["prompts"], [])
        self.assertIsNotNone(captured["initial_mask_path"])
        np.testing.assert_array_equal(captured["staged_mask"], initial.astype(np.uint8))
        np.testing.assert_array_equal(result.masks[1], initial)


if __name__ == "__main__":
    unittest.main()
