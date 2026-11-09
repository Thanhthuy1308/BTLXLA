import { useRef } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { Box, ButtonBase } from "@mui/material";
import { radius, tone } from "../lib/theme";

export type PillOption<T extends string> = { value: T; label: ReactNode };

/**
 * Pill-shaped single-choice control. The selected option gets its pill
 * background immediately (no sliding animation, which felt laggy).
 *
 * - `variant="plain"`: page-level tabs (role tablist/tab).
 * - `variant="segmented"`: compact mode switch inside a grey track (role radiogroup/radio).
 * Arrow keys, Home and End move the selection, as in native tab and radio groups.
 */
export default function PillTabs<T extends string>({ options, value, onChange, label, variant = "plain" }: {
  options: PillOption<T>[]; value: T; onChange: (value: T) => void; label: string; variant?: "plain" | "segmented";
}) {
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const tabs = variant === "plain";
  const segmented = !tabs;

  const onKeyDown = (event: KeyboardEvent) => {
    if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const index = options.findIndex((option) => option.value === value);
    const next = event.key === "Home" ? 0 : event.key === "End" ? options.length - 1
      : (index + (event.key === "ArrowRight" ? 1 : -1) + options.length) % options.length;
    onChange(options[next].value);
    buttons.current[next]?.focus();
  };

  return <Box role={tabs ? "tablist" : "radiogroup"} aria-label={label} onKeyDown={onKeyDown}
    sx={{ display: "inline-flex", flexWrap: "wrap", gap: .5, p: segmented ? .5 : 0, borderRadius: radius.pill, bgcolor: segmented ? tone.surfaceContainer : "transparent" }}>
    {options.map((option, index) => {
      const selected = option.value === value;
      const selectedBg = segmented ? "#fff" : "#e8eaed";
      return <ButtonBase key={option.value} ref={(element) => { buttons.current[index] = element; }}
        role={tabs ? "tab" : "radio"} aria-selected={tabs ? selected : undefined} aria-checked={tabs ? undefined : selected}
        tabIndex={selected ? 0 : -1} onClick={() => onChange(option.value)} focusRipple
        sx={{ minHeight: segmented ? 30 : 36, px: segmented ? 1.5 : 1.75, gap: .75, borderRadius: radius.pill, fontWeight: 650, fontSize: segmented ? 13 : 14, whiteSpace: "nowrap",
          color: selected ? tone.onSurface : tone.onSurfaceVariant,
          bgcolor: selected ? selectedBg : "transparent",
          border: segmented ? `1px solid ${selected ? tone.outline : "transparent"}` : "none",
          transition: "color .15s",
          "&:hover": { color: tone.onSurface, bgcolor: selected ? selectedBg : "rgba(32,33,36,.05)" },
          "&.Mui-focusVisible": { outline: `2px solid ${tone.primary}`, outlineOffset: 2 } }}>
        {option.label}
      </ButtonBase>;
    })}
  </Box>;
}
