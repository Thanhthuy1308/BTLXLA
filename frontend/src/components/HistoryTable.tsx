import { Box, Button, ButtonBase, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { fixed } from "../lib/format";
import { historyCsv } from "../lib/history";
import type { HistoryEntry } from "../lib/history";
import { tone } from "../lib/theme";

function exportCsv(entries: HistoryEntry[]) {
  const url = URL.createObjectURL(new Blob([historyCsv(entries)], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "so-sanh-nhieu-anh.csv";
  link.click();
  URL.revokeObjectURL(url);
}

const change = (before: number, after: number, digits = 2, unit = "") =>
  Math.abs(after - before) < 10 ** -digits / 2 ? `${fixed(before, digits)}${unit}` : `${fixed(before, digits)} → ${fixed(after, digits)}${unit}`;

/**
 * Every image analysed in this tab, side by side. Useful for the report's
 * experiment chapter: the same rules applied to many inputs, one row each.
 */
export default function HistoryTable({ entries, currentId, onOpen, onClear }: {
  entries: HistoryEntry[]; currentId?: string; onOpen: (entry: HistoryEntry) => void; onClear: () => void;
}) {
  if (!entries.length) return <Typography color="text.secondary">Chưa có ảnh nào được phân tích trong phiên này.</Typography>;
  return <Box>
    <Stack direction={{ xs: "column", sm: "row" }} sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, gap: 1.5, mb: 1.5 }}>
      <Typography color="text.secondary">{entries.length} ảnh đã phân tích trong phiên này · bấm một dòng để mở lại kết quả.</Typography>
      <Stack direction="row" spacing={1}>
        <Button size="small" variant="outlined" onClick={() => exportCsv(entries)} sx={{ minHeight: 36 }}>Xuất CSV</Button>
        <Button size="small" color="inherit" onClick={onClear} sx={{ minHeight: 36 }}>Xoá lịch sử</Button>
      </Stack>
    </Stack>
    <Box sx={{ overflowX: "auto", border: `1px solid ${tone.outline}`, borderRadius: 1.5 }}>
      <Table size="small" sx={{ minWidth: 860, "& th": { fontWeight: 700, whiteSpace: "nowrap", bgcolor: "#fafbfc" }, "& td": { fontVariantNumeric: "tabular-nums" }, "& td.MuiTableCell-alignRight": { whiteSpace: "nowrap" } }}>
        <TableHead><TableRow>
          <TableCell>Ảnh</TableCell><TableCell>Phân loại</TableCell><TableCell>Phép xử lý</TableCell>
          <TableCell align="right">μ</TableCell><TableCell align="right">σ</TableCell><TableCell align="right">Dải động</TableCell><TableCell align="right">Tỉ lệ biên</TableCell><TableCell align="right">Thời gian</TableCell>
        </TableRow></TableHead>
        <TableBody>{entries.map((entry) => {
          const { result: r } = entry;
          const active = r.job_id === currentId;
          return <TableRow key={r.job_id} hover selected={active} onClick={() => onOpen(entry)} sx={{ cursor: "pointer" }}>
            <TableCell>
              <ButtonBase onClick={(event) => { event.stopPropagation(); onOpen(entry); }} aria-label={`Mở lại kết quả ${r.name}`} sx={{ display: "flex", gap: 1.25, alignItems: "center", textAlign: "left", borderRadius: .5 }}>
                <Box component="img" src={r.original_url} alt="" sx={{ width: 56, height: 42, objectFit: "cover", borderRadius: .5, bgcolor: tone.surfaceContainer, flexShrink: 0 }} />
                <Typography sx={{ fontSize: 13.5, fontWeight: active ? 700 : 500, maxWidth: 180 }} noWrap>{r.name}</Typography>
              </ButtonBase>
            </TableCell>
            <TableCell sx={{ color: tone.primary, fontWeight: 650 }}>{r.conditions.join(" · ")}</TableCell>
            <TableCell>{r.operation_label}</TableCell>
            <TableCell align="right">{change(r.metrics.mean_gray.before, r.metrics.mean_gray.after)}</TableCell>
            <TableCell align="right">{change(r.metrics.std_gray.before, r.metrics.std_gray.after)}</TableCell>
            <TableCell align="right">{change(r.metrics.dynamic_range.before, r.metrics.dynamic_range.after, 0)}</TableCell>
            <TableCell align="right">{change(r.metrics.edge_ratio.before, r.metrics.edge_ratio.after, 2, "%")}</TableCell>
            <TableCell align="right">{fixed(entry.elapsed, 1)} s</TableCell>
          </TableRow>;
        })}</TableBody>
      </Table>
    </Box>
  </Box>;
}
