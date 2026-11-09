# Histogram-Based Image Brightness and Contrast Analysis

## Abstract

Ảnh kỹ thuật số được chụp trong điều kiện thiếu sáng hoặc ánh sáng không đồng đều, thường có độ sáng kém và độ tương phản thấp, khiến các chi tiết và đường biên của đối tượng khó nhận biết.

Đề tài này đề xuất phương pháp phân tích độ sáng và độ tương phản của ảnh dựa trên Histogram. Với mỗi ảnh đầu vào, hệ thống tính Histogram 256 mức xám, mức xám trung bình và độ lệch chuẩn để nhận biết ảnh tối hoặc ảnh có độ tương phản thấp; ảnh có xu hướng sáng chỉ được nhận xét và giữ nguyên. Sau đó, chương trình áp dụng hiệu chỉnh Gamma (Gamma Correction) và kéo giãn tương phản (Contrast Stretching) tùy theo tình trạng ảnh.

Hiệu quả của từng phép cải thiện được đánh giá bằng cách so sánh các thông số thống kê, Histogram và kết quả phát hiện biên Canny trước và sau khi xử lý. Kết quả là một công cụ minh bạch, cho thấy quy tắc nào đã được áp dụng, mỗi phép biến đổi đã thay đổi ảnh như thế nào, và việc cải thiện độ sáng, độ tương phản có giúp đường biên rõ hơn hay không.

**Keywords:** cải thiện ảnh, phân tích Histogram, độ sáng, độ tương phản, hiệu chỉnh Gamma, kéo giãn tương phản, phát hiện biên Canny.

## Sample Visualization

![Hai ảnh mẫu kèm Histogram mức xám](assets/sample_cover_histograms.png)

## Quick start

Yêu cầu: **Python 3.11+** và **Node.js 20.19+ hoặc 22.12+** (Node chỉ cần để build giao diện web).

```powershell
# 1. Tạo môi trường Python và cài thư viện
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .

# 2. Build giao diện web (thư mục frontend/dist không được commit)
cd frontend
npm ci
npm run build
cd ..

# 3. Chạy server
python web/app.py
```

Mở `http://127.0.0.1:5000` trên trình duyệt. Trên macOS/Linux, kích hoạt môi
trường bằng `source .venv/bin/activate`.

Bước 2 là bắt buộc: Flask phục vụ giao diện từ `frontend/dist`, nếu bỏ qua bước
này trang web sẽ trống. Cần build lại sau mỗi lần sửa mã trong `frontend/src`.

Ảnh tải lên và kết quả phân tích được lưu trong `web/runtime/` (đã bỏ qua trong
Git). Các kết quả cũ hơn 24 giờ được tự động xóa trước mỗi lần tải ảnh mới; đổi
thời hạn bằng biến môi trường `RUNTIME_TTL_HOURS`.

## Decision rules

Mọi giá trị tính trên thang mức xám 8 bit và được định nghĩa trong `src/analysis.py`.

| Quy tắc | Điều kiện | Xử lý |
| --- | --- | --- |
| Ảnh tối | μ < 85 | Hiệu chỉnh Gamma, `s = 255·(r/255)^0.60` |
| Tương phản thấp | σ < 45 (trước hoặc sau Gamma) | Kéo giãn tương phản giữa phân vị 2% và 98%, thực hiện trên kênh L của không gian màu Lab để giữ nguyên màu sắc |
| Ảnh có xu hướng sáng | μ > 170 | Chỉ nhận xét, không biến đổi |
| Các trường hợp còn lại | — | Giữ nguyên ảnh |

Biên Canny được tính sau khi làm mịn ảnh bằng bộ lọc Gaussian 5×5 (σ = 1,4) với
ngưỡng kép cố định 50/150, áp dụng giống nhau cho ảnh trước và sau xử lý để tỉ lệ
biên có thể so sánh được. Tỉ lệ biên chỉ là chỉ số hỗ trợ, không phải điểm chất
lượng ảnh: đường biên liền mạch xuất hiện thêm cho thấy chi tiết đã lộ rõ, còn các
điểm rời rạc có thể là nhiễu bị khuếch đại.

Cơ sở lựa chọn các ngưỡng được trình bày trong `docs/rule-validation.md`.

## Command-line usage

```powershell
# Xử lý một ảnh: lưu ảnh sau xử lý, ảnh so sánh và tệp số liệu JSON
python scripts/process_image.py --input path\to\image.jpg --output data\processed\demo

# Tạo lại các ảnh mẫu cho giao diện web trong frontend/public/samples
python scripts/build_web_samples.py
```

## HTTP API

| Phương thức và đường dẫn | Chức năng |
| --- | --- |
| `POST /api/analyze` | Trường multipart `image`; trả về toàn bộ kết quả dạng JSON. |
| `POST /api/analyze/stream` | Đầu vào giống trên; trả về JSON theo từng dòng: mỗi bước xử lý hoàn tất gửi một sự kiện `step`, cuối cùng là sự kiện `result` (hoặc `error`). |
| `GET /results/<job_id>/<file>` | Các tệp do một lần phân tích tạo ra; thêm `?download=1` để tải xuống. |
| `GET /api/health` | Kiểm tra server còn hoạt động; giao diện gọi khi mở trang Phân tích để đánh thức server đang ngủ. |

## Deployment

Giao diện được đăng lên **GitHub Pages** (`https://thanhthuy1308.github.io/BTLXLA/`),
còn server phân tích (Flask + OpenCV) chạy trên **Render** (gói miễn phí) bằng
`Dockerfile` ở thư mục gốc. Cả hai tự triển khai lại khi có thay đổi được merge vào
`main`:

| Thành phần | Cấu hình | Tự triển khai khi thay đổi |
| --- | --- | --- |
| Giao diện trên GitHub Pages | `.github/workflows/deploy-pages.yml` | `frontend/` |
| Server trên Render | `render.yaml` + `Dockerfile` | `src/`, `web/app.py`, `frontend/`, `Dockerfile`, `pyproject.toml` |

Cấu hình lần đầu:

1. Đăng nhập Render bằng tài khoản GitHub, chọn **New → Blueprint**, chọn repository
   này rồi bấm **Apply**. Render đọc `render.yaml`, build `Dockerfile` và cấp địa
   chỉ dạng `https://btlxla.onrender.com`.
2. Trong repository GitHub, mở *Settings → Secrets and variables → Actions →
   Variables* và thêm `API_BASE_URL` = địa chỉ Render ở bước 1.
3. Mở *Settings → Pages*, chọn **Source: GitHub Actions**.
4. Vào tab *Actions*, chạy workflow **Deploy frontend to GitHub Pages** bằng
   **Run workflow** (các lần sau sẽ tự chạy khi merge vào `main`).

Server chỉ nhận yêu cầu từ trang GitHub Pages của dự án; đổi danh sách này bằng
biến môi trường `ALLOWED_ORIGINS` trên Render.

Gói miễn phí của Render có 512 MB RAM và tự ngủ sau 15 phút không có yêu cầu; lần
phân tích đầu tiên sau đó có thể mất khoảng một phút để server khởi động lại. Trang
Phân tích tự gửi yêu cầu đánh thức ngay khi được mở.

## Experimental Evaluation

Bộ benchmark có thể tái lập gồm 54 ảnh: ảnh thiếu sáng và ảnh chụp trong điều kiện
ánh sáng yếu tự nhiên, ảnh đối chứng bình thường hoặc quá sáng, ảnh cá nhân dùng để
kiểm tra nhanh, và sáu biến thể tương phản thấp được tạo có kiểm soát. Chạy toàn bộ
thực nghiệm và tổng hợp kết quả bằng các lệnh:

```powershell
python scripts/run_benchmark.py --output outputs/benchmark
python scripts/analyze_benchmark.py --metrics outputs/benchmark/metrics.csv --output outputs/analysis
python scripts/evaluate_lol_references.py --output outputs/analysis/full_reference
```

Ở lần chạy hiện tại, chương trình chọn hiệu chỉnh Gamma kết hợp kéo giãn tương phản
cho 25 ảnh, chỉ hiệu chỉnh Gamma cho 7 ảnh, chỉ kéo giãn tương phản cho 6 ảnh và giữ
nguyên 16 ảnh. Các phép kiểm tra đối chứng cho kết quả đúng như mong đợi: cả 21 ảnh
thiếu sáng đều thỏa quy tắc ảnh tối; cả sáu ảnh tương phản thấp được tạo có kiểm soát
đều được kéo giãn tương phản; sáu ảnh đối chứng bình thường và bảy ảnh quá sáng đều
được giữ nguyên.

Trên toàn bộ tập ảnh, mức xám trung bình tăng trung bình 41,04, dải động (phân vị
2–98%) tăng 106,19 và mật độ biên Canny tăng 0,0499. Các thay đổi này thể hiện phản
ứng về tông màu và cấu trúc của ảnh, không phải điểm chất lượng tuyệt đối: với những
ảnh tối nhất, chi tiết hữu ích có thể lộ ra cùng với nhiễu bị khuếch đại. Phần thảo
luận chi tiết và các trường hợp tiêu biểu được trình bày trong
`outputs/analysis/findings.md`.

> **Lưu ý:** kết quả benchmark đã commit được tạo trước khi bước Canny được bổ sung
> làm mịn Gaussian và đổi sang ngưỡng 50/150 (trước đây là 100/200 trên ảnh gốc).
> Các số liệu về độ sáng, độ tương phản, PSNR và SSIM không bị ảnh hưởng, nhưng
> các giá trị mật độ biên trong `outputs/` và con số 0,0499 ở trên sẽ thay đổi khi
> chạy lại benchmark.

### Full-reference result on paired LOL images

Chỉ 14 ảnh LOL có ảnh đối chiếu đủ sáng, cùng cảnh và căn chỉnh đúng từng điểm ảnh
mới đủ điều kiện để đánh giá có tham chiếu; các ảnh còn lại trong benchmark được loại
ra vì PSNR và SSIM yêu cầu cùng một cảnh và cùng hình học điểm ảnh. Trên tập con này,
ảnh sau xử lý nâng PSNR trung bình từ **8,04 lên 16,76 dB** (+8,72 dB; 13/14 cặp
cải thiện) và SSIM mức xám trung bình từ **0,208 lên 0,523** (+0,315; 14/14 cặp cải
thiện). `LOL_LOW_12` là trường hợp duy nhất PSNR giảm (−0,74 dB) dù SSIM tăng
0,216, vì vậy phương pháp nên được xem là một baseline có thể tái lập, không phải
bảo đảm độ chính xác trên từng điểm ảnh. Tệp CSV theo từng cặp ảnh, tệp tổng hợp
JSON và biểu đồ được lưu trong `outputs/analysis/full_reference/`.
