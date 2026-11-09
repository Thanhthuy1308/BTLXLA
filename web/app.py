"""Local Flask interface for the histogram-analysis course project.

The web layer deliberately orchestrates the existing analysis module instead of
reimplementing image rules. This keeps the CLI, benchmark, and browser results
consistent and makes the user interface a transparent presentation of the same
experiment. All user-facing text is Vietnamese to match the course report.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys
import time
import uuid
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, Response, abort, jsonify, make_response, request, send_from_directory
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from analysis import (  # noqa: E402
    BRIGHT_MEAN_THRESHOLD,
    CANNY_BLUR_KERNEL,
    CANNY_BLUR_SIGMA,
    CANNY_HIGH_THRESHOLD,
    CANNY_LOW_THRESHOLD,
    CLIP_HIGH_LEVEL,
    CLIP_LOW_LEVEL,
    DARK_MEAN_THRESHOLD,
    GAMMA_FOR_DARK_IMAGES,
    LOW_CONTRAST_STD_THRESHOLD,
    PERCENTILE_HIGH,
    PERCENTILE_LOW,
    EnhancementConfig,
    ImageMetrics,
    canny_edges,
    clipping_ratios,
    enhance,
    gamma_correct,
    histogram,
    is_bright,
    is_dark,
    is_low_contrast,
    measure,
    read_bgr,
    save_comparison_figure,
    save_histogram_comparison,
    stretch_bounds,
    to_gray,
)


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
FRONTEND_DIST = ROOT / "frontend" / "dist"

# Vietnamese names for the operation codes persisted by ``enhance``.
OPERATION_LABELS = {
    "gamma": "Hiệu chỉnh Gamma",
    "contrast_stretch": "Kéo giãn tương phản",
    "identity": "Giữ nguyên ảnh",
}

app = Flask(__name__)
# A course-demo interface should fail predictably on impractically large inputs.
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def allowed_origins() -> set[str]:
    """Origins allowed to call the API from another site (e.g. GitHub Pages).

    Read from ``ALLOWED_ORIGINS`` (comma-separated, ``*`` for any) on every
    request so deployments and tests can change it without a restart. Empty by
    default: the bundled interface is served from the same origin as the API.
    """
    return {origin.strip().rstrip("/") for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",") if origin.strip()}


@app.after_request
def add_cors_headers(response: Response) -> Response:
    """Let the GitHub Pages frontend call this API and read downloaded file names."""
    origin = request.headers.get("Origin", "").rstrip("/")
    allowed = allowed_origins()
    if origin and ("*" in allowed or origin in allowed):
        response.headers["Access-Control-Allow-Origin"] = "*" if "*" in allowed else origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
        response.headers.add("Vary", "Origin")
    return response


def prune_runtime(max_age_hours: float | None = None) -> int:
    """Delete analysis jobs older than ``RUNTIME_TTL_HOURS`` (default 24 h).

    Called before each upload so a long-running server never fills its disk;
    the staging folder is skipped because it only holds in-flight uploads.
    """
    hours = max_age_hours if max_age_hours is not None else float(os.environ.get("RUNTIME_TTL_HOURS", "24"))
    if not RUNTIME_DIR.is_dir() or hours <= 0:
        return 0
    cutoff = time.time() - hours * 3600
    removed = 0
    for job_dir in RUNTIME_DIR.iterdir():
        if job_dir.is_dir() and job_dir.name != "staging" and job_dir.stat().st_mtime < cutoff:
            shutil.rmtree(job_dir, ignore_errors=True)
            removed += 1
    return removed


def allowed_image(filename: str) -> bool:
    """Return whether an uploaded filename has a supported image extension."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def number(value: float) -> float:
    """Round API values for readable UI presentation without altering saved data."""
    return round(float(value), 2)


def vn(value: float, digits: int = 2) -> str:
    """Format a number with a Vietnamese decimal comma for prose."""
    return f"{value:.{digits}f}".replace(".", ",")


def operation_label(operation: str) -> str:
    """Translate ``gamma+contrast_stretch`` into a readable Vietnamese sequence."""
    return " + ".join(OPERATION_LABELS[step] for step in operation.split("+"))


def operation_phrase(operation: str) -> str:
    """Mid-sentence form: lowercase only the first letter so 'Gamma' keeps its capital."""
    return " và ".join(OPERATION_LABELS[step][0].lower() + OPERATION_LABELS[step][1:] for step in operation.split("+"))


def metric_payload(before: ImageMetrics, after: ImageMetrics) -> dict[str, dict[str, float]]:
    """Expose the metrics used by the interface in a stable, small schema."""
    return {
        "mean_gray": {"before": number(before.mean_gray), "after": number(after.mean_gray)},
        "std_gray": {"before": number(before.std_gray), "after": number(after.std_gray)},
        "dynamic_range": {"before": number(before.dynamic_range), "after": number(after.dynamic_range)},
        "edge_ratio": {"before": number(before.edge_ratio * 100), "after": number(after.edge_ratio * 100)},
    }


def brightness_level(metrics: ImageMetrics) -> str:
    """Describe the global brightness band defined by the two mean thresholds."""
    if is_dark(metrics):
        return "tối"
    if is_bright(metrics):
        return "sáng"
    return "trung bình"


def overview_payload(
    before: ImageMetrics,
    after: ImageMetrics,
    operation: str,
    clip_before: tuple[float, float],
    clip_after: tuple[float, float],
) -> list[dict[str, str]]:
    """Build the Vietnamese overall assessment (output 6 in the report's scope).

    Each paragraph names the measured value and the rule it was compared with,
    so the conclusion can be traced back to the numbers shown on the page.
    """
    level = brightness_level(before)
    if level == "tối":
        brightness = (
            f"μ = {vn(before.mean_gray)} nhỏ hơn ngưỡng {DARK_MEAN_THRESHOLD:.0f}: ảnh có xu hướng tối, "
            "phần lớn pixel nằm ở vùng mức xám thấp nên chi tiết vùng tối khó quan sát."
        )
    elif level == "sáng":
        brightness = (
            f"μ = {vn(before.mean_gray)} lớn hơn {BRIGHT_MEAN_THRESHOLD:.0f}: ảnh có xu hướng sáng, "
            "histogram lệch về phía phải. Chương trình chỉ nhận xét, không tự làm tối ảnh "
            "vì phạm vi đề tài tập trung vào ảnh tối và ảnh tương phản thấp."
        )
    else:
        brightness = (
            f"μ = {vn(before.mean_gray)} nằm trong khoảng [{DARK_MEAN_THRESHOLD:.0f}; {BRIGHT_MEAN_THRESHOLD:.0f}]: "
            "độ sáng tổng thể ở mức trung bình."
        )

    if is_low_contrast(before):
        contrast = (
            f"σ = {vn(before.std_gray)} nhỏ hơn ngưỡng {LOW_CONTRAST_STD_THRESHOLD:.0f}: các mức xám tập trung "
            f"trong khoảng hẹp (dải động p2–p98 chỉ {vn(before.dynamic_range, 0)} mức), ảnh có độ tương phản thấp."
        )
    else:
        contrast = (
            f"σ = {vn(before.std_gray)} không nhỏ hơn ngưỡng {LOW_CONTRAST_STD_THRESHOLD:.0f}: mức xám phân tán "
            f"đủ rộng (dải động p2–p98 là {vn(before.dynamic_range, 0)} mức), độ tương phản đạt yêu cầu."
        )

    dark_clip, bright_clip = clip_before
    clip_notes = []
    if dark_clip >= 0.05:
        clip_notes.append(f"{vn(dark_clip * 100, 1)}% pixel gần đen (≤ {CLIP_LOW_LEVEL})")
    if bright_clip >= 0.05:
        clip_notes.append(f"{vn(bright_clip * 100, 1)}% pixel gần trắng (≥ {CLIP_HIGH_LEVEL})")
    if clip_notes:
        histogram_text = (
            "Histogram có cột dồn ở đầu mút: " + " và ".join(clip_notes)
            + ". Chi tiết tại các vùng này đã bị mất khi chụp và không thể khôi phục hoàn toàn bằng biến đổi mức xám."
        )
    else:
        histogram_text = "Histogram không có hiện tượng dồn cột đáng kể ở hai đầu mút (mức 0 hoặc 255)."

    if operation == "identity":
        result = "Ảnh không vượt ngưỡng nào nên được giữ nguyên; các thông số trước và sau xử lý trùng nhau."
    else:
        result = (
            f"Sau khi áp dụng {operation_phrase(operation)}, μ: {vn(before.mean_gray)} → {vn(after.mean_gray)}, "
            f"σ: {vn(before.std_gray)} → {vn(after.std_gray)}, dải động: {vn(before.dynamic_range, 0)} → "
            f"{vn(after.dynamic_range, 0)}. Tỉ lệ pixel gần trắng sau xử lý là {vn(clip_after[1] * 100, 1)}%, "
            "cần quan sát ảnh để tránh cháy sáng."
        )

    edge_delta = (after.edge_ratio - before.edge_ratio) * 100
    if operation == "identity":
        edges = "Ảnh biên Canny không thay đổi vì ảnh được giữ nguyên."
    elif before.edge_ratio < 0.001 <= after.edge_ratio:
        edges = (
            f"Ảnh gốc gần như không có biên ({vn(before.edge_ratio * 100)}%) vì chênh lệch mức xám quá nhỏ; sau xử lý "
            f"xuất hiện {vn(after.edge_ratio * 100)}% pixel biên, cho thấy đường viền đối tượng đã lộ rõ hơn."
        )
    else:
        verb, preposition = ("tăng", "lên") if edge_delta >= 0 else ("giảm", "xuống")
        edges = (
            f"Tỉ lệ pixel biên {verb} từ {vn(before.edge_ratio * 100)}% {preposition} {vn(after.edge_ratio * 100)}%. "
            "Đây là chỉ số hỗ trợ: cần đối chiếu với ảnh để phân biệt chi tiết thật với nhiễu bị khuếch đại."
        )

    return [
        {"title": "Độ sáng", "text": brightness},
        {"title": "Độ tương phản", "text": contrast},
        {"title": "Histogram", "text": histogram_text},
        {"title": "Kết quả xử lý", "text": result},
        {"title": "Phát hiện biên Canny", "text": edges},
    ]


def interpretation_payload(
    before: ImageMetrics,
    after: ImageMetrics,
    operation: str,
    stretch_range: tuple[float, float] | None,
    clip_before: tuple[float, float],
    clip_after: tuple[float, float],
) -> dict[str, object]:
    """Return the explanatory data shown alongside each browser result.

    This API shape deliberately carries definitions, threshold comparisons, and
    transformation effects from the same server that made the decision.  The UI
    therefore does not need to duplicate image-processing policy in JavaScript.
    """
    dark, low_contrast = is_dark(before), is_low_contrast(before)
    applied_steps: list[dict[str, str]] = [
        {
            "name": "Chuyển ảnh màu sang ảnh xám",
            "formula": "Gray = 0,299·R + 0,587·G + 0,114·B",
            "effect": "Đưa ảnh về một kênh độ sáng 0–255 để Histogram, μ và σ cùng đo trên một tín hiệu.",
        }
    ]
    if "gamma" in operation:
        applied_steps.append(
            {
                "name": "Hiệu chỉnh Gamma",
                "formula": f"s = 255 · (r / 255)^γ,  γ = {vn(GAMMA_FOR_DARK_IMAGES)}",
                "effect": "γ < 1 nâng các mức xám thấp mạnh hơn mức xám cao, giúp làm sáng vùng tối mà ít làm cháy vùng sáng.",
            }
        )
    if "contrast_stretch" in operation and stretch_range is not None:
        r_min, r_max = stretch_range
        applied_steps.append(
            {
                "name": "Kéo giãn tương phản",
                "formula": (
                    f"s = (r − r_min) · 255 / (r_max − r_min),  "
                    f"r_min = {vn(r_min, 0)} (phân vị {PERCENTILE_LOW:.0f}%), r_max = {vn(r_max, 0)} (phân vị {PERCENTILE_HIGH:.0f}%)"
                ),
                "effect": (
                    f"Ánh xạ khoảng [{vn(r_min, 0)}; {vn(r_max, 0)}] ra toàn dải [0; 255], giá trị ngoài khoảng được cắt về 0 hoặc 255. "
                    "Phép kéo giãn thực hiện trên kênh độ sáng L của không gian màu Lab để giữ nguyên sắc màu của ảnh."
                ),
            }
        )
    if operation == "identity":
        applied_steps.append(
            {
                "name": "Không biến đổi",
                "formula": "s = r",
                "effect": "Ảnh không vượt ngưỡng tối hoặc tương phản thấp nên giữ nguyên giá trị mức xám ban đầu.",
            }
        )

    return {
        "metrics": {
            "mean_gray": {
                "symbol": "μ",
                "name": "Mức xám trung bình (Mean)",
                "definition": "Trung bình cộng mức xám của mọi pixel, phản ánh độ sáng tổng thể của ảnh trên thang 0–255.",
                "threshold": DARK_MEAN_THRESHOLD,
                "rule": f"μ < {DARK_MEAN_THRESHOLD:.0f} → ảnh tối.",
                "triggered": dark,
                "effect": "Giá trị tăng sau xử lý cho thấy phân bố mức xám đã dịch về phía sáng hơn.",
            },
            "std_gray": {
                "symbol": "σ",
                "name": "Độ lệch chuẩn (Standard Deviation)",
                "definition": "Mức độ phân tán của mức xám quanh μ, dùng để đánh giá độ tương phản.",
                "threshold": LOW_CONTRAST_STD_THRESHOLD,
                "rule": f"σ < {LOW_CONTRAST_STD_THRESHOLD:.0f} → ảnh tương phản thấp.",
                "triggered": low_contrast,
                "effect": "Giá trị tăng sau xử lý cho thấy các mức xám tách biệt hơn; cần xem cùng Histogram để tránh xử lý quá mức.",
            },
        },
        "overview": overview_payload(before, after, operation, clip_before, clip_after),
        "clipping": {
            "before": {"dark": number(clip_before[0] * 100), "bright": number(clip_before[1] * 100)},
            "after": {"dark": number(clip_after[0] * 100), "bright": number(clip_after[1] * 100)},
        },
        "histogram": {
            "definition": "Histogram 256 mức thống kê số pixel ở mỗi mức xám, với 0 là đen và 255 là trắng.",
            "reading": (
                "Histogram dồn về bên trái cho thấy ảnh tối; trải rộng cho thấy tương phản tốt. Đường nét đứt đánh dấu μ. "
                "Mỗi biểu đồ có trục tung riêng; cột dồn ở mức 0 hoặc 255 được ghi chú số pixel thay vì kéo giãn trục."
            ),
        },
        "canny": {
            "definition": (
                f"Ảnh xám được làm mịn bằng bộ lọc Gaussian {CANNY_BLUR_KERNEL[0]}×{CANNY_BLUR_KERNEL[1]} "
                f"(σ = {vn(CANNY_BLUR_SIGMA, 1)}), sau đó Canny tính gradient, loại bỏ điểm không cực đại và dùng ngưỡng kép "
                f"{CANNY_LOW_THRESHOLD}/{CANNY_HIGH_THRESHOLD}. Cùng một bộ tham số được áp dụng cho ảnh trước và sau xử lý."
            ),
            "reading": (
                "Đường biên liền mạch xuất hiện thêm cho thấy chi tiết đã lộ rõ; các điểm rời rạc có thể là nhiễu bị khuếch đại. "
                "Tỉ lệ biên chỉ là chỉ số hỗ trợ, không phải điểm chất lượng ảnh."
            ),
        },
        "transformations": applied_steps,
        "summary": (
            f"Trước xử lý: μ = {vn(before.mean_gray)}, σ = {vn(before.std_gray)}. "
            + (
                "Ảnh không vượt ngưỡng nào nên được giữ nguyên."
                if operation == "identity" else
                f"Sau khi {operation_phrase(operation)}: μ = {vn(after.mean_gray)}, σ = {vn(after.std_gray)}."
            )
        ),
    }


OVERLAY_ORIGINAL = "canny_overlay_original.png"
OVERLAY_ENHANCED = "canny_overlay_enhanced.png"
# BGR amber: stays visible on both the dimmed dark original and bright results.
OVERLAY_COLOR = (0, 196, 255)


def edge_overlay(image_bgr: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Draw Canny edges in colour on a dimmed copy of the image they came from.

    Dimming keeps the photo recognisable while making edge pixels the most
    salient element, so viewers can see which object each edge belongs to.
    """
    overlay = (image_bgr.astype(np.float32) * 0.55).astype(np.uint8)
    overlay[edges > 0] = OVERLAY_COLOR
    return overlay


def stage_stats(image_bgr: np.ndarray) -> dict[str, object]:
    """Grayscale μ, σ and the 256-bin histogram of one pipeline stage."""
    gray = to_gray(image_bgr)
    return {
        "mean": number(gray.mean()),
        "std": number(gray.std()),
        "hist": [int(value) for value in histogram(gray)],
    }


def pipeline_stages(
    base_url: str,
    original_name: str,
    original: np.ndarray,
    gamma_stage: np.ndarray,
    enhanced: np.ndarray,
    enhanced_name: str,
    operation: str,
    stretch_range: tuple[float, float] | None,
) -> list[dict[str, object]]:
    """Describe each image the pipeline produced, in processing order.

    The grayscale stage shares the original's statistics because every metric is
    measured on that grayscale signal; showing it as its own step makes this explicit.
    """
    original_stats = stage_stats(original)
    stages: list[dict[str, object]] = [
        {"key": "original", "label": "Ảnh gốc", "note": "Ảnh màu được tải lên", "url": f"{base_url}/{original_name}", **original_stats},
        {"key": "grayscale", "label": "Ảnh xám", "note": "Gray = 0,299R + 0,587G + 0,114B · μ, σ và histogram được đo trên ảnh này", "url": f"{base_url}/grayscale.png", **original_stats},
    ]
    if "gamma" in operation:
        stages.append({"key": "gamma", "label": "Hiệu chỉnh Gamma", "note": f"s = 255·(r/255)^γ, γ = {vn(GAMMA_FOR_DARK_IMAGES)}", "url": f"{base_url}/gamma.png", **stage_stats(gamma_stage)})
    if "contrast_stretch" in operation and stretch_range is not None:
        r_min, r_max = stretch_range
        stages.append({"key": "stretch", "label": "Kéo giãn tương phản", "note": f"[{vn(r_min, 0)}; {vn(r_max, 0)}] → [0; 255] trên kênh L", "url": f"{base_url}/{enhanced_name}", **stage_stats(enhanced)})
    if operation == "identity":
        stages.append({"key": "identity", "label": "Giữ nguyên", "note": "Không vượt ngưỡng nào, không biến đổi", "url": f"{base_url}/{enhanced_name}", **original_stats})
    stages[-1]["final"] = True
    return stages


def write_metric_exports(job_dir: Path, payload: dict[str, object], before: ImageMetrics, after: ImageMetrics,
                         clip_before: tuple[float, float], clip_after: tuple[float, float]) -> None:
    """Persist the measurements as JSON and CSV so they can be cited in the report."""
    rows = [
        ("mean_gray", "Mức xám trung bình μ", before.mean_gray, after.mean_gray),
        ("std_gray", "Độ lệch chuẩn σ", before.std_gray, after.std_gray),
        ("p02_gray", "Phân vị 2%", before.p02_gray, after.p02_gray),
        ("p98_gray", "Phân vị 98%", before.p98_gray, after.p98_gray),
        ("dynamic_range", "Dải động p2–p98", before.dynamic_range, after.dynamic_range),
        ("entropy", "Entropy (bit)", before.entropy, after.entropy),
        ("edge_ratio_percent", "Tỉ lệ biên Canny (%)", before.edge_ratio * 100, after.edge_ratio * 100),
        ("near_black_percent", f"Pixel gần đen ≤ {CLIP_LOW_LEVEL} (%)", clip_before[0] * 100, clip_after[0] * 100),
        ("near_white_percent", f"Pixel gần trắng ≥ {CLIP_HIGH_LEVEL} (%)", clip_before[1] * 100, clip_after[1] * 100),
    ]
    # utf-8-sig lets Excel open the Vietnamese labels correctly.
    with (job_dir / "metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ma_chi_so", "chi_so", "truoc_xu_ly", "sau_xu_ly"])
        for key, label, value_before, value_after in rows:
            writer.writerow([key, label, f"{value_before:.4f}", f"{value_after:.4f}"])
    export = {
        "image": payload["name"],
        "operation": payload["operation"],
        "operation_label": payload["operation_label"],
        "conditions": payload["conditions"],
        "thresholds": payload["thresholds"],
        "metrics": {key: {"label": label, "before": value_before, "after": value_after} for key, label, value_before, value_after in rows},
        "overview": payload["interpretation"]["overview"],  # type: ignore[index]
    }
    (job_dir / "metrics.json").write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")


# Each streamed event is one JSON document terminated by a newline (NDJSON).
NDJSON_NEWLINE = "\n"

# Pipeline steps reported to the browser, in execution order. Keys match the UI checklist.
PIPELINE_STEPS = ("decode", "grayscale", "measure", "enhance", "compare")


def analyse_steps(image_path: Path, original_name: str) -> Iterator[tuple[str, object]]:
    """Run one isolated browser job, yielding progress as each pipeline step finishes.

    Yields ``("step", key)`` after every step in ``PIPELINE_STEPS`` and finally
    ``("result", payload)``. The streaming endpoint forwards these events so the
    interface shows real progress instead of a timer-driven animation.
    """
    job_id = uuid.uuid4().hex
    job_dir = RUNTIME_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=False)

    try:
        # Copy the input into this job directory so each result remains self-contained.
        input_path = job_dir / f"original{image_path.suffix.lower()}"
        shutil.copyfile(image_path, input_path)
        original = read_bgr(input_path)
    except ValueError:
        # An undecodable upload must not leave an empty job directory behind.
        shutil.rmtree(job_dir, ignore_errors=True)
        raise ValueError("Không đọc được ảnh. Tệp có thể bị hỏng hoặc không đúng định dạng JPG/PNG.") from None
    yield ("step", "decode")

    gray = to_gray(original)
    yield ("step", "grayscale")
    before = measure(original)
    yield ("step", "measure")
    enhanced, operation = enhance(original, before, EnhancementConfig())
    after = measure(enhanced)
    yield ("step", "enhance")

    # Persist every required study output independently. The React interface can
    # then present each transformation without parsing a composite report image.
    enhanced_name = f"enhanced{input_path.suffix.lower()}"
    grayscale_name = "grayscale.png"
    gamma_name = "gamma.png"
    original_edges_name = "canny_original.png"
    enhanced_edges_name = "canny_enhanced.png"
    histogram_name = "histogram_comparison.png"
    comparison_name = "comparison.png"
    gamma_stage = gamma_correct(original) if is_dark(before) else original
    # The stretch bounds are measured on the exact image that enters the stretch
    # step (after gamma when gamma was applied), so the displayed r_min/r_max are
    # the values the pipeline really used.
    stretch_range = stretch_bounds(gamma_stage) if "contrast_stretch" in operation else None
    original_edges = canny_edges(gray)
    enhanced_edges = canny_edges(to_gray(enhanced))
    output_images = (
        (job_dir / enhanced_name, enhanced),
        (job_dir / grayscale_name, gray),
        (job_dir / gamma_name, gamma_stage),
        (job_dir / original_edges_name, original_edges),
        (job_dir / enhanced_edges_name, enhanced_edges),
        (job_dir / OVERLAY_ORIGINAL, edge_overlay(original, original_edges)),
        (job_dir / OVERLAY_ENHANCED, edge_overlay(enhanced, enhanced_edges)),
    )
    if not all(cv2.imwrite(str(path), image) for path, image in output_images):
        raise ValueError("Không ghi được một hoặc nhiều ảnh kết quả.")
    save_histogram_comparison(original, enhanced, job_dir / histogram_name)
    save_comparison_figure(
        Path(original_name).stem,
        original,
        enhanced,
        before,
        after,
        operation,
        job_dir / comparison_name,
    )

    conditions = []
    if is_dark(before):
        conditions.append("Ảnh tối")
    if is_low_contrast(before):
        conditions.append("Tương phản thấp")
    if is_bright(before):
        conditions.append("Ảnh có xu hướng sáng")
    if not conditions:
        conditions.append("Đạt ngưỡng, không cần xử lý")

    clip_before, clip_after = clipping_ratios(original), clipping_ratios(enhanced)
    base_url = f"/results/{job_id}"
    payload: dict[str, object] = {
        "job_id": job_id,
        "name": original_name,
        "operation": operation,
        "operation_label": operation_label(operation),
        "conditions": conditions,
        "rules": {
            "dark": f"μ < {DARK_MEAN_THRESHOLD:.0f}",
            "low_contrast": f"σ < {LOW_CONTRAST_STD_THRESHOLD:.0f}",
            "bright": f"μ > {BRIGHT_MEAN_THRESHOLD:.0f} (chỉ nhận xét)",
        },
        "metrics": metric_payload(before, after),
        "interpretation": interpretation_payload(before, after, operation, stretch_range, clip_before, clip_after),
        "original_url": f"{base_url}/{input_path.name}",
        "grayscale_url": f"{base_url}/{grayscale_name}",
        "gamma_url": f"{base_url}/{gamma_name}",
        "enhanced_url": f"{base_url}/{enhanced_name}",
        "histogram_url": f"{base_url}/{histogram_name}",
        "original_edges_url": f"{base_url}/{original_edges_name}",
        "enhanced_edges_url": f"{base_url}/{enhanced_edges_name}",
        "comparison_url": f"{base_url}/{comparison_name}",
        "download_url": f"{base_url}/{enhanced_name}?download=1",
        "original_overlay_url": f"{base_url}/{OVERLAY_ORIGINAL}",
        "enhanced_overlay_url": f"{base_url}/{OVERLAY_ENHANCED}",
        # Numeric thresholds let the UI draw gauges without duplicating policy.
        "thresholds": {
            "dark_mean": DARK_MEAN_THRESHOLD,
            "bright_mean": BRIGHT_MEAN_THRESHOLD,
            "low_contrast_std": LOW_CONTRAST_STD_THRESHOLD,
        },
        "stages": pipeline_stages(base_url, input_path.name, original, gamma_stage, enhanced, enhanced_name, operation, stretch_range),
        "downloads": [
            *([{"label": "Ảnh sau xử lý", "detail": enhanced_name.split(".")[-1].upper(), "url": f"{base_url}/{enhanced_name}?download=1"}] if operation != "identity" else []),
            {"label": "Ảnh tổng hợp so sánh", "detail": "PNG · ảnh, histogram, Canny", "url": f"{base_url}/{comparison_name}?download=1"},
            {"label": "Histogram trước – sau", "detail": "PNG", "url": f"{base_url}/{histogram_name}?download=1"},
            {"label": "Số liệu phân tích", "detail": "CSV", "url": f"{base_url}/metrics.csv?download=1"},
            {"label": "Số liệu phân tích", "detail": "JSON", "url": f"{base_url}/metrics.json?download=1"},
        ],
        "raw": {"before": asdict(before), "after": asdict(after)},
    }
    write_metric_exports(job_dir, payload, before, after, clip_before, clip_after)
    yield ("step", "compare")
    yield ("result", payload)


def analyse_path(image_path: Path, original_name: str) -> dict[str, object]:
    """Run the whole pipeline and return only the final payload (non-streaming API)."""
    for kind, value in analyse_steps(image_path, original_name):
        if kind == "result":
            return value  # type: ignore[return-value]
    raise ValueError("Phân tích kết thúc mà không có kết quả.")


def react_shell() -> Response:
    """Serve the current React entry document without allowing a stale app shell.

    Vite hashes JavaScript/CSS assets, so those files can be cached safely.  The
    HTML shell, however, points to the newest hash after each frontend build and
    must be revalidated to avoid users receiving an earlier interface.
    """
    response = make_response(send_from_directory(FRONTEND_DIST, "index.html"))
    response.cache_control.no_cache = True
    response.cache_control.must_revalidate = True
    return response


@app.get("/")
def index() -> Response:
    """Serve the built React application shell from the Flask development server."""
    return react_shell()


@app.get("/studio")
def studio() -> Response:
    """Let React Router render the analysis view on a direct navigation."""
    return react_shell()


def stage_upload() -> tuple[Path, str] | tuple[Response, int]:
    """Validate the multipart upload and save it to a staging file."""
    upload: FileStorage | None = request.files.get("image")
    if upload is None or not upload.filename:
        return jsonify(error="Hãy chọn một ảnh JPG hoặc PNG trước khi phân tích."), 400
    filename = secure_filename(upload.filename)
    if not filename or not allowed_image(filename):
        return jsonify(error="Chỉ hỗ trợ tệp JPG, JPEG và PNG."), 400
    prune_runtime()
    staging_dir = RUNTIME_DIR / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    staging_path = staging_dir / f"{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
    upload.save(staging_path)
    return staging_path, filename


@app.get("/api/health")
def health():
    """Cheap liveness check; the frontend calls it early to wake a sleeping free-tier server."""
    return jsonify(status="ok")


@app.post("/api/analyze")
def analyze_upload():
    """Validate one upload, run the shared pipeline, and return result URLs as JSON."""
    staged = stage_upload()
    if isinstance(staged[0], Response):
        return staged
    staging_path, filename = staged  # type: ignore[misc]
    try:
        return jsonify(analyse_path(staging_path, filename))
    except ValueError as error:
        return jsonify(error=str(error)), 422
    finally:
        staging_path.unlink(missing_ok=True)


@app.post("/api/analyze/stream")
def analyze_upload_stream():
    """Same pipeline as ``/api/analyze``, streamed as newline-delimited JSON events.

    Each line is one of ``{"type": "step", "step", "seconds", "elapsed"}``,
    ``{"type": "result", "elapsed", "result"}`` or ``{"type": "error", "error"}``.
    Validation failures happen before streaming and return a normal JSON error.
    """
    staged = stage_upload()
    if isinstance(staged[0], Response):
        return staged
    staging_path, filename = staged  # type: ignore[misc]

    def events() -> Iterator[str]:
        started = last = time.perf_counter()
        try:
            for kind, value in analyse_steps(staging_path, filename):
                now = time.perf_counter()
                if kind == "step":
                    yield json.dumps({"type": "step", "step": value, "seconds": round(now - last, 3), "elapsed": round(now - started, 3)}) + NDJSON_NEWLINE
                    last = now
                else:
                    yield json.dumps({"type": "result", "elapsed": round(now - started, 3), "result": value}, ensure_ascii=False) + NDJSON_NEWLINE
        except ValueError as error:
            yield json.dumps({"type": "error", "error": str(error)}, ensure_ascii=False) + NDJSON_NEWLINE
        finally:
            staging_path.unlink(missing_ok=True)

    # The staging file was saved above, so the generator never touches the request.
    return Response(events(), mimetype="application/x-ndjson", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/results/<job_id>/<path:filename>")
def result_file(job_id: str, filename: str):
    """Serve only files created by the requested analysis job."""
    job_dir = RUNTIME_DIR / job_id
    if not job_dir.is_dir() or Path(filename).name != filename:
        abort(404)
    return send_from_directory(job_dir, filename, as_attachment=request.args.get("download") == "1")


@app.get("/assets/<path:filename>")
def frontend_asset(filename: str):
    """Serve hashed Vite build assets when Flask is used without the dev server."""
    return send_from_directory(FRONTEND_DIST / "assets", filename)


@app.get("/samples/<path:filename>")
def frontend_sample(filename: str):
    """Serve the demo images copied from ``frontend/public/samples`` by Vite."""
    return send_from_directory(FRONTEND_DIST / "samples", filename)


# Logo files generated by scripts/build_logo.py and copied to dist/ by Vite.
@app.get('/<any("favicon.svg", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):name>')
def app_icon(name: str):
    """Serve the tab, touch and app icons referenced by the React shell."""
    return send_from_directory(FRONTEND_DIST, name)


@app.errorhandler(413)
def file_too_large(_error):
    """Provide a useful JSON message when Flask rejects an oversized upload."""
    return jsonify(error="Ảnh quá lớn. Hãy chọn tệp nhỏ hơn 10 MB."), 413


if __name__ == "__main__":
    # Local development server. Production (Docker on Render) runs
    # gunicorn instead; see the Dockerfile.
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", port=int(os.environ.get("PORT", "5000")))
