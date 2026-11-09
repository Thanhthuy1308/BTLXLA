import { useNavigate } from "react-router-dom";
import { Box, Button, Container, Stack, Typography } from "@mui/material";
import PixelConverter from "../components/PixelConverter";
import { tone } from "../lib/theme";

const HIGHLIGHTS = [
  ["Đo lường mức xám", "Histogram 256 mức, mức xám trung bình (μ) và độ lệch chuẩn (σ)."],
  ["Phân loại theo ngưỡng", "Ảnh gốc được so sánh với ngưỡng μ < 85 (ảnh tối) và σ < 45 (tương phản thấp) trước khi xử lý."],
  ["So sánh trước – sau", "Ảnh xám, hiệu chỉnh Gamma, kéo giãn tương phản và ảnh biên Canny giúp kiểm chứng từng bước biến đổi."],
];

export default function OverviewPage() {
  const navigate = useNavigate();
  return <Box component="main"><Container maxWidth={false} sx={{ maxWidth: 1440, py: { xs: 5, lg: 8 } }}>
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, gap: { xs: 5, lg: 8 }, alignItems: "center" }}>
      <Box>
        <Typography color="primary" sx={{ mb: 2, fontSize: 14, fontWeight: 700 }}>PHÂN TÍCH ẢNH BẰNG HISTOGRAM</Typography>
        <Typography variant="h1" sx={{ maxWidth: 680 }}>Đánh giá độ sáng và độ tương phản của ảnh.</Typography>
        <Typography sx={{ mt: 3, maxWidth: 620, color: "text.secondary", fontSize: { xs: 17, md: 19 }, lineHeight: 1.6 }}>Tải ảnh lên để tính Histogram 256 mức xám, mức xám trung bình và độ lệch chuẩn. Chương trình nhận biết ảnh tối hoặc tương phản thấp, cải thiện bằng hiệu chỉnh Gamma và kéo giãn tương phản, rồi so sánh kết quả trước – sau.</Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mt: 4 }}>
          <Button variant="contained" size="large" onClick={() => navigate("/studio")}>Phân tích một ảnh</Button>
          <Button variant="outlined" size="large" onClick={() => navigate("/studio?sample=dark_low_contrast")}>Thử với ảnh mẫu</Button>
        </Stack>
      </Box>
      <Box>
        <PixelConverter originalSrc="/samples/hero_original.jpg" enhancedSrc="/samples/hero_enhanced.jpg" />
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>Ảnh mẫu LOL_LOW_10 (bộ dữ liệu LOL). Ảnh sau xử lý do chính pipeline Python của chương trình tạo ra; μ, σ và histogram được tính trực tiếp từ hai ảnh hiển thị.</Typography>
      </Box>
    </Box>
    <Box sx={{ mt: { xs: 6, lg: 9 }, pt: 4, borderTop: `1px solid ${tone.outline}`, display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" }, gap: { xs: 3, md: 5 } }}>
      {HIGHLIGHTS.map(([title, text]) => <Box key={title}><Typography sx={{ fontWeight: 700 }}>{title}</Typography><Typography color="text.secondary" sx={{ mt: .5 }}>{text}</Typography></Box>)}
    </Box>
  </Container></Box>;
}
