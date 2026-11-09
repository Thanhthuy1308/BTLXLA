"""Contract tests for the Flask adapter around the shared analysis pipeline."""

from __future__ import annotations

import io
import shutil
import sys
import unittest
from pathlib import Path


# Import the local Flask application rather than starting a network server. This
# keeps the test focused on the HTTP contract and makes it fast enough for every
# pre-commit run.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.app import RUNTIME_DIR, app  # noqa: E402


class AnalysisApiTests(unittest.TestCase):
    """Verify that browser uploads use the same result schema as the UI."""

    def setUp(self) -> None:
        """Enable Flask's deterministic test mode for every request."""
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_analyze_returns_auditable_result_contract(self) -> None:
        """A valid PNG produces every image URL and the explanatory payload."""
        sample = ROOT / "data" / "benchmark" / "derived" / "LCV_01.png"
        with sample.open("rb") as image_file:
            response = self.client.post(
                "/api/analyze",
                data={"image": (image_file, sample.name)},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        required_fields = {
            "job_id",
            "operation",
            "metrics",
            "interpretation",
            "original_url",
            "enhanced_url",
            "histogram_url",
            "original_edges_url",
            "enhanced_edges_url",
            "download_url",
        }
        self.assertTrue(required_fields.issubset(payload))
        self.assertIn("mean_gray", payload["interpretation"]["metrics"])
        self.assertIn("std_gray", payload["interpretation"]["metrics"])

        # The application intentionally persists assets per job. Remove only the
        # test job so source-controlled evidence and other runtime jobs survive.
        shutil.rmtree(RUNTIME_DIR / payload["job_id"], ignore_errors=True)

    def test_analyze_rejects_a_disallowed_extension(self) -> None:
        """Validation fails before any unsupported upload enters the pipeline."""
        response = self.client.post(
            "/api/analyze",
            data={"image": (io.BytesIO(b"not an image"), "notes.gif")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Chỉ hỗ trợ tệp JPG", response.get_json()["error"])

    def test_bright_image_is_described_but_not_enhanced(self) -> None:
        """A bright, high-contrast upload gets a Vietnamese 'bright' note and no transform."""
        import cv2
        import numpy as np

        image = np.full((80, 80, 3), 200, dtype=np.uint8)
        image[:, 40:] = 255
        image[:20, :20] = 30
        ok, encoded = cv2.imencode(".png", image)
        self.assertTrue(ok)
        response = self.client.post(
            "/api/analyze",
            data={"image": (io.BytesIO(encoded.tobytes()), "bright.png")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["operation"], "identity")
        self.assertIn("Ảnh có xu hướng sáng", payload["conditions"])
        titles = [item["title"] for item in payload["interpretation"]["overview"]]
        self.assertEqual(titles, ["Độ sáng", "Độ tương phản", "Histogram", "Kết quả xử lý", "Phát hiện biên Canny"])
        shutil.rmtree(RUNTIME_DIR / payload["job_id"], ignore_errors=True)

    def test_stretch_formula_reports_actual_bounds(self) -> None:
        """A low-contrast upload shows r_min/r_max values in the stretch formula."""
        sample = ROOT / "data" / "benchmark" / "derived" / "LCV_01.png"
        with sample.open("rb") as image_file:
            response = self.client.post(
                "/api/analyze",
                data={"image": (image_file, sample.name)},
                content_type="multipart/form-data",
            )
        payload = response.get_json()
        stretch = [step for step in payload["interpretation"]["transformations"] if step["name"] == "Kéo giãn tương phản"]
        self.assertEqual(len(stretch), 1)
        self.assertIn("r_min = ", stretch[0]["formula"])
        self.assertIn("r_max = ", stretch[0]["formula"])
        shutil.rmtree(RUNTIME_DIR / payload["job_id"], ignore_errors=True)

    def test_pipeline_stages_overlays_and_exports(self) -> None:
        """Each pipeline step carries a 256-bin histogram, and every download link resolves."""
        sample = ROOT / "data" / "benchmark" / "primary" / "LOL_LOW_10.png"
        with sample.open("rb") as image_file:
            response = self.client.post(
                "/api/analyze",
                data={"image": (image_file, sample.name)},
                content_type="multipart/form-data",
            )
        payload = response.get_json()
        self.assertEqual([stage["key"] for stage in payload["stages"]], ["original", "grayscale", "gamma", "stretch"])
        self.assertTrue(all(len(stage["hist"]) == 256 for stage in payload["stages"]))
        self.assertTrue(payload["stages"][-1]["final"])
        self.assertEqual(payload["thresholds"]["dark_mean"], 85.0)
        urls = [item["url"] for item in payload["downloads"]] + [payload["original_overlay_url"], payload["enhanced_overlay_url"]]
        for url in urls:
            file_response = self.client.get(url)
            self.assertEqual(file_response.status_code, 200, url)
            file_response.close()
        csv_text = (RUNTIME_DIR / payload["job_id"] / "metrics.csv").read_text(encoding="utf-8-sig")
        self.assertIn("mean_gray", csv_text)
        shutil.rmtree(RUNTIME_DIR / payload["job_id"], ignore_errors=True)

    def test_stream_reports_every_step_in_order_then_result(self) -> None:
        """The NDJSON stream emits the five pipeline steps, then the same payload as the JSON API."""
        import json

        sample = ROOT / "data" / "benchmark" / "derived" / "LCV_01.png"
        with sample.open("rb") as image_file:
            response = self.client.post(
                "/api/analyze/stream",
                data={"image": (image_file, sample.name)},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/x-ndjson")
        events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
        steps = [event["step"] for event in events if event["type"] == "step"]
        self.assertEqual(steps, ["decode", "grayscale", "measure", "enhance", "compare"])
        self.assertEqual(events[-1]["type"], "result")
        self.assertIn("stages", events[-1]["result"])
        self.assertTrue(all(event["seconds"] >= 0 for event in events if event["type"] == "step"))
        shutil.rmtree(RUNTIME_DIR / events[-1]["result"]["job_id"], ignore_errors=True)

    def test_stream_reports_decode_error_as_event(self) -> None:
        """A corrupt image yields one error event instead of a broken stream."""
        import json

        response = self.client.post(
            "/api/analyze/stream",
            data={"image": (io.BytesIO(b"not really a png"), "broken.png")},
            content_type="multipart/form-data",
        )
        events = [json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
        self.assertEqual(events, [{"type": "error", "error": events[0]["error"]}])
        self.assertIn("Không đọc được ảnh", events[0]["error"])

    def test_app_icons_are_served(self) -> None:
        """Every logo file referenced by index.html is reachable from the server."""
        if not (ROOT / "frontend" / "dist" / "favicon.svg").exists():
            self.skipTest("frontend/dist is not built")
        for name, mimetype in (("favicon.svg", "image/svg+xml"), ("apple-touch-icon.png", "image/png"),
                               ("icon-192.png", "image/png"), ("icon-512.png", "image/png")):
            response = self.client.get(f"/{name}")
            self.assertEqual(response.status_code, 200, name)
            self.assertEqual(response.mimetype, mimetype, name)
            response.close()

    def test_health_endpoint(self) -> None:
        """The wake-up ping answers quickly with a fixed payload."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_cors_only_for_configured_origins(self) -> None:
        """GitHub Pages may call the API; other sites receive no CORS grant."""
        import os
        from unittest import mock

        pages = "https://thanhthuy1308.github.io"
        with mock.patch.dict(os.environ, {"ALLOWED_ORIGINS": pages}):
            allowed = self.client.get("/api/health", headers={"Origin": pages})
            other = self.client.get("/api/health", headers={"Origin": "https://example.com"})
        self.assertEqual(allowed.headers.get("Access-Control-Allow-Origin"), pages)
        self.assertIn("Content-Disposition", allowed.headers.get("Access-Control-Expose-Headers", ""))
        self.assertNotIn("Access-Control-Allow-Origin", other.headers)
        with mock.patch.dict(os.environ, {"ALLOWED_ORIGINS": ""}):
            unset = self.client.get("/api/health", headers={"Origin": pages})
        self.assertNotIn("Access-Control-Allow-Origin", unset.headers)

    def test_prune_runtime_removes_only_expired_jobs(self) -> None:
        """Old job folders are deleted; recent jobs and the staging folder stay."""
        import os
        import time

        from web.app import prune_runtime

        old_job, new_job = RUNTIME_DIR / "test-old-job", RUNTIME_DIR / "test-new-job"
        for folder in (old_job, new_job, RUNTIME_DIR / "staging"):
            folder.mkdir(parents=True, exist_ok=True)
        two_days_ago = time.time() - 48 * 3600
        os.utime(old_job, (two_days_ago, two_days_ago))
        try:
            prune_runtime(24)
            self.assertFalse(old_job.exists())
            self.assertTrue(new_job.exists())
            self.assertTrue((RUNTIME_DIR / "staging").exists())
        finally:
            shutil.rmtree(old_job, ignore_errors=True)
            shutil.rmtree(new_job, ignore_errors=True)

    def test_corrupt_image_returns_vietnamese_error_without_job_dir(self) -> None:
        """An undecodable PNG fails cleanly and leaves no orphan job directory."""
        before = {path.name for path in RUNTIME_DIR.iterdir()} if RUNTIME_DIR.exists() else set()
        response = self.client.post(
            "/api/analyze",
            data={"image": (io.BytesIO(b"not really a png"), "broken.png")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("Không đọc được ảnh", response.get_json()["error"])
        after = {path.name for path in RUNTIME_DIR.iterdir()}
        self.assertEqual(after - before, set())


if __name__ == "__main__":
    unittest.main()
