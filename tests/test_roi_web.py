from __future__ import annotations

import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import SimpleITK as sitk
from fastapi.testclient import TestClient

from roi_web.api import create_app
from roi_web.errors import ConflictError
from roi_web.workbench.state import TaskManager
from roi_workbench.core import LabelDefinition, PredictionResult


class RoiWebTests(unittest.TestCase):
    @staticmethod
    def session_headers(session: dict) -> dict[str, str]:
        return {
            "X-ROI-Case-ID": session["case_id"],
            "X-ROI-Session-ID": session["session_token"],
        }

    def make_unicode_dataset(self, temporary: Path) -> Path:
        root = temporary / "附一原位"
        patient = root / "PAT_001"
        patient.mkdir(parents=True)
        ascii_image = temporary / "source.nii.gz"
        ascii_mask = temporary / "source_mask.nii.gz"
        array = np.arange(8 * 12 * 16, dtype=np.int16).reshape(8, 12, 16)
        image = sitk.GetImageFromArray(array)
        image.SetSpacing((0.8, 1.1, 2.5))
        sitk.WriteImage(image, str(ascii_image), True)
        mask = np.zeros(array.shape, dtype=np.uint8)
        mask[2:5, 3:7, 4:9] = 1
        mask_image = sitk.GetImageFromArray(mask)
        mask_image.CopyInformation(image)
        sitk.WriteImage(mask_image, str(ascii_mask), True)
        shutil.copy2(ascii_image, patient / "image.nii.gz")
        shutil.copy2(ascii_mask, patient / "mask.nii.gz")
        return root

    def make_file_scoped_layer_dataset(self, temporary: Path) -> tuple[Path, Path, np.ndarray, np.ndarray]:
        root = temporary / "file-scoped-layers"
        patient = root / "PAT_LAYER_001"
        patient.mkdir(parents=True)
        image_array = np.arange(7 * 11 * 13, dtype=np.int16).reshape(7, 11, 13)
        image = sitk.GetImageFromArray(image_array)
        image.SetSpacing((0.9, 1.2, 2.2))
        sitk.WriteImage(image, str(patient / "image.nii.gz"), True)

        tumor = np.zeros(image_array.shape, dtype=np.uint8)
        tumor[1:4, 2:5, 3:7] = 1
        body = np.zeros(image_array.shape, dtype=np.uint8)
        body[4:6, 6:10, 7:12] = 1
        body[2:5, 7:9, 2:5] = 2
        for filename, array in (("roi_tumor.nii.gz", tumor), ("body_composition_roi.nii.gz", body)):
            mask = sitk.GetImageFromArray(array)
            mask.CopyInformation(image)
            sitk.WriteImage(mask, str(patient / filename), True)
        return root, patient, tumor, body

    def test_multiple_formal_roi_files_are_not_auto_selected_on_case_load(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root, patient, _tumor, _body = self.make_file_scoped_layer_dataset(Path(tmp))
            shutil.copy2(patient / "body_composition_roi.nii.gz", patient / "roi_body_composition.nii.gz")
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                loaded.raise_for_status()
                session = loaded.json()
                self.assertEqual(session["selected_roi_files"], [])
                self.assertTrue(session["editable_roi_source"].startswith("@working/"))
                self.assertTrue(any("未自动选择" in warning for warning in session["warnings"]))

    def test_roi_layers_are_scoped_by_source_file_and_source_label(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root, _patient, tumor, body = self.make_file_scoped_layer_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                loaded.raise_for_status()
                headers = self.session_headers(loaded.json())

                tumor_only = client.post("/api/roi/selection", headers=headers, json={
                    "relative_paths": ["roi_tumor.nii.gz"],
                    "discard_dirty": False,
                })
                self.assertEqual(tumor_only.status_code, 200, tumor_only.text)
                tumor_session = tumor_only.json()
                self.assertEqual(tumor_session["selected_roi_files"], ["roi_tumor.nii.gz"])
                self.assertEqual(
                    {(layer["source_file"], layer["source_label_id"]) for layer in tumor_session["layers"]},
                    {("roi_tumor.nii.gz", 1)},
                )
                self.assertEqual(int(client.app.state.service.require_loaded().masks[tumor_session["layers"][0]["id"]].sum()), int(tumor.sum()))

                both = client.post("/api/roi/selection", headers=headers, json={
                    "relative_paths": ["roi_tumor.nii.gz", "body_composition_roi.nii.gz"],
                    "discard_dirty": False,
                })
                self.assertEqual(both.status_code, 200, both.text)
                layers = both.json()["layers"]
                label_ones = [layer for layer in layers if layer["source_label_id"] == 1]
                self.assertEqual(len(label_ones), 2)
                self.assertEqual(len({layer["layer_key"] for layer in label_ones}), 2)
                self.assertEqual(len({layer["id"] for layer in label_ones}), 2)
                by_source = {layer["source_file"]: layer for layer in label_ones}
                loaded_case = client.app.state.service.require_loaded()
                self.assertEqual(int(loaded_case.masks[by_source["roi_tumor.nii.gz"]["id"]].sum()), int(tumor.sum()))
                self.assertEqual(int(loaded_case.masks[by_source["body_composition_roi.nii.gz"]["id"]].sum()), int((body == 1).sum()))

                recolored = client.post("/api/labels/color", headers=headers, json={
                    "label_id": by_source["roi_tumor.nii.gz"]["id"],
                    "layer_key": by_source["roi_tumor.nii.gz"]["layer_key"],
                    "color": "#ff00ff",
                })
                self.assertEqual(recolored.status_code, 200, recolored.text)
                colors = {layer["source_file"]: layer["color"] for layer in recolored.json()["layers"] if layer["source_label_id"] == 1}
                self.assertEqual(colors["roi_tumor.nii.gz"], "#ff00ff")
                self.assertNotEqual(colors["body_composition_roi.nii.gz"], "#ff00ff")

                mismatched_identity = client.post("/api/labels/color", headers=headers, json={
                    "label_id": by_source["roi_tumor.nii.gz"]["id"],
                    "layer_key": by_source["body_composition_roi.nii.gz"]["layer_key"],
                    "color": "#00ffff",
                })
                self.assertEqual(mismatched_identity.status_code, 409)

    def test_file_selection_clears_edit_target_and_export_only_writes_editable_file(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root, patient, tumor, body = self.make_file_scoped_layer_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                loaded.raise_for_status()
                headers = self.session_headers(loaded.json())

                editable = client.post("/api/roi/load-editable", headers=headers, json={
                    "relative_path": "roi_tumor.nii.gz",
                    "discard_dirty": False,
                })
                self.assertEqual(editable.status_code, 200, editable.text)
                selected = client.post("/api/roi/selection", headers=headers, json={
                    "relative_paths": ["roi_tumor.nii.gz", "body_composition_roi.nii.gz"],
                    "discard_dirty": False,
                })
                self.assertEqual(selected.status_code, 200, selected.text)
                session = selected.json()
                self.assertEqual(session["editable_roi_source"], "roi_tumor.nii.gz")
                tumor_layer = next(layer for layer in session["layers"] if layer["source_file"] == "roi_tumor.nii.gz" and layer["source_label_id"] == 1)
                body_layer = next(layer for layer in session["layers"] if layer["source_file"] == "body_composition_roi.nii.gz" and layer["source_label_id"] == 1)
                self.assertTrue(tumor_layer["editable"])
                self.assertFalse(body_layer["editable"])

                edited = client.post("/api/edit/stroke", headers=headers, json={
                    "orientation": "axial", "index": 0,
                    "label_id": tumor_layer["id"], "layer_key": tumor_layer["layer_key"],
                    "tool": "brush", "radius": 1, "points": [{"x": 1, "y": 1}],
                })
                self.assertEqual(edited.status_code, 200, edited.text)
                source_tumor_bytes = (patient / "roi_tumor.nii.gz").read_bytes()
                source_body_bytes = (patient / "body_composition_roi.nii.gz").read_bytes()
                exported = client.post("/api/export", headers=headers, json={"reviewed": False, "roi_name": "tumor_isolated"})
                self.assertEqual(exported.status_code, 200, exported.text)
                exported_array = sitk.GetArrayFromImage(sitk.ReadImage(exported.json()["output"]))
                self.assertEqual(int((exported_array == 1).sum()), int(tumor.sum()) + 5)
                self.assertFalse(np.any(exported_array == 2), "body-composition label 2 must not leak into tumor export")
                self.assertEqual((patient / "roi_tumor.nii.gz").read_bytes(), source_tumor_bytes)
                self.assertEqual((patient / "body_composition_roi.nii.gz").read_bytes(), source_body_bytes)

                body_only = client.post("/api/roi/selection", headers=headers, json={
                    "relative_paths": ["body_composition_roi.nii.gz"],
                    "discard_dirty": False,
                })
                self.assertEqual(body_only.status_code, 200, body_only.text)
                self.assertEqual(body_only.json()["editable_roi_source"], "")
                self.assertTrue(all(not layer["editable"] for layer in body_only.json()["layers"]))
                self.assertNotIn(tumor_layer["layer_key"], {layer["layer_key"] for layer in body_only.json()["layers"]})

    def test_selected_roi_can_be_moved_to_recycle_bin_without_touching_other_same_label_file(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root, patient, tumor, body = self.make_file_scoped_layer_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                loaded.raise_for_status()
                headers = self.session_headers(loaded.json())
                client.post("/api/roi/selection", headers=headers, json={
                    "relative_paths": ["roi_tumor.nii.gz", "body_composition_roi.nii.gz"],
                }).raise_for_status()

                moved: list[Path] = []
                def move_to_test_recycle_bin(value: str) -> None:
                    moved.append(Path(value))
                    Path(value).unlink()

                with patch.object(client.app.state.service, "_tumor_batch_is_active", return_value=False), patch(
                    "roi_web.workbench.service.send2trash", side_effect=move_to_test_recycle_bin,
                ):
                    deleted = client.post("/api/roi/delete", headers=headers, json={
                        "relative_path": "roi_tumor.nii.gz", "confirm": True, "request_id": 2,
                    })
                self.assertEqual(deleted.status_code, 200, deleted.text)
                self.assertEqual(moved, [patient / "roi_tumor.nii.gz"])
                self.assertFalse((patient / "roi_tumor.nii.gz").exists())
                self.assertTrue((patient / "body_composition_roi.nii.gz").exists())
                self.assertEqual(int(sitk.GetArrayFromImage(sitk.ReadImage(str(patient / "body_composition_roi.nii.gz"))).sum()), int(body.sum()))
                session = deleted.json()
                self.assertEqual(session["selected_roi_files"], ["body_composition_roi.nii.gz"])
                self.assertEqual({layer["source_file"] for layer in session["layers"]}, {"body_composition_roi.nii.gz"})
                self.assertEqual(session["editable_roi_source"], "")

    def test_tumor_roi_delete_is_blocked_while_batch_controller_is_active(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root, patient, _tumor, _body = self.make_file_scoped_layer_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                headers = self.session_headers(loaded.json())
                with patch.object(client.app.state.service, "_tumor_batch_is_active", return_value=True):
                    deleted = client.post("/api/roi/delete", headers=headers, json={
                        "relative_path": "roi_tumor.nii.gz", "confirm": True, "request_id": 2,
                    })
                self.assertEqual(deleted.status_code, 409)
                self.assertTrue((patient / "roi_tumor.nii.gz").exists())

    def test_stale_roi_delete_is_rejected_after_newer_file_selection(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root, patient, _tumor, _body = self.make_file_scoped_layer_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                headers = self.session_headers(loaded.json())
                client.post("/api/roi/selection", headers=headers, json={
                    "relative_paths": ["body_composition_roi.nii.gz"], "request_id": 3,
                }).raise_for_status()
                deleted = client.post("/api/roi/delete", headers=headers, json={
                    "relative_path": "roi_tumor.nii.gz", "confirm": True, "request_id": 2,
                })
                self.assertEqual(deleted.status_code, 409)
                self.assertTrue((patient / "roi_tumor.nii.gz").exists())

    def test_frontend_uses_file_scoped_layer_keys_for_selection_editing_and_3d(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with TestClient(create_app(project_root)) as client:
            html = client.get("/").text
            javascript = client.get("/static/app.js").text
            roi3d_js = client.get("/static/roi3d.js").text
        self.assertIn('id="roi-file-selection"', html)
        self.assertIn('id="roi-file-count-filter"', html)
        self.assertIn("selectedRoiFiles", javascript)
        self.assertIn("layer_key", javascript)
        self.assertIn("data-layer-key", javascript)
        self.assertIn("/api/roi/selection", javascript)
        self.assertIn("/api/roi/delete", javascript)
        self.assertIn("data-delete-roi-file", javascript)
        self.assertIn("const deleteRequestId = ++state.roiSelectionRequestId", javascript)
        self.assertIn("request_id: deleteRequestId", javascript)
        self.assertIn("updateSession(await api('/api/session'))", javascript)
        self.assertIn("syncLabelLock(); renderRoiLayers(); await refreshSlice();", javascript)
        self.assertIn("deleteRequestId !== state.roiSelectionRequestId", javascript)
        self.assertNotIn("ui.roiFileSelection?.addEventListener('contextmenu'", javascript)
        self.assertIn("roiSelectionRequestId", javascript)
        self.assertIn("request_id: requestId", javascript)
        self.assertIn("roiFileCountFilter", javascript)
        self.assertIn("String((item.files || []).length) === roiFileCount", javascript)
        self.assertIn("function displayRoiSource", javascript)
        self.assertIn("layer_key=${encodeURIComponent", javascript)
        self.assertNotIn("data-roi-3d-visibility=\"${labelId}\"", javascript)
        self.assertIn("layerKey: String(mesh.layer_key || '')", roi3d_js)

    @unittest.skip("全自动肿瘤模块不属于半自动公开版")
    def test_auto_then_interactive_tumor_output_stays_independent_from_body_label_one(self) -> None:
        project_root = Path(__file__).resolve().parents[1]

        class SyntheticAutoEngine:
            def predict(self, _case, volume):
                mask = np.zeros(volume.array_zyx.shape, dtype=bool)
                mask[1:3, 2:6, 3:8] = True
                return PredictionResult({1: mask}, "synthetic-auto", "test")

            def cancel(self):
                return None

        class SyntheticInteractiveEngine:
            def __init__(self, _client, _prompts, label_id, initial_mask=None):
                self.label_id = label_id
                self.initial_mask = initial_mask

            def predict(self, _case, volume):
                mask = np.zeros(volume.array_zyx.shape, dtype=bool)
                mask[2:5, 4:8, 5:10] = True
                return PredictionResult({self.label_id: mask}, "synthetic-interactive", "test")

            def cancel(self):
                return None

        with tempfile.TemporaryDirectory() as tmp:
            root, patient, _tumor, body = self.make_file_scoped_layer_dataset(Path(tmp))
            tumor_path = patient / "roi_tumor.nii.gz"
            body_path = patient / "body_composition_roi.nii.gz"
            tumor_bytes = tumor_path.read_bytes()
            body_bytes = body_path.read_bytes()
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                loaded.raise_for_status()
                headers = self.session_headers(loaded.json())
                editable = client.post("/api/roi/load-editable", headers=headers, json={"relative_path": "roi_tumor.nii.gz"})
                editable.raise_for_status()
                selected = client.post("/api/roi/selection", headers=headers, json={
                    "relative_paths": ["roi_tumor.nii.gz", "body_composition_roi.nii.gz"],
                })
                selected.raise_for_status()
                tumor_layer = next(layer for layer in selected.json()["layers"] if layer["source_file"] == "roi_tumor.nii.gz")
                body_layer = next(layer for layer in selected.json()["layers"] if layer["source_file"] == "body_composition_roi.nii.gz" and layer["source_label_id"] == 1)
                client.app.state.service.models["synthetic-auto"] = SyntheticAutoEngine()
                auto_task = client.post("/api/tasks/auto", headers=headers, json={"model_name": "synthetic-auto"})
                auto_task.raise_for_status()
                for _ in range(50):
                    status = client.get(f"/api/tasks/{auto_task.json()['id']}", headers=headers).json()["status"]
                    if status in {"completed", "failed", "cancelled"}:
                        break
                    time.sleep(0.02)
                self.assertEqual(status, "completed")
                client.post("/api/prompts", headers=headers, json={
                    "orientation": "axial", "index": 2, "kind": "positive",
                    "points": [{"x": 6, "y": 5}], "radius": 2,
                }).raise_for_status()
                with patch("roi_web.workbench.service.NnInteractivePromptEngine", SyntheticInteractiveEngine):
                    interactive_task = client.post("/api/tasks/interactive", headers=headers, json={
                        "label_id": tumor_layer["id"], "layer_key": tumor_layer["layer_key"],
                    })
                    interactive_task.raise_for_status()
                    for _ in range(50):
                        status = client.get(f"/api/tasks/{interactive_task.json()['id']}", headers=headers).json()["status"]
                        if status in {"completed", "failed", "cancelled"}:
                            break
                        time.sleep(0.02)
                self.assertEqual(status, "completed")
                session = client.get("/api/session", headers=headers).json()
                body_after = next(layer for layer in session["layers"] if layer["layer_key"] == body_layer["layer_key"])
                self.assertFalse(body_after["editable"])
                exported = client.post("/api/export", headers=headers, json={"roi_name": "tumor_refined", "reviewed": False})
                exported.raise_for_status()
                output = sitk.GetArrayFromImage(sitk.ReadImage(exported.json()["output"]))
                self.assertFalse(np.any(output == 2))
                self.assertEqual(int((output == 1).sum()), 3 * 4 * 5)
            self.assertEqual(tumor_path.read_bytes(), tumor_bytes)
            self.assertEqual(body_path.read_bytes(), body_bytes)
            self.assertTrue(np.any(body == 1))

    @unittest.skip("全自动肿瘤模块不属于半自动公开版")
    def test_auto_tumor_layer_does_not_merge_with_selected_body_composition_label_one(self) -> None:
        project_root = Path(__file__).resolve().parents[1]

        class SyntheticAutoEngine:
            def predict(self, _case, volume):
                mask = np.zeros(volume.array_zyx.shape, dtype=bool)
                mask[1:4, 3:7, 4:9] = True
                return PredictionResult({1: mask}, "arterial-tumor-auto", "test")

            def cancel(self):
                return None

        class SyntheticInteractiveEngine:
            def __init__(self, _client, _prompts, label_id, initial_mask=None):
                self.label_id = label_id

            def predict(self, _case, volume):
                mask = np.zeros(volume.array_zyx.shape, dtype=bool)
                mask[2:5, 4:8, 5:10] = True
                return PredictionResult({self.label_id: mask}, "arterial-tumor-refine", "test")

            def cancel(self):
                return None

        with tempfile.TemporaryDirectory() as tmp:
            root, patient, _tumor, body = self.make_file_scoped_layer_dataset(Path(tmp))
            body_path = patient / "body_composition_roi.nii.gz"
            body_bytes = body_path.read_bytes()
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                loaded.raise_for_status()
                headers = self.session_headers(loaded.json())
                selected = client.post("/api/roi/selection", headers=headers, json={
                    "relative_paths": ["body_composition_roi.nii.gz"],
                })
                selected.raise_for_status()
                self.assertTrue(all(not layer["editable"] for layer in selected.json()["layers"]))
                client.app.state.service.models["arterial-tumor-auto"] = SyntheticAutoEngine()
                auto_task = client.post("/api/tasks/auto", headers=headers, json={"model_name": "arterial-tumor-auto"})
                auto_task.raise_for_status()
                for _ in range(50):
                    status = client.get(f"/api/tasks/{auto_task.json()['id']}", headers=headers).json()["status"]
                    if status in {"completed", "failed", "cancelled"}:
                        break
                    time.sleep(0.02)
                self.assertEqual(status, "completed")
                after_auto = client.get("/api/session", headers=headers).json()
                label_ones = [layer for layer in after_auto["layers"] if layer["source_label_id"] == 1]
                self.assertEqual(len(label_ones), 2)
                self.assertEqual(len({layer["layer_key"] for layer in label_ones}), 2)
                body_layer = next(layer for layer in label_ones if layer["source_file"] == "body_composition_roi.nii.gz")
                tumor_layer = next(layer for layer in label_ones if layer["source_file"].startswith("@working/new_auto-"))
                self.assertFalse(body_layer["editable"])
                self.assertTrue(tumor_layer["editable"])
                self.assertEqual(after_auto["working_layer_kind"], "new_auto")
                client.post("/api/prompts", headers=headers, json={
                    "orientation": "axial", "index": 2, "kind": "positive",
                    "points": [{"x": 6, "y": 5}], "radius": 2,
                }).raise_for_status()
                with patch("roi_web.workbench.service.NnInteractivePromptEngine", SyntheticInteractiveEngine):
                    interactive_task = client.post("/api/tasks/interactive", headers=headers, json={
                        "label_id": tumor_layer["id"], "layer_key": tumor_layer["layer_key"],
                    })
                    interactive_task.raise_for_status()
                    for _ in range(50):
                        status = client.get(f"/api/tasks/{interactive_task.json()['id']}", headers=headers).json()["status"]
                        if status in {"completed", "failed", "cancelled"}:
                            break
                        time.sleep(0.02)
                self.assertEqual(status, "completed")
                exported = client.post("/api/export", headers=headers, json={"roi_name": "arterial_tumor", "reviewed": False})
                exported.raise_for_status()
                output = sitk.GetArrayFromImage(sitk.ReadImage(exported.json()["output"]))
                self.assertFalse(np.any(output == 2))
                self.assertEqual(int((output == 1).sum()), 3 * 4 * 5)
            self.assertEqual(body_path.read_bytes(), body_bytes)
            self.assertTrue(np.any(body == 1))

    def test_unicode_path_end_to_end_html_api(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                self.assertEqual(client.get("/health").status_code, 200)
                scan = client.post("/api/root", json={"path": str(root)})
                self.assertEqual(scan.status_code, 200, scan.text)
                self.assertEqual(scan.json()["case_count"], 1)
                root_info = client.get("/api/root")
                self.assertEqual(root_info.status_code, 200, root_info.text)
                self.assertEqual(Path(root_info.json()["root"]), root.resolve())
                self.assertEqual(root_info.json()["case_count"], 1)
                cases = client.get("/api/cases").json()["items"]
                self.assertEqual(len(cases), 1)
                self.assertNotIn("mask", cases[0]["case_id"].lower())
                self.assertEqual(cases[0]["patient_id"], "PAT_001")
                self.assertEqual(cases[0]["status"], "未开始")
                self.assertEqual([item["role"] for item in cases[0]["files"]], ["image", "mask"])
                loaded = client.post("/api/cases/load", json={"case_id": cases[0]["case_id"]})
                self.assertEqual(loaded.status_code, 200, loaded.text)
                headers = self.session_headers(loaded.json())
                self.assertEqual(loaded.json()["status"], "未开始")
                self.assertEqual(loaded.json()["reference_label_ids"], [60000])
                self.assertEqual(loaded.json()["shape_zyx"], [8, 12, 16])
                self.assertFalse(any("mask.nii.gz" in warning for warning in loaded.json()["warnings"]))
                self.assertIn(
                    "mask.nii.gz",
                    {item["relative_path"] for item in loaded.json()["available_roi_files"]},
                )
                png = client.get("/api/slice", params={"orientation": "axial", "index": 3, "level": 500, "width": 1000}, headers=headers)
                self.assertEqual(png.status_code, 200, png.text)
                self.assertTrue(png.content.startswith(b"\x89PNG"))
                image_only = client.get("/api/slice", params={
                    "orientation": "axial", "index": 3, "level": 500, "width": 1000,
                    "opacity": 0, "baseline": False, "proposal": False,
                }, headers=headers)
                hidden_roi = client.get("/api/slice", params={
                    "orientation": "axial", "index": 3, "level": 500, "width": 1000,
                    "opacity": 0.49, "baseline": False, "proposal": False, "hidden_labels": "1,60000",
                }, headers=headers)
                visible_roi = client.get("/api/slice", params={
                    "orientation": "axial", "index": 3, "level": 500, "width": 1000,
                    "opacity": 0.49, "baseline": False, "proposal": False,
                }, headers=headers)
                self.assertEqual(hidden_roi.content, image_only.content)
                self.assertNotEqual(visible_roi.content, image_only.content)
                service = client.app.state.service
                self.assertEqual(int(service.require_loaded().masks[1].sum()), 0)
                self.assertEqual(int(service.require_loaded().masks[60000].sum()), 60)
                invalid_visibility = client.get("/api/slice", params={
                    "orientation": "axial", "index": 3, "hidden_labels": "1,bad",
                }, headers=headers)
                self.assertEqual(invalid_visibility.status_code, 422)
                edit = client.post("/api/edit/stroke", headers=headers, json={
                    "orientation": "axial", "index": 3, "label_id": 1,
                    "tool": "brush", "radius": 2, "points": [{"x": 8, "y": 6}],
                })
                self.assertEqual(edit.status_code, 200, edit.text)
                self.assertTrue(edit.json()["dirty"])
                self.assertEqual(client.post("/api/edit/undo", headers=headers).status_code, 200)
                saved = client.post("/api/save", headers=headers, json={"reviewed": False})
                self.assertEqual(saved.status_code, 200, saved.text)
                self.assertTrue(Path(saved.json()["output"], "segmentation_labels.nii.gz").is_file())
                refreshed = client.get("/api/cases").json()["items"][0]
                saved_names = {item["name"] for item in refreshed["files"] if item["role"] == "saved_roi"}
                self.assertIn("segmentation_labels.nii.gz", saved_names)
                self.assertIn("roi_1_ROI.nii.gz", saved_names)

    def test_saved_roi_auto_loads_before_original_mask_and_keeps_mask_as_comparison(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = self.make_unicode_dataset(temporary)
            patient = root / "PAT_001"
            source_image = sitk.ReadImage(str(temporary / "source.nii.gz"))
            saved_array = np.zeros((8, 12, 16), dtype=np.uint8)
            saved_array[6, 8:10, 11:14] = 1
            saved_image = sitk.GetImageFromArray(saved_array)
            saved_image.CopyInformation(source_image)
            ascii_saved = temporary / "saved_roi.nii.gz"
            sitk.WriteImage(saved_image, str(ascii_saved), True)
            shutil.copy2(ascii_saved, patient / "roi_ROI.nii.gz")

            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case = client.get("/api/cases").json()["items"][0]
                self.assertEqual(case["status"], "已完成")
                loaded_response = client.post("/api/cases/load", json={"case_id": case["case_id"]})
                loaded_response.raise_for_status()
                session = loaded_response.json()
                self.assertEqual(session["status"], "已完成")
                self.assertFalse(session["dirty"])
                self.assertEqual(session["loaded_roi_source"], "roi_ROI.nii.gz")

                service = client.app.state.service
                loaded = service.require_loaded()
                self.assertEqual(int(loaded.masks[1].sum()), int(saved_array.sum()))
                self.assertEqual(len(session["reference_label_ids"]), 1)
                reference_id = session["reference_label_ids"][0]
                self.assertEqual(int(loaded.masks[reference_id].sum()), 60)
                self.assertTrue(next(label for label in session["labels"] if label["id"] == reference_id)["locked"])

    def test_session_refresh_discovers_vascular_roi_created_after_case_load(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = self.make_unicode_dataset(temporary)
            patient = root / "PAT_001"

            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                loaded.raise_for_status()
                headers = self.session_headers(loaded.json())
                self.assertNotIn(
                    "roi.nii.gz",
                    {item["relative_path"] for item in loaded.json()["available_roi_files"]},
                )

                source_image = sitk.ReadImage(str(temporary / "source.nii.gz"))
                vascular_array = np.zeros((8, 12, 16), dtype=np.uint8)
                vascular_array[2:7, 5:7, 7:10] = 1
                vascular_image = sitk.GetImageFromArray(vascular_array)
                vascular_image.CopyInformation(source_image)
                ascii_vascular = temporary / "vascular_roi.nii.gz"
                sitk.WriteImage(vascular_image, str(ascii_vascular), True)
                shutil.copy2(ascii_vascular, patient / "roi.nii.gz")

                refreshed = client.get("/api/session", headers=headers)
                self.assertEqual(refreshed.status_code, 200, refreshed.text)
                self.assertIn(
                    "roi.nii.gz",
                    {item["relative_path"] for item in refreshed.json()["available_roi_files"]},
                )

    def test_arbitrary_named_nifti_roi_is_discovered_completed_and_auto_loaded(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = self.make_unicode_dataset(temporary)
            patient = root / "PAT_001"
            source_image = sitk.ReadImage(str(temporary / "source.nii.gz"))
            roi_array = np.zeros((8, 12, 16), dtype=np.uint8)
            roi_array[1:4, 4:9, 6:12] = 1
            roi_image = sitk.GetImageFromArray(roi_array)
            roi_image.CopyInformation(source_image)
            ascii_roi = temporary / "arbitrary_roi_source.nii.gz"
            sitk.WriteImage(roi_image, str(ascii_roi), True)
            arbitrary_name = "医生最终勾画_A区.nii.gz"
            shutil.copy2(ascii_roi, patient / arbitrary_name)

            with TestClient(create_app(project_root)) as client:
                scan = client.post("/api/root", json={"path": str(root)})
                self.assertEqual(scan.status_code, 200, scan.text)
                cases = client.get("/api/cases").json()["items"]
                self.assertEqual(len(cases), 1, "任意名称 ROI 不得被误扫描成第二个影像病例")
                case = cases[0]
                self.assertEqual(case["status"], "已完成")
                self.assertIn(arbitrary_name, {item["relative_path"] for item in case["files"]})

                response = client.post("/api/cases/load", json={"case_id": case["case_id"]})
                self.assertEqual(response.status_code, 200, response.text)
                session = response.json()
                self.assertEqual(session["status"], "已完成")
                self.assertIn(arbitrary_name, {
                    item["relative_path"] for item in session["available_roi_files"]
                })
                loaded = client.app.state.service.require_loaded()
                self.assertEqual(int(loaded.masks[1].sum()), int(roi_array.sum()))
                self.assertEqual(loaded.provenance["loaded_roi"], arbitrary_name)

    def test_import_patient_masks_change_colors_and_adjust_boundary_width(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = self.make_unicode_dataset(temporary)
            patient = root / "PAT_001"
            masks_dir = patient / "Masks"
            masks_dir.mkdir()

            source_image = sitk.ReadImage(str(temporary / "source.nii.gz"))
            compare_array = np.zeros((8, 12, 16), dtype=np.uint8)
            compare_array[4, 2:10, 3:13] = 1
            compare_array[5, 4:8, 6:10] = 3
            compare_image = sitk.GetImageFromArray(compare_array)
            compare_image.CopyInformation(source_image)
            ascii_compare = temporary / "roi_compare.nii.gz"
            sitk.WriteImage(compare_image, str(ascii_compare), True)
            shutil.copy2(ascii_compare, masks_dir / "roi_compare.nii.gz")

            wrong_image = sitk.GetImageFromArray(compare_array)
            wrong_image.CopyInformation(source_image)
            wrong_image.SetOrigin((20.0, 0.0, 0.0))
            ascii_wrong = temporary / "roi_wrong.nii.gz"
            sitk.WriteImage(wrong_image, str(ascii_wrong), True)
            shutil.copy2(ascii_wrong, masks_dir / "roi_wrong.nii.gz")

            with TestClient(create_app(project_root)) as client:
                html = client.get("/").text
                self.assertIn('id="import-mask"', html)
                self.assertIn('id="label-color"', html)
                self.assertIn('data-overlay-mode="fill"', html)
                self.assertIn('data-overlay-mode="boundary"', html)
                self.assertIn('实心填充（推荐）', html)
                self.assertIn('中间空白仅为显示效果', html)
                self.assertIn('id="boundary-width"', html)
                self.assertIn('id="left-panel-resizer"', html)
                self.assertIn('id="right-panel-resizer"', html)
                self.assertIn('role="separator"', html)
                self.assertIn('id="trim-roi-left"', html)
                self.assertIn('id="trim-roi-right"', html)
                self.assertIn('id="range-operation-log"', html)
                self.assertIn('id="theme-select"', html)
                self.assertIn('id="render-3d"', html)
                self.assertIn('id="roi-3d-panel"', html)
                self.assertIn('id="roi-3d-canvas"', html)
                self.assertIn('id="roi-3d-roi-list"', html)
                self.assertIn('id="roi-3d-select-all"', html)
                self.assertIn('id="roi-3d-clear-all"', html)
                self.assertIn('id="roi-3d-opacity"', html)
                self.assertEqual(html.count('class="workflow-column"'), 2)
                self.assertIn('aria-label="显示与 ROI 来源"', html)
                self.assertIn('aria-label="AI 分割与修订"', html)
                app_js = client.get("/static/app.js").text
                styles = client.get("/static/styles.css").text
                roi3d_js = client.get("/static/roi3d.js")
                self.assertEqual(roi3d_js.status_code, 200, roi3d_js.text)
                self.assertIn("classList.toggle('empty-state', !patients.size)", app_js)
                self.assertIn("/api/roi-mesh", app_js)
                self.assertIn("Roi3DRenderer", app_js)
                self.assertIn("visibleRoiLabelIds", app_js)
                self.assertIn("selectedRoi3dLabelIds", app_js)
                self.assertIn("data-roi-3d-color", app_js)
                self.assertIn("getAttribute('data-roi-3d-visibility')", app_js)
                self.assertIn("getAttribute('data-roi-3d-color')", app_js)
                self.assertIn("Promise.allSettled", app_js)
                self.assertIn('WebGL2', roi3d_js.text)
                self.assertIn('ResizeObserver', roi3d_js.text)
                self.assertIn('setMeshes(meshes)', roi3d_js.text)
                self.assertIn('setMeshColor(labelId, hexColor)', roi3d_js.text)
                self.assertIn('[data-theme="light"]', styles)
                self.assertIn('.visualization-layout.show-3d', styles)
                self.assertIn("const PANEL_DEFAULTS = { left: 256, right: 520 };", app_js)
                self.assertIn("right: [300, 720]", app_js)
                self.assertIn(".roi-module-panel > .right-panel-scroll", styles)
                self.assertIn("repeat(auto-fit, minmax(230px, 1fr))", styles)
                self.assertIn(".case-list { flex: 1 1 auto; min-height: 0; overflow-y: auto", styles)
                self.assertIn(".left-panel { min-height: 0;", styles)

                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case = client.get("/api/cases").json()["items"][0]
                self.assertEqual(case["status"], "未开始")
                relative_paths = {item["relative_path"] for item in case["files"]}
                self.assertIn("Masks/roi_compare.nii.gz", relative_paths)
                loaded = client.post("/api/cases/load", json={"case_id": case["case_id"]})
                loaded.raise_for_status()
                headers = self.session_headers(loaded.json())
                available = {item["relative_path"] for item in loaded.json()["available_roi_files"]}
                self.assertIn("Masks/roi_compare.nii.gz", available)
                self.assertIn("Masks/roi_wrong.nii.gz", available)

                service = client.app.state.service
                drawn = client.post("/api/edit/stroke", headers=headers, json={
                    "orientation": "axial", "index": 3, "label_id": 1,
                    "tool": "brush", "radius": 2, "points": [{"x": 8, "y": 6}],
                })
                self.assertEqual(drawn.status_code, 200, drawn.text)
                original_sum = int(service.require_loaded().masks[1].sum())
                self.assertGreater(original_sum, 0)
                imported = client.post("/api/roi/import", headers=headers, json={
                    "relative_path": "Masks/roi_compare.nii.gz",
                })
                self.assertEqual(imported.status_code, 200, imported.text)
                self.assertEqual(imported.json()["imported_label_ids"], [60001, 60002])
                self.assertEqual(imported.json()["reference_label_ids"], [60000, 60001, 60002])
                self.assertEqual(int(service.require_loaded().masks[1].sum()), original_sum)
                self.assertEqual(int(service.require_loaded().masks[60001].sum()), int((compare_array == 1).sum()))
                self.assertEqual(int(service.require_loaded().masks[60002].sum()), int((compare_array == 3).sum()))
                self.assertTrue(next(label for label in imported.json()["labels"] if label["id"] == 60001)["locked"])

                cannot_unlock = client.post("/api/labels/lock", headers=headers, json={
                    "label_id": 60001, "locked": False,
                })
                self.assertEqual(cannot_unlock.status_code, 409, cannot_unlock.text)

                common = {
                    "orientation": "axial", "index": 4, "level": 500, "width": 1000,
                    "opacity": 0.8, "baseline": False, "proposal": False, "hidden_labels": "1,60000,60002",
                }
                before_color = client.get("/api/slice", params=common, headers=headers).content
                recolored = client.post("/api/labels/color", headers=headers, json={
                    "label_id": 60001, "color": "#ff00ff",
                })
                self.assertEqual(recolored.status_code, 200, recolored.text)
                self.assertEqual(next(label for label in recolored.json()["labels"] if label["id"] == 60001)["color"], "#ff00ff")
                after_color = client.get("/api/slice", params=common, headers=headers).content
                self.assertNotEqual(before_color, after_color)

                thin = client.get("/api/slice", params={**common, "mode": "boundary", "boundary_width": 1}, headers=headers)
                thick = client.get("/api/slice", params={**common, "mode": "boundary", "boundary_width": 4}, headers=headers)
                self.assertEqual(thin.status_code, 200, thin.text)
                self.assertEqual(thick.status_code, 200, thick.text)
                self.assertNotEqual(thin.content, thick.content)

                loaded_case = service.require_loaded()
                model_mask = np.zeros(loaded_case.volume.array_zyx.shape, dtype=bool)
                model_mask[3, 4:8, 5:10] = True
                with loaded_case.lock:
                    service._apply_prediction(
                        loaded_case,
                        PredictionResult({1: model_mask}, "nnInteractive", "test"),
                        interactive=True,
                    )
                self.assertEqual(service.session_info()["reference_label_ids"], [60000, 60001, 60002])

                exported = client.post("/api/export", headers=headers, json={
                    "reviewed": False, "roi_name": "新勾画",
                })
                self.assertEqual(exported.status_code, 200, exported.text)
                ascii_exported = temporary / "exported_without_references.nii.gz"
                shutil.copy2(exported.json()["output"], ascii_exported)
                exported_image = sitk.ReadImage(str(ascii_exported))
                exported_values = set(int(value) for value in np.unique(sitk.GetArrayFromImage(exported_image)))
                self.assertEqual(exported_values, {0, 1})

                before_ids = set(service.require_loaded().masks)
                wrong = client.post("/api/roi/import", headers=headers, json={
                    "relative_path": "Masks/roi_wrong.nii.gz",
                })
                self.assertEqual(wrong.status_code, 422, wrong.text)
                self.assertEqual(set(service.require_loaded().masks), before_ids)
                outside = client.post("/api/roi/import", headers=headers, json={"relative_path": "../outside.nii.gz"})
                self.assertEqual(outside.status_code, 422, outside.text)

    def test_keep_clicked_component_across_volume_is_undoable(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                service = client.app.state.service
                loaded = service.require_loaded()
                with loaded.lock:
                    loaded.masks[1][:] = False
                    loaded.masks[1][2:5, 2:5, 2:5] = True
                    loaded.masks[1][2:5, 8:11, 12:15] = True
                    before = loaded.masks[1].copy()

                kept = client.post("/api/edit/keep-component", headers=headers, json={
                    "orientation": "axial", "index": 3, "label_id": 1,
                    "point": {"x": 13, "y": 9},
                })
                self.assertEqual(kept.status_code, 200, kept.text)
                self.assertEqual(kept.json()["kept_voxels"], 27)
                self.assertEqual(kept.json()["removed_voxels"], 27)
                self.assertEqual(kept.json()["selected_slice_voxels"], 9)
                self.assertEqual(kept.json()["scope"], "volume")
                self.assertEqual(int(loaded.masks[1].sum()), 27)
                self.assertEqual(kept.json()["status"], "修补中")

                client.post("/api/edit/undo", headers=headers).raise_for_status()
                np.testing.assert_array_equal(loaded.masks[1], before)
                client.post("/api/edit/redo", headers=headers).raise_for_status()
                self.assertEqual(int(loaded.masks[1].sum()), 27)

                unchanged = loaded.masks[1].copy()
                outside = client.post("/api/edit/keep-component", headers=headers, json={
                    "orientation": "axial", "index": 3, "label_id": 1,
                    "point": {"x": 0, "y": 0},
                })
                self.assertEqual(outside.status_code, 422, outside.text)
                np.testing.assert_array_equal(loaded.masks[1], unchanged)

    def test_exclude_intensity_inside_roi_supports_slice_volume_and_undo(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                service = client.app.state.service
                loaded = service.require_loaded()
                with loaded.lock:
                    loaded.masks[1][:] = False
                    loaded.masks[1][2, 2:5, 3:7] = True
                    loaded.masks[1][5, 2:5, 3:7] = True
                    loaded.volume.array_zyx[2, 2:3, 3:7] = -900
                    loaded.volume.array_zyx[2, 3:5, 3:7] = 50
                    loaded.volume.array_zyx[5, 2:5, 3:7] = -100
                    before = loaded.masks[1].copy()

                air = client.post("/api/edit/exclude-intensity", headers=headers, json={
                    "orientation": "axial", "index": 2, "label_id": 1,
                    "scope": "slice", "minimum": None, "maximum": -500,
                })
                self.assertEqual(air.status_code, 200, air.text)
                self.assertEqual(air.json()["removed_voxels"], 4)
                self.assertEqual(int(loaded.masks[1][2].sum()), 8)
                self.assertEqual(int(loaded.masks[1][5].sum()), 12)
                client.post("/api/edit/undo", headers=headers).raise_for_status()
                np.testing.assert_array_equal(loaded.masks[1], before)

                fat = client.post("/api/edit/exclude-intensity", headers=headers, json={
                    "orientation": "axial", "index": 2, "label_id": 1,
                    "minimum": -190, "maximum": -30,
                })
                self.assertEqual(fat.status_code, 200, fat.text)
                self.assertEqual(fat.json()["removed_voxels"], 12)
                self.assertEqual(fat.json()["scope"], "volume")
                self.assertEqual(int(loaded.masks[1][2].sum()), 12)
                self.assertEqual(int(loaded.masks[1][5].sum()), 0)

                invalid = client.post("/api/edit/exclude-intensity", headers=headers, json={
                    "orientation": "axial", "index": 2, "label_id": 1,
                    "scope": "slice", "minimum": 100, "maximum": -100,
                })
                self.assertEqual(invalid.status_code, 422, invalid.text)

    def test_load_selected_patient_roi_as_editable_start_without_overwriting_source(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = self.make_unicode_dataset(temporary)
            patient = root / "PAT_001"
            source_image = sitk.ReadImage(str(temporary / "source.nii.gz"))
            auto_array = np.zeros((8, 12, 16), dtype=np.uint8)
            auto_array[4, 3:8, 5:11] = 1
            auto_image = sitk.GetImageFromArray(auto_array)
            auto_image.CopyInformation(source_image)
            ascii_auto = temporary / "auto_seg.nii.gz"
            sitk.WriteImage(auto_image, str(ascii_auto), True)
            editable_path = patient / "segmentation_auto.nii.gz"
            shutil.copy2(ascii_auto, editable_path)
            source_bytes = editable_path.read_bytes()

            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case = client.get("/api/cases").json()["items"][0]
                loaded_response = client.post("/api/cases/load", json={"case_id": case["case_id"]})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                loaded = client.app.state.service.require_loaded()
                self.assertEqual(int(loaded.masks[1].sum()), int(auto_array.sum()))
                self.assertEqual(loaded_response.json()["reference_label_ids"], [60000])

                editable = client.post("/api/roi/load-editable", headers=headers, json={
                    "relative_path": "segmentation_auto.nii.gz",
                })
                self.assertEqual(editable.status_code, 200, editable.text)
                session = editable.json()
                self.assertEqual(session["status"], "已完成")
                self.assertFalse(session["dirty"])
                self.assertEqual(session["editable_roi_source"], "segmentation_auto.nii.gz")
                self.assertEqual(session["auto_baseline_labels"], [1])
                self.assertEqual(session["reference_label_ids"], [])
                same_file_reference = client.post("/api/roi/load-interactive-reference", headers=headers, json={
                    "relative_path": "segmentation_auto.nii.gz",
                })
                self.assertEqual(same_file_reference.status_code, 409, same_file_reference.text)
                self.assertEqual(int(loaded.masks[1].sum()), int(auto_array.sum()))
                self.assertTrue(np.array_equal(loaded.auto_baseline[1], auto_array.astype(bool)))
                self.assertEqual(editable_path.read_bytes(), source_bytes)

                erased = client.post("/api/edit/stroke", headers=headers, json={
                    "orientation": "axial", "index": 4, "label_id": 1,
                    "tool": "eraser", "radius": 1, "points": [{"x": 7, "y": 5}],
                })
                self.assertEqual(erased.status_code, 200, erased.text)
                self.assertLess(int(loaded.masks[1].sum()), int(auto_array.sum()))
                self.assertEqual(erased.json()["status"], "修补中")

                restored = client.post("/api/proposals/merge", headers=headers, json={
                    "label_id": 1, "operation": "restore_baseline",
                })
                self.assertEqual(restored.status_code, 200, restored.text)
                self.assertEqual(int(loaded.masks[1].sum()), int(auto_array.sum()))
                self.assertEqual(editable_path.read_bytes(), source_bytes)

                semi_array = np.zeros_like(auto_array, dtype=bool)
                semi_array[5, 6:9, 8:12] = True
                with loaded.lock:
                    client.app.state.service._apply_prediction(
                        loaded,
                        PredictionResult({1: semi_array.copy()}, "nnInteractive", "test"),
                        interactive=True,
                    )
                self.assertTrue(np.array_equal(loaded.masks[1], semi_array))
                self.assertTrue(np.array_equal(loaded.auto_baseline[1], auto_array.astype(bool)))
                restored_loaded_source = client.post("/api/proposals/merge", headers=headers, json={
                    "label_id": 1, "operation": "restore_baseline",
                })
                self.assertEqual(restored_loaded_source.status_code, 200, restored_loaded_source.text)
                self.assertTrue(np.array_equal(loaded.masks[1], auto_array.astype(bool)))
                self.assertEqual(editable_path.read_bytes(), source_bytes)

    def test_new_roi_cleanup_controls_are_exposed_in_html_and_javascript(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with TestClient(create_app(project_root)) as client:
            html = client.get("/").text
            javascript = client.get("/static/app.js").text
            self.assertIn('data-tool="keep_component"', html)
            self.assertIn('id="load-editable-roi"', html)
            self.assertIn('id="load-interactive-reference"', html)
            self.assertIn('id="intensity-preset"', html)
            self.assertIn('id="exclude-intensity"', html)
            self.assertIn('/api/edit/keep-component', javascript)
            self.assertIn('/api/edit/exclude-intensity', javascript)
            self.assertIn('/api/roi/load-editable', javascript)
            self.assertIn('/api/roi/load-interactive-reference', javascript)

    def test_trim_current_roi_left_right_all_orientations_with_history_and_undo(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                service = client.app.state.service
                loaded = service.require_loaded()
                shape = loaded.volume.array_zyx.shape
                current = np.ones(shape, dtype=bool)
                other = np.zeros(shape, dtype=bool)
                other[1:3, 2:5, 4:7] = True
                with loaded.lock:
                    loaded.masks[1] = current.copy()
                    loaded.labels.append(LabelDefinition(2, "other", "Other", "#34c759"))
                    loaded.masks[2] = other.copy()

                axial_left = client.post("/api/edit/trim", headers=headers, json={
                    "orientation": "axial", "index": 3, "label_id": 1, "direction": "left",
                })
                self.assertEqual(axial_left.status_code, 200, axial_left.text)
                self.assertFalse(np.any(loaded.masks[1][:4]))
                self.assertTrue(np.all(loaded.masks[1][4:]))
                self.assertEqual(axial_left.json()["status"], "修补中")
                self.assertEqual(axial_left.json()["range_operation_log"][-1]["message"], "轴位第 4 层：当前层及滑动条左侧 ROI 已删除")
                self.assertIsNotNone(loaded.undo_stack[-1].region)
                self.assertEqual(loaded.undo_stack[-1].before.shape, (4, shape[1], shape[2]))

                client.post("/api/edit/undo", headers=headers).raise_for_status()
                self.assertTrue(np.all(loaded.masks[1]))
                client.post("/api/edit/redo", headers=headers).raise_for_status()
                self.assertFalse(np.any(loaded.masks[1][:4]))
                client.post("/api/edit/undo", headers=headers).raise_for_status()

                axial_right = client.post("/api/edit/trim", headers=headers, json={
                    "orientation": "axial", "index": 3, "label_id": 1, "direction": "right",
                })
                axial_right.raise_for_status()
                self.assertTrue(np.all(loaded.masks[1][:3]))
                self.assertFalse(np.any(loaded.masks[1][3:]))
                client.post("/api/edit/undo", headers=headers).raise_for_status()

                coronal_left = client.post("/api/edit/trim", headers=headers, json={
                    "orientation": "coronal", "index": 5, "label_id": 1, "direction": "left",
                })
                coronal_left.raise_for_status()
                self.assertFalse(np.any(loaded.masks[1][:, :6, :]))
                self.assertTrue(np.all(loaded.masks[1][:, 6:, :]))
                client.post("/api/edit/undo", headers=headers).raise_for_status()

                sagittal_right = client.post("/api/edit/trim", headers=headers, json={
                    "orientation": "sagittal", "index": 8, "label_id": 1, "direction": "right",
                })
                sagittal_right.raise_for_status()
                self.assertTrue(np.all(loaded.masks[1][:, :, :8]))
                self.assertFalse(np.any(loaded.masks[1][:, :, 8:]))
                self.assertTrue(np.array_equal(loaded.masks[2], other))
                client.post("/api/edit/undo", headers=headers).raise_for_status()

                with loaded.lock:
                    loaded.labels[0].locked = True
                before_locked = loaded.masks[1].copy()
                locked = client.post("/api/edit/trim", headers=headers, json={
                    "orientation": "axial", "index": 2, "label_id": 1, "direction": "left",
                })
                self.assertEqual(locked.status_code, 409, locked.text)
                self.assertTrue(np.array_equal(loaded.masks[1], before_locked))
                self.assertEqual(
                    [item["direction"] for item in service.session_info()["range_operation_log"]],
                    ["left", "right", "left", "right"],
                )

                invalid_index = client.post("/api/edit/trim", headers=headers, json={
                    "orientation": "axial", "index": shape[0], "label_id": 1, "direction": "left",
                })
                self.assertEqual(invalid_index.status_code, 422, invalid_index.text)

    def test_single_named_nifti_export_is_click_reopenable_and_eraser_persists(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = self.make_unicode_dataset(temporary)
            patient = root / "PAT_001"
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={
                    "case_id": case_id,
                    "roi_relative_path": "mask.nii.gz",
                })
                loaded.raise_for_status()
                headers = self.session_headers(loaded.json())
                service = client.app.state.service
                before = int(service.require_loaded().masks[1].sum())

                erased = client.post("/api/edit/stroke", headers=headers, json={
                    "orientation": "axial", "index": 3, "label_id": 1,
                    "tool": "eraser", "radius": 1, "points": [{"x": 6, "y": 5}],
                })
                self.assertEqual(erased.status_code, 200, erased.text)
                after = int(service.require_loaded().masks[1].sum())
                self.assertLess(after, before)

                exported = client.post("/api/export", headers=headers, json={
                    "reviewed": False, "roi_name": "肿瘤 ROI.nii.gz",
                })
                self.assertEqual(exported.status_code, 200, exported.text)
                payload = exported.json()
                self.assertEqual(payload["filename"], "roi_肿瘤_ROI.nii.gz")
                self.assertEqual(payload["status"], "已完成")
                self.assertEqual(client.get("/api/session", headers=headers).json()["status"], "已完成")
                output = Path(payload["output"])
                self.assertEqual(output.parent, patient)
                self.assertTrue(output.is_file())
                self.assertEqual(list(patient.glob("roi_*.nii.gz")), [output])
                self.assertFalse((patient / "ROI").exists())

                ascii_saved = temporary / "exported_roi.nii.gz"
                ascii_source = temporary / "exported_source.nii.gz"
                shutil.copy2(output, ascii_saved)
                shutil.copy2(patient / "image.nii.gz", ascii_source)
                saved_image = sitk.ReadImage(str(ascii_saved))
                source_image = sitk.ReadImage(str(ascii_source))
                self.assertEqual(saved_image.GetSize(), source_image.GetSize())
                self.assertEqual(saved_image.GetSpacing(), source_image.GetSpacing())
                self.assertEqual(int(sitk.GetArrayFromImage(saved_image)[3, 5, 6]), 0)

                files = client.get("/api/cases").json()["items"][0]["files"]
                saved_rows = [item for item in files if item["role"] == "saved_roi"]
                self.assertTrue(any(item["relative_path"] == payload["relative_path"] for item in saved_rows))
                reopened = client.post("/api/cases/load", json={
                    "case_id": case_id,
                    "roi_relative_path": payload["relative_path"],
                })
                self.assertEqual(reopened.status_code, 200, reopened.text)
                self.assertTrue(any(payload["filename"] in warning for warning in reopened.json()["warnings"]))
                self.assertEqual(int(service.require_loaded().masks[1].sum()), after)

                outside = root / "outside.nii.gz"
                shutil.copy2(output, outside)
                blocked = client.post("/api/cases/load", json={
                    "case_id": case_id,
                    "roi_relative_path": "../outside.nii.gz",
                })
                self.assertEqual(blocked.status_code, 422, blocked.text)

    def test_model_result_enters_editable_working_layer_and_restores_original(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = self.make_unicode_dataset(temporary)
            patient = root / "PAT_001"
            with TestClient(create_app(project_root)) as client:
                html = client.get("/").text
                self.assertIn('id="restore-original"', html)
                self.assertIn('id="prompt-radius"', html)
                self.assertIn('id="add-positive-point"', html)
                self.assertIn('id="add-negative-point"', html)
                self.assertIn('id="run-point-refine"', html)
                self.assertNotIn('id="adopt-proposal"', html)
                self.assertNotIn('id="new-label"', html)
                self.assertNotIn('id="review-roi"', html)
                self.assertNotIn('data-merge=', html)
                self.assertNotIn('data-tool="scribble_positive"', html)
                self.assertNotIn('data-tool="scribble_negative"', html)
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                service = client.app.state.service
                loaded = service.require_loaded()
                model_mask = np.zeros(loaded.volume.array_zyx.shape, dtype=bool)
                model_mask[3, 4:8, 5:10] = True
                with loaded.lock:
                    loaded.masks[1][:] = False
                    service._apply_prediction(
                        loaded,
                        PredictionResult({1: model_mask.copy()}, "nnInteractive", "test"),
                        interactive=True,
                    )
                session = service.session_info(loaded.case.case_id, loaded.session_token)
                self.assertTrue(session["dirty"])
                self.assertFalse(session["proposal_labels"])
                self.assertEqual(session["model_output_labels"], [1])
                self.assertFalse(session["empty_model_output_labels"])
                self.assertIn(1, session["auto_baseline_labels"])
                self.assertFalse(loaded.ai_proposal)
                self.assertEqual(int(loaded.masks[1].sum()), int(model_mask.sum()))
                self.assertFalse(list(patient.glob("roi_*.nii.gz")))

                erased = client.post("/api/edit/stroke", headers=headers, json={
                    "orientation": "axial", "index": 3, "label_id": 1,
                    "tool": "eraser", "radius": 1, "points": [{"x": 7, "y": 5}],
                })
                self.assertEqual(erased.status_code, 200, erased.text)
                erased_sum = int(loaded.masks[1].sum())
                self.assertLess(erased_sum, int(model_mask.sum()))
                restored = client.post("/api/proposals/merge", headers=headers, json={
                    "label_id": 1, "operation": "restore_baseline",
                })
                self.assertEqual(restored.status_code, 200, restored.text)
                self.assertEqual(int(loaded.masks[1].sum()), int(model_mask.sum()))
                client.post("/api/edit/undo", headers=headers).raise_for_status()
                self.assertEqual(int(loaded.masks[1].sum()), erased_sum)
                client.post("/api/edit/redo", headers=headers).raise_for_status()
                self.assertEqual(int(loaded.masks[1].sum()), int(model_mask.sum()))

                exported = client.post("/api/export", headers=headers, json={
                    "reviewed": False, "roi_name": "修补后病灶",
                })
                self.assertEqual(exported.status_code, 200, exported.text)
                self.assertTrue(Path(exported.json()["output"]).is_file())

    def test_empty_model_result_does_not_overwrite_editable_roi(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                client.post("/api/cases/load", json={"case_id": case_id}).raise_for_status()
                service = client.app.state.service
                loaded = service.require_loaded()
                with loaded.lock:
                    loaded.masks[1][:] = False
                    loaded.masks[1][2, 3:6, 4:8] = True
                    before = loaded.masks[1].copy()
                    service._apply_prediction(
                        loaded,
                        PredictionResult({1: np.zeros_like(before)}, "nnInteractive", "test"),
                        interactive=True,
                    )
                session = service.session_info(loaded.case.case_id, loaded.session_token)
                self.assertTrue(np.array_equal(loaded.masks[1], before))
                self.assertFalse(session["model_output_labels"])
                self.assertEqual(session["empty_model_output_labels"], [1])
                self.assertTrue(any("返回空 ROI" in warning for warning in session["warnings"]))

    def test_wrong_shape_model_result_does_not_mutate_editable_layers(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                client.post("/api/cases/load", json={"case_id": case_id}).raise_for_status()
                service = client.app.state.service
                loaded = service.require_loaded()
                original_labels = [label.id for label in loaded.labels]
                original_masks = {label_id: mask.copy() for label_id, mask in loaded.masks.items()}
                with loaded.lock, self.assertRaisesRegex(ValueError, "shape"):
                    service._apply_prediction(
                        loaded,
                        PredictionResult({99: np.zeros((1, 2, 3), dtype=bool)}, "bad-model", "test"),
                        interactive=True,
                    )
                self.assertEqual([label.id for label in loaded.labels], original_labels)
                self.assertEqual(set(loaded.masks), set(original_masks))
                self.assertTrue(all(np.array_equal(loaded.masks[key], value) for key, value in original_masks.items()))

    def test_mr_display_metadata_uses_robust_intensity_range(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = temporary / "中文MR"
            patient = root / "P001"
            patient.mkdir(parents=True)
            ascii_image = temporary / "T2_MR.nii.gz"
            array = np.linspace(0, 65535, 8 * 10 * 12, dtype=np.float32).reshape(8, 10, 12)
            image = sitk.GetImageFromArray(array)
            image.SetSpacing((0.9, 0.9, 3.0))
            sitk.WriteImage(image, str(ascii_image), True)
            shutil.copy2(ascii_image, patient / "T2_MR.nii.gz")
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                self.assertEqual(loaded.status_code, 200, loaded.text)
                display = loaded.json()["display"]
                self.assertEqual(display["suggested_modality"], "MR")
                self.assertGreater(display["mr_default_width"], 50000)
                self.assertGreater(display["mr_default_level"], 0)
                headers = self.session_headers(loaded.json())
                rendered = client.get("/api/slice", headers=headers, params={
                    "orientation": "axial", "index": 4,
                    "level": display["mr_default_level"], "width": display["mr_default_width"],
                })
                self.assertEqual(rendered.status_code, 200, rendered.text)
                self.assertTrue(rendered.content.startswith(b"\x89PNG"))

    def test_unknown_positive_nifti_is_not_silently_declared_ct(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = temporary / "数据"
            patient = root / "P001"
            patient.mkdir(parents=True)
            ascii_image = temporary / "source.nii.gz"
            array = np.linspace(0, 1800, 8 * 10 * 12, dtype=np.float32).reshape(8, 10, 12)
            sitk.WriteImage(sitk.GetImageFromArray(array), str(ascii_image), True)
            shutil.copy2(ascii_image, patient / "image.nii.gz")
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                self.assertEqual(loaded.status_code, 200, loaded.text)
                display = loaded.json()["display"]
                self.assertEqual(display["suggested_modality"], "UNKNOWN")
                self.assertGreater(display["mr_default_width"], 1000)

    def test_cancelling_queued_task_never_runs_or_cancels_shared_engine(self) -> None:
        manager = TaskManager()
        first_started = threading.Event()
        release_first = threading.Event()
        second_calls = []

        class SharedEngine:
            cancel_calls = 0

            def cancel(self):
                self.cancel_calls += 1

        engine = SharedEngine()

        def first_operation(_entry):
            first_started.set()
            release_first.wait(3)

        def second_operation(_entry):
            second_calls.append(True)

        first = manager.submit("auto", "A", engine, first_operation)
        self.assertTrue(first_started.wait(1))
        second = manager.submit("auto", "A", engine, second_operation)
        manager.cancel(second.id)
        release_first.set()
        for _ in range(50):
            if first.status == "completed":
                break
            time.sleep(0.01)
        self.assertEqual(second.status, "cancelled")
        self.assertFalse(second_calls)
        self.assertEqual(engine.cancel_calls, 0)

    def test_slow_case_load_cannot_discard_edit_created_during_read(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            second = root / "PAT_002"
            second.mkdir()
            shutil.copy2(root / "PAT_001" / "image.nii.gz", second / "image.nii.gz")
            shutil.copy2(root / "PAT_001" / "mask.nii.gz", second / "mask.nii.gz")
            service = create_app(project_root).state.service
            service.set_root(root)
            case_ids = [item["case_id"] for item in service.list_cases()]
            first, second_case = case_ids
            service.load_case(first)
            started = threading.Event()
            release = threading.Event()
            errors = []

            from roi_web.workbench import service as service_module
            original_read = service_module.read_volume

            def delayed_read(case):
                if case.case_id == second_case:
                    started.set()
                    release.wait(3)
                return original_read(case)

            def load_second():
                try:
                    service.load_case(second_case)
                except Exception as exc:
                    errors.append(exc)

            with patch("roi_web.workbench.service.read_volume", side_effect=delayed_read):
                worker = threading.Thread(target=load_second)
                worker.start()
                self.assertTrue(started.wait(1))
                service.stroke("axial", 0, 1, "brush", 1, [(1, 1)], first)
                release.set()
                worker.join(5)
            self.assertTrue(errors and isinstance(errors[0], ConflictError))
            loaded = service.require_loaded()
            self.assertEqual(loaded.case.case_id, first)
            self.assertTrue(loaded.dirty)
            self.assertTrue(loaded.masks[1][0, 1, 1])
            service._cancel_recovery(loaded, clear=True)

    def test_root_generation_blocks_slow_load_from_previous_dataset(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            first_root = self.make_unicode_dataset(temporary)
            second_root = temporary / "另一个根"
            second_patient = second_root / "PAT_B"
            second_patient.mkdir(parents=True)
            shutil.copy2(first_root / "PAT_001" / "image.nii.gz", second_patient / "image.nii.gz")
            service = create_app(project_root).state.service
            service.set_root(first_root)
            first_case = service.list_cases()[0]["case_id"]
            started = threading.Event()
            release = threading.Event()
            errors = []

            from roi_web.workbench import service as service_module
            original_read = service_module.read_volume

            def delayed_read(case):
                started.set()
                release.wait(3)
                return original_read(case)

            def load_first():
                try:
                    service.load_case(first_case)
                except Exception as exc:
                    errors.append(exc)

            with patch("roi_web.workbench.service.read_volume", side_effect=delayed_read):
                worker = threading.Thread(target=load_first)
                worker.start()
                self.assertTrue(started.wait(1))
                service.set_root(second_root)
                release.set()
                worker.join(5)
            self.assertTrue(errors and isinstance(errors[0], ConflictError))
            self.assertIsNone(service.state.loaded)
            self.assertEqual(service.state.data_root, second_root.resolve())
            self.assertEqual(service.list_cases()[0]["case_id"], "PAT_B/image")

    def test_session_token_blocks_same_case_id_from_different_root(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            source_root = self.make_unicode_dataset(temporary)
            root_a = temporary / "root_a"
            root_b = temporary / "root_b"
            for root in (root_a, root_b):
                patient = root / "PAT_001"
                patient.mkdir(parents=True)
                shutil.copy2(source_root / "PAT_001" / "image.nii.gz", patient / "image.nii.gz")
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root_a)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                first = client.post("/api/cases/load", json={"case_id": case_id}).json()
                first_headers = self.session_headers(first)
                client.post("/api/root", json={"path": str(root_b)}).raise_for_status()
                second = client.post("/api/cases/load", json={"case_id": case_id}).json()
                self.assertNotEqual(first["session_token"], second["session_token"])
                service = client.app.state.service
                before = int(service.require_loaded().masks[1].sum())
                stale = client.post("/api/edit/stroke", headers=first_headers, json={
                    "orientation": "axial", "index": 0, "label_id": 1,
                    "tool": "brush", "radius": 1, "points": [{"x": 1, "y": 1}],
                })
                self.assertEqual(stale.status_code, 409)
                self.assertEqual(int(service.require_loaded().masks[1].sum()), before)

    def test_prompt_reset_preserves_automatic_proposal_and_invalidates_interactive_proposal(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                service = client.app.state.service
                loaded = service.require_loaded()
                proposal = np.ones(loaded.volume.array_zyx.shape, dtype=bool)

                with loaded.lock:
                    loaded.ai_proposal = {1: proposal.copy()}
                    loaded.provenance = {"model_id": "care_rectum", "proposal_labels": [1]}
                    loaded.prompts = [{"kind": "point"}]
                client.post("/api/prompts/reset", headers=headers).raise_for_status()
                self.assertIn(1, loaded.ai_proposal)

                with loaded.lock:
                    loaded.ai_proposal = {1: proposal.copy()}
                    loaded.provenance = {"model_id": "nnInteractive", "proposal_labels": [1]}
                    loaded.prompts = [{"kind": "point"}]
                client.post("/api/prompts/undo", headers=headers).raise_for_status()
                self.assertFalse(loaded.ai_proposal)
                self.assertEqual(loaded.provenance["decisions"]["1"], "prompt_undone")

                with loaded.lock:
                    loaded.ai_proposal = {1: proposal.copy()}
                    loaded.labels[0].locked = True
                blocked = client.post("/api/proposals/merge", headers=headers, json={"label_id": 1, "operation": "replace"})
                self.assertEqual(blocked.status_code, 409)
                self.assertTrue(blocked.json()["request_id"])
                rejected = client.post("/api/proposals/merge", headers=headers, json={"label_id": 1, "operation": "reject"})
                self.assertEqual(rejected.status_code, 200, rejected.text)
                self.assertFalse(loaded.ai_proposal)

    def test_stale_tab_cannot_edit_another_case_and_cross_site_post_is_blocked(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            second = root / "PAT_002"
            second.mkdir()
            shutil.copy2(root / "PAT_001" / "image.nii.gz", second / "image.nii.gz")
            shutil.copy2(root / "PAT_001" / "mask.nii.gz", second / "mask.nii.gz")
            (root / "roi_manifest.csv").write_text(
                "case_id,status\nPAT_001/image,<img onerror=alert(1)>\n", encoding="utf-8"
            )
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                cases = client.get("/api/cases").json()["items"]
                self.assertTrue(all(item["status"] in {"未开始", "待审核", "修补中", "已完成", "失败"} for item in cases))
                first, second_case = (item["case_id"] for item in cases)
                first_loaded = client.post("/api/cases/load", json={"case_id": first})
                first_loaded.raise_for_status()
                first_headers = self.session_headers(first_loaded.json())
                second_loaded = client.post("/api/cases/load", json={"case_id": second_case})
                second_loaded.raise_for_status()
                second_headers = self.session_headers(second_loaded.json())
                service = client.app.state.service
                before = int(service.require_loaded().masks[1].sum())
                stale = client.post("/api/edit/stroke", headers=first_headers, json={
                    "orientation": "axial", "index": 3, "label_id": 1,
                    "tool": "brush", "radius": 2, "points": [{"x": 1, "y": 1}],
                })
                self.assertEqual(stale.status_code, 409, stale.text)
                self.assertEqual(int(service.require_loaded().masks[1].sum()), before)
                csrf = client.post(
                    "/api/edit/undo",
                    headers={**second_headers, "Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
                )
                self.assertEqual(csrf.status_code, 403)
                client.post("/api/edit/stroke", headers=second_headers, json={
                    "orientation": "axial", "index": 0, "label_id": 1,
                    "tool": "brush", "radius": 1, "points": [{"x": 1, "y": 1}],
                }).raise_for_status()
                blocked_scan = client.post("/api/root", json={"path": str(root)})
                self.assertEqual(blocked_scan.status_code, 409)
                self.assertEqual(service.require_loaded().case.case_id, second_case)

    def test_reviewed_edit_becomes_repairing_and_empty_saved_roi_stays_empty(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                service = client.app.state.service
                loaded = service.require_loaded()
                loaded.case.status = "已完成"
                edited = client.post("/api/edit/stroke", headers=headers, json={
                    "orientation": "axial", "index": 0, "label_id": 1,
                    "tool": "brush", "radius": 1, "points": [{"x": 1, "y": 1}],
                })
                self.assertEqual(edited.json()["status"], "修补中")
                with loaded.lock:
                    loaded.masks[1][:] = False
                    loaded.dirty = True
                saved = client.post("/api/save", headers=headers, json={"reviewed": False})
                saved.raise_for_status()
                self.assertEqual(saved.json()["status"], "已完成")
                reopened = client.post("/api/cases/load", json={"case_id": case_id}).json()
                self.assertEqual(reopened["status"], "已完成")
                self.assertFalse(any("mask.nii.gz 作为待审核" in item for item in reopened["warnings"]))
                self.assertEqual(int(service.require_loaded().masks[1].sum()), 0)

    def test_prompt_change_discards_inflight_interactive_result(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        started = threading.Event()
        release = threading.Event()

        class DelayedInteractiveEngine:
            def __init__(self, _client, _prompts, label_id):
                self.label_id = label_id

            def predict(self, _case, volume):
                started.set()
                release.wait(5)
                mask = np.ones(volume.array_zyx.shape, dtype=bool)
                return PredictionResult({self.label_id: mask}, "nnInteractive", "test")

            def cancel(self):
                release.set()

        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                client.post("/api/prompts", headers=headers, json={
                    "orientation": "axial", "index": 2, "kind": "positive", "points": [{"x": 4, "y": 4}], "radius": 7,
                }).raise_for_status()
                self.assertEqual(client.app.state.service.require_loaded().prompts[0]["radius"], 7)
                with patch("roi_web.workbench.service.NnInteractivePromptEngine", DelayedInteractiveEngine):
                    task = client.post("/api/tasks/interactive", headers=headers, json={"label_id": 1}).json()
                    self.assertTrue(started.wait(2))
                    client.post("/api/prompts/reset", headers=headers).raise_for_status()
                    release.set()
                    for _ in range(50):
                        status = client.get(f"/api/tasks/{task['id']}", headers=headers).json()["status"]
                        if status in {"cancelled", "completed", "failed"}:
                            break
                        time.sleep(0.02)
                self.assertEqual(status, "cancelled")
                self.assertFalse(client.app.state.service.require_loaded().ai_proposal)

    def test_interactive_uses_loaded_roi_as_initial_mask(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        captured: dict[str, object] = {}

        class CapturingInteractiveEngine:
            def __init__(self, _client, prompts, label_id, initial_mask=None):
                captured["prompts"] = prompts
                captured["initial_mask"] = None if initial_mask is None else initial_mask.copy()
                self.label_id = label_id

            def predict(self, _case, volume):
                return PredictionResult({self.label_id: np.ones(volume.array_zyx.shape, dtype=bool)}, "nnInteractive", "test")

            def cancel(self):
                return None

        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                loaded = client.app.state.service.require_loaded()
                with loaded.lock:
                    loaded.masks[1][:] = False
                    loaded.masks[1][2:5, 3:7, 4:9] = True
                    initial_seed = loaded.masks[1].copy()

                with patch("roi_web.workbench.service.NnInteractivePromptEngine", CapturingInteractiveEngine):
                    task_response = client.post("/api/tasks/interactive", headers=headers, json={"label_id": 1})
                    self.assertEqual(task_response.status_code, 200, task_response.text)
                    task_id = task_response.json()["id"]
                    for _ in range(50):
                        status = client.get(f"/api/tasks/{task_id}", headers=headers).json()["status"]
                        if status in {"completed", "failed", "cancelled"}:
                            break
                        time.sleep(0.02)

                self.assertEqual(status, "completed")
                self.assertEqual(captured["prompts"], [])
                np.testing.assert_array_equal(captured["initial_mask"], initial_seed)

    def test_interactive_creates_unsaved_working_layer_after_all_roi_files_are_deselected(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        captured: dict[str, object] = {}

        class CapturingInteractiveEngine:
            def __init__(self, _client, prompts, label_id, initial_mask=None):
                captured["prompts"] = list(prompts)
                captured["label_id"] = label_id
                captured["initial_mask"] = initial_mask
                self.label_id = label_id

            def predict(self, _case, volume):
                mask = np.zeros(volume.array_zyx.shape, dtype=bool)
                mask[2:4, 3:6, 4:8] = True
                return PredictionResult({self.label_id: mask}, "nnInteractive", "test")

            def cancel(self):
                return None

        with tempfile.TemporaryDirectory() as tmp:
            root, patient, tumor, body = self.make_file_scoped_layer_dataset(Path(tmp))
            tumor_bytes = (patient / "roi_tumor.nii.gz").read_bytes()
            body_bytes = (patient / "body_composition_roi.nii.gz").read_bytes()
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                loaded.raise_for_status()
                headers = self.session_headers(loaded.json())
                cleared = client.post("/api/roi/selection", headers=headers, json={
                    "relative_paths": [], "discard_dirty": False,
                })
                self.assertEqual(cleared.status_code, 200, cleared.text)
                self.assertEqual(cleared.json()["layers"], [])
                self.assertEqual(cleared.json()["editable_roi_source"], "")
                client.post("/api/prompts", headers=headers, json={
                    "orientation": "axial", "index": 2, "kind": "positive",
                    "points": [{"x": 5, "y": 4}], "radius": 3,
                }).raise_for_status()

                with patch("roi_web.workbench.service.NnInteractivePromptEngine", CapturingInteractiveEngine):
                    task_response = client.post("/api/tasks/interactive", headers=headers, json={"label_id": 1})
                    self.assertEqual(task_response.status_code, 200, task_response.text)
                    task_id = task_response.json()["id"]
                    for _ in range(50):
                        status = client.get(f"/api/tasks/{task_id}", headers=headers).json()["status"]
                        if status in {"completed", "failed", "cancelled"}:
                            break
                        time.sleep(0.02)

                self.assertEqual(status, "completed")
                self.assertEqual(captured["label_id"], 1)
                self.assertIsNone(captured["initial_mask"])
                session = client.get("/api/session", headers=headers).json()
                self.assertEqual(session["selected_roi_files"], [])
                self.assertEqual(len(session["layers"]), 1)
                layer = session["layers"][0]
                self.assertTrue(layer["editable"])
                self.assertEqual(layer["source_label_id"], 1)
                self.assertTrue(layer["source_file"].startswith("@working/"))
                self.assertEqual(session["working_layer_kind"], "new_interactive")
                self.assertFalse(list(patient.glob("roi_nninteractive_new*.nii.gz")))
                self.assertEqual((patient / "roi_tumor.nii.gz").read_bytes(), tumor_bytes)
                self.assertEqual((patient / "body_composition_roi.nii.gz").read_bytes(), body_bytes)

                exported = client.post("/api/export", headers=headers, json={"roi_name": "new_tumor", "reviewed": False})
                self.assertEqual(exported.status_code, 200, exported.text)
                saved = client.get("/api/session", headers=headers).json()
                self.assertEqual(saved["editable_roi_source"], "roi_new_tumor.nii.gz")
                self.assertEqual(saved["selected_roi_files"], ["roi_new_tumor.nii.gz"])
                self.assertEqual(saved["working_layer_kind"], "")
                self.assertTrue(all(layer["source_file"] == "roi_new_tumor.nii.gz" for layer in saved["layers"] if layer["editable"]))

    def test_interactive_adds_new_target_when_only_reference_layers_are_selected(self) -> None:
        project_root = Path(__file__).resolve().parents[1]

        class CapturingInteractiveEngine:
            def __init__(self, _client, _prompts, label_id, initial_mask=None):
                self.label_id = label_id
                self.initial_mask = initial_mask

            def predict(self, _case, volume):
                result = np.zeros(volume.array_zyx.shape, dtype=bool)
                result[1:3, 2:5, 3:7] = True
                return PredictionResult({self.label_id: result}, "nnInteractive", "test")

            def cancel(self):
                return None

        with tempfile.TemporaryDirectory() as tmp:
            root, patient, _tumor, _body = self.make_file_scoped_layer_dataset(Path(tmp))
            reference_bytes = (patient / "body_composition_roi.nii.gz").read_bytes()
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded = client.post("/api/cases/load", json={"case_id": case_id})
                loaded.raise_for_status()
                headers = self.session_headers(loaded.json())
                references = client.post("/api/roi/selection", headers=headers, json={
                    "relative_paths": ["body_composition_roi.nii.gz"], "discard_dirty": False,
                })
                references.raise_for_status()
                self.assertTrue(all(not layer["editable"] for layer in references.json()["layers"]))
                reference_layer_count = len(references.json()["layers"])
                client.post("/api/prompts", headers=headers, json={
                    "orientation": "axial", "index": 2, "kind": "positive",
                    "points": [{"x": 5, "y": 4}], "radius": 3,
                }).raise_for_status()
                with patch("roi_web.workbench.service.NnInteractivePromptEngine", CapturingInteractiveEngine):
                    task = client.post("/api/tasks/interactive", headers=headers, json={"label_id": 1})
                    task.raise_for_status()
                    task_id = task.json()["id"]
                    for _ in range(50):
                        status = client.get(f"/api/tasks/{task_id}", headers=headers).json()["status"]
                        if status in {"completed", "failed", "cancelled"}:
                            break
                        time.sleep(0.02)
                self.assertEqual(status, "completed")
                session = client.get("/api/session", headers=headers).json()
                self.assertEqual(session["working_layer_kind"], "new_interactive")
                self.assertEqual(len([layer for layer in session["layers"] if layer["editable"]]), 1)
                self.assertEqual(len([layer for layer in session["layers"] if not layer["editable"]]), reference_layer_count)
                self.assertEqual((patient / "body_composition_roi.nii.gz").read_bytes(), reference_bytes)

    def test_interactive_reference_is_separate_locked_layer(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        captured: dict[str, object] = {}

        class CapturingInteractiveEngine:
            def __init__(self, _client, prompts, label_id, initial_mask=None):
                captured["prompts"] = list(prompts)
                captured["initial_mask"] = None if initial_mask is None else initial_mask.copy()
                self.label_id = label_id

            def predict(self, _case, _volume):
                return PredictionResult({self.label_id: current_array.astype(bool)}, "nnInteractive", "test")

            def cancel(self):
                return None

        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = self.make_unicode_dataset(temporary)
            patient = root / "PAT_001"
            source_image = sitk.ReadImage(str(temporary / "source.nii.gz"))
            current_array = np.zeros((8, 12, 16), dtype=np.uint8)
            current_array[1:3, 2:5, 3:7] = 1
            reference_array = np.zeros((8, 12, 16), dtype=np.uint8)
            reference_array[5:7, 8:11, 10:14] = 1
            for array, filename in ((current_array, "roi_current.nii.gz"), (reference_array, "manual_reference.nii.gz")):
                image = sitk.GetImageFromArray(array)
                image.CopyInformation(source_image)
                ascii_path = temporary / filename
                sitk.WriteImage(image, str(ascii_path), True)
                shutil.copy2(ascii_path, patient / filename)

            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                service = client.app.state.service
                loaded = service.require_loaded()
                with loaded.lock:
                    loaded.masks[1] = current_array.astype(bool)
                current_sum = int(current_array.sum())

                reference = client.post("/api/roi/load-interactive-reference", headers=headers, json={
                    "relative_path": "manual_reference.nii.gz",
                })
                self.assertEqual(reference.status_code, 200, reference.text)
                session = reference.json()
                self.assertEqual(session["interactive_reference"]["relative_path"], "manual_reference.nii.gz")
                self.assertTrue(session["interactive_reference_pending"])
                reference_ids = session["interactive_reference_label_ids"]
                self.assertEqual(len(reference_ids), 1)
                reference_label = next(label for label in session["labels"] if label["id"] == reference_ids[0])
                self.assertTrue(reference_label["locked"])
                self.assertEqual(int(loaded.masks[1].sum()), current_sum)
                self.assertEqual(int(loaded.masks[reference_ids[0]].sum()), int(reference_array.sum()))

                with patch("roi_web.workbench.service.NnInteractivePromptEngine", CapturingInteractiveEngine):
                    task_response = client.post("/api/tasks/interactive", headers=headers, json={"label_id": 1})
                    self.assertEqual(task_response.status_code, 200, task_response.text)
                    task_id = task_response.json()["id"]
                    for _ in range(50):
                        status = client.get(f"/api/tasks/{task_id}", headers=headers).json()["status"]
                        if status in {"completed", "failed", "cancelled"}:
                            break
                        time.sleep(0.02)

                self.assertEqual(status, "completed")
                self.assertEqual(captured["prompts"], [])
                np.testing.assert_array_equal(captured["initial_mask"], reference_array.astype(bool))
                after_prediction = client.get("/api/session", headers=headers)
                self.assertEqual(after_prediction.status_code, 200, after_prediction.text)
                self.assertEqual(after_prediction.json()["interactive_reference_label_ids"], reference_ids)
                self.assertFalse(after_prediction.json()["interactive_reference_pending"])
                self.assertEqual(after_prediction.json()["interactive_reference"]["relative_path"], "manual_reference.nii.gz")
                self.assertEqual(int(loaded.masks[reference_ids[0]].sum()), int(reference_array.sum()))

    def test_oblique_workspace_hash_failure_blocks_old_roi(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            temporary = Path(tmp)
            root = temporary / "中文数据"
            patient = root / "P001"
            patient.mkdir(parents=True)
            ascii_source = temporary / "oblique.nii.gz"
            image = sitk.GetImageFromArray(np.zeros((8, 10, 12), dtype=np.int16))
            angle = np.deg2rad(12.0)
            image.SetDirection((np.cos(angle), -np.sin(angle), 0.0, np.sin(angle), np.cos(angle), 0.0, 0.0, 0.0, 1.0))
            image.SetSpacing((0.8, 0.9, 2.0))
            sitk.WriteImage(image, str(ascii_source), True)
            shutil.copy2(ascii_source, patient / "image.nii.gz")
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                headers = self.session_headers(loaded_response.json())
                client.post("/api/edit/stroke", headers=headers, json={
                    "orientation": "axial", "index": 3, "label_id": 1,
                    "tool": "brush", "radius": 2, "points": [{"x": 4, "y": 4}],
                }).raise_for_status()
                output = Path(client.post("/api/save", headers=headers, json={"reviewed": False}).json()["output"])
                workspace = output / "workspace_labels.nii.gz"
                self.assertTrue(workspace.is_file())
                with workspace.open("r+b") as handle:
                    handle.write(b"BROKEN")
                reopened = client.post("/api/cases/load", json={"case_id": case_id})
                self.assertEqual(reopened.status_code, 200, reopened.text)
                self.assertEqual(reopened.json()["status"], "失败")
                self.assertTrue(any("工作网格ROI" in item for item in reopened.json()["warnings"]))
                self.assertEqual(int(client.app.state.service.require_loaded().masks[1].sum()), 0)

    def test_roi_mesh_uses_current_unsaved_mask_and_physical_spacing(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_unicode_dataset(Path(tmp))
            with TestClient(create_app(project_root)) as client:
                client.post("/api/root", json={"path": str(root)}).raise_for_status()
                case_id = client.get("/api/cases").json()["items"][0]["case_id"]
                loaded_response = client.post("/api/cases/load", json={"case_id": case_id})
                loaded_response.raise_for_status()
                session = loaded_response.json()
                headers = self.session_headers(session)

                empty = client.get("/api/roi-mesh", params={"label_id": 1}, headers=headers)
                self.assertEqual(empty.status_code, 422, empty.text)
                self.assertIn("当前标签没有可渲染的 ROI", empty.json()["detail"])

                service = client.app.state.service
                loaded = service.require_loaded()
                with loaded.lock:
                    loaded.masks[1][2:5, 3:7, 4:9] = True
                    loaded.revision += 1
                    loaded.dirty = True
                    expected_revision = loaded.revision
                    expected_dirty = loaded.dirty

                response = client.get("/api/roi-mesh", params={"label_id": 1}, headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
                mesh = response.json()
                self.assertEqual(mesh["label_id"], 1)
                self.assertEqual(mesh["revision"], expected_revision)
                self.assertEqual(mesh["voxel_count"], 60)
                self.assertEqual(mesh["spacing_xyz"], [0.8, 1.1, 2.5])
                self.assertEqual(mesh["coordinate_system"], "display_physical_xyz")
                self.assertEqual(mesh["mesh_step"], 1)
                self.assertFalse(mesh["downsampled"])
                self.assertGreater(mesh["vertex_count"], 0)
                self.assertGreater(mesh["triangle_count"], 0)
                self.assertEqual(len(mesh["vertices"]), mesh["vertex_count"] * 3)
                self.assertEqual(len(mesh["normals"]), mesh["vertex_count"] * 3)
                self.assertEqual(len(mesh["indices"]), mesh["triangle_count"] * 3)
                self.assertTrue(all(high > low for low, high in zip(mesh["bounds_mm"]["min"], mesh["bounds_mm"]["max"])))

                with loaded.lock:
                    self.assertEqual(loaded.revision, expected_revision, "3D 预览不得改变工作层 revision")
                    self.assertEqual(loaded.dirty, expected_dirty, "3D 预览不得改变未保存状态")

                missing = client.get("/api/roi-mesh", params={"label_id": 999}, headers=headers)
                self.assertEqual(missing.status_code, 404, missing.text)
                stale_headers = dict(headers)
                stale_headers["X-ROI-Session-ID"] = "0" * 32
                stale = client.get("/api/roi-mesh", params={"label_id": 1}, headers=stale_headers)
                self.assertEqual(stale.status_code, 409, stale.text)


if __name__ == "__main__":
    unittest.main()
