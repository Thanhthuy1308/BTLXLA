import { Box } from "@mui/material";
import { conditionTone, radius } from "../lib/theme";

/** Map a server condition label to its fixed colour pair. */
export function toneFor(condition: string) {
  if (condition.startsWith("Ảnh tối")) return conditionTone.dark;
  if (condition.startsWith("Tương phản thấp")) return conditionTone.lowContrast;
  if (condition.includes("sáng")) return conditionTone.bright;
  return conditionTone.ok;
}

/** Classification labels as coloured pills, identical wherever they appear. */
export default function ConditionChips({ conditions, size = "md" }: { conditions: string[]; size?: "sm" | "md" }) {
  return <Box component="span" sx={{ display: "inline-flex", flexWrap: "wrap", gap: .75 }}>
    {conditions.map((condition) => {
      const colors = toneFor(condition);
      return <Box component="span" key={condition} sx={{ display: "inline-flex", alignItems: "center", gap: .75,
        px: size === "sm" ? 1 : 1.5, py: size === "sm" ? .25 : .5, borderRadius: radius.pill, bgcolor: colors.bg, color: colors.fg,
        fontSize: size === "sm" ? 12.5 : 15, fontWeight: 700, whiteSpace: "nowrap" }}>
        <Box component="span" aria-hidden="true" sx={{ width: size === "sm" ? 6 : 8, height: size === "sm" ? 6 : 8, borderRadius: "50%", bgcolor: colors.fg }} />
        {condition}
      </Box>;
    })}
  </Box>;
}
