import { useEffect, useRef, useState } from "react";

interface Option {
  value: string;
  label?: string;
}

interface Props {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

/**
 * A custom dark-glass dropdown that replaces <select>.
 * Native <select> dropdowns always render the OS white popup — no amount
 * of CSS can fix that. This component renders its own list so the glass
 * theme stays consistent across the whole panel.
 */
export function GlassSelect({
  value,
  options,
  onChange,
  placeholder = "— select —",
  disabled = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  // Scroll selected option into view when opening
  useEffect(() => {
    if (!open || !listRef.current) return;
    const sel = listRef.current.querySelector(".gs-option-selected") as HTMLElement | null;
    sel?.scrollIntoView({ block: "nearest" });
  }, [open]);

  const selected = options.find((o) => o.value === value);
  const displayLabel = selected ? (selected.label ?? selected.value) : null;

  return (
    <div className={`gs-wrap${disabled ? " gs-disabled" : ""}`} ref={containerRef}>
      <button
        type="button"
        className={`gs-trigger mono${open ? " gs-open" : ""}`}
        onClick={() => !disabled && setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
      >
        <span className={displayLabel ? "" : "gs-placeholder"}>
          {displayLabel ?? placeholder}
        </span>
        <svg
          className={`gs-arrow${open ? " gs-arrow-open" : ""}`}
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
        >
          <path d="M2 4.5L6 8.5L10 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="gs-dropdown" role="listbox" ref={listRef}>
          {options.length === 0 ? (
            <div className="gs-empty">No options</div>
          ) : (
            options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                role="option"
                aria-selected={opt.value === value}
                className={`gs-option mono${opt.value === value ? " gs-option-selected" : ""}`}
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
              >
                {opt.value === value && <span className="gs-check">✓</span>}
                {opt.label ?? opt.value}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
