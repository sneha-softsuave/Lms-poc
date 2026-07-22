import { ReactNode } from "react";
import { motion } from "framer-motion";

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    published: "badge-green", draft: "badge-amber", unpublished: "badge-gray",
    approved: "badge-green", rejected: "badge-red", pending: "badge-amber",
    active: "badge-blue", completed: "badge-green", structured: "badge-blue", extracted: "badge-gray",
    queued: "badge-gray", ocr: "badge-blue", classifying: "badge-amber", done: "badge-green", failed: "badge-red",
  };
  return <span className={`badge ${map[status] || "badge-gray"}`}>{status}</span>;
}

export function DifficultyBadge({ level }: { level: string }) {
  const map: Record<string, string> = { basic: "badge-green", intermediate: "badge-amber", advanced: "badge-red" };
  return <span className={`badge ${map[level] || "badge-gray"}`}>{level}</span>;
}

export function Progress({ pct }: { pct: number }) {
  return <div className="progress"><span style={{ width: `${pct}%` }} /></div>;
}

export function ProgressRing({ pct, size = 56, stroke = 5 }: { pct: number; size?: number; stroke?: number }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(-90deg)" }}>
      <circle className="progress-ring-bg" cx={size / 2} cy={size / 2} r={r} strokeWidth={stroke} />
      <motion.circle
        className="progress-ring-fg"
        cx={size / 2} cy={size / 2} r={r}
        strokeWidth={stroke}
        strokeDasharray={c}
        initial={{ strokeDashoffset: c }}
        animate={{ strokeDashoffset: c - (Math.max(0, Math.min(100, pct)) / 100) * c }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] as const }}
      />
      <text
        x="50%" y="50%" dy=".35em" textAnchor="middle"
        transform={`rotate(90, ${size / 2}, ${size / 2})`}
        style={{ fill: "var(--text-main)", fontSize: 13, fontWeight: 600, fontFamily: "var(--font-mono)", fontVariantNumeric: "tabular-nums" }}
      >
        {Math.round(pct)}%
      </text>
    </svg>
  );
}

export function Empty({ icon = "📭", title, hint }: { icon?: string; title: string; hint?: string }) {
  return (
    <div className="empty">
      <div className="big">{icon}</div>
      <div style={{ fontWeight: 600, color: "var(--text-muted)" }}>{title}</div>
      {hint && <div className="small mt">{hint}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="row" style={{ padding: 20 }}>
      <span className="spinner" /> {label && <span className="muted">{label}</span>}
    </div>
  );
}

export function Citations({ items }: { items: any[] }) {
  if (!items?.length) return null;
  return (
    <div className="small muted mt">
      <b style={{ color: "var(--text-dim)", fontFamily: "var(--font-mono)", textTransform: "uppercase", fontSize: "var(--text-xs)" }}>Sources</b>
      <div className="pill-row mt">
        {items.map((c, i) => (
          <span key={i} className="badge badge-gray">
            {c.doc}{c.section ? ` · §${c.section}` : ""}{c.page ? ` · p${c.page}` : ""}
          </span>
        ))}
      </div>
    </div>
  );
}

export function Section({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <div className="card mb">
      <div className="card-head"><h3 style={{ margin: 0 }}>{title}</h3>{action}</div>
      <div className="card-pad">{children}</div>
    </div>
  );
}

export function StepIndicator({ steps, current, onChange }: { steps: { id: string; label: string }[]; current: string; onChange?: (id: string) => void }) {
  const curIdx = steps.findIndex((s) => s.id === current);
  return (
    <div className="step-indicator">
      {steps.map((s, i) => {
        const completed = i < curIdx;
        const active = i === curIdx;
        return (
          <button
            key={s.id}
            className={`step ${completed ? "completed" : ""} ${active ? "active" : ""}`}
            onClick={() => onChange?.(s.id)}
            disabled={!onChange}
            type="button"
          >
            <span className="step-num">{completed ? "✓" : i + 1}</span>
            <span className="step-label">{s.label}</span>
            {i < steps.length - 1 && <span className="step-line" />}
          </button>
        );
      })}
    </div>
  );
}

export function SkeletonText({ lines = 1, width = "100%" }: { lines?: number; width?: string | string[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton" style={{ width: Array.isArray(width) ? width[i] : width, height: 12 }} />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="card" style={{ padding: 20 }}>
      <SkeletonText lines={3} width={["40%", "100%", "80%"]} />
    </div>
  );
}

export function SlideOver({ open, onClose, title, children }: { open: boolean; onClose: () => void; title?: ReactNode; children: ReactNode }) {
  return (
    <>
      {open && (
        <motion.div
          className="slide-over-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        />
      )}
      <motion.aside
        className="slide-over"
        initial={{ x: "100%" }}
        animate={{ x: open ? 0 : "100%" }}
        exit={{ x: "100%" }}
        transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] as const }}
      >
        <div className="slide-over-head">
          {title && <div className="slide-over-title">{title}</div>}
          <button className="btn btn-ghost btn-sm" onClick={onClose}>Close</button>
        </div>
        <div className="slide-over-body">{children}</div>
      </motion.aside>
    </>
  );
}

export function ScoreRing({ score, size = 120 }: { score: number; size?: number }) {
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, score));
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(-90deg)" }}>
        <circle className="progress-ring-bg" cx={size / 2} cy={size / 2} r={r} strokeWidth={stroke} />
        <motion.circle
          className="progress-ring-fg"
          cx={size / 2} cy={size / 2} r={r} strokeWidth={stroke}
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c - (clamped / 100) * c }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] as const }}
        />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3, duration: 0.3 }}
          style={{ textAlign: "center" }}
        >
          <div style={{ fontSize: size * 0.32, fontWeight: 700, fontFamily: "var(--font-mono)", lineHeight: 1 }}>{Math.round(score)}%</div>
          <div style={{ fontSize: size * 0.13, color: "var(--text-muted)", fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>Score</div>
        </motion.div>
      </div>
    </div>
  );
}
