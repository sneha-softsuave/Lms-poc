import { ReactNode } from "react";

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    published: "badge-green", draft: "badge-amber", unpublished: "badge-gray",
    approved: "badge-green", rejected: "badge-red", pending: "badge-amber",
    active: "badge-blue", completed: "badge-green", structured: "badge-blue", extracted: "badge-gray",
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

export function Empty({ icon = "📭", title, hint }: { icon?: string; title: string; hint?: string }) {
  return (
    <div className="empty">
      <div className="big">{icon}</div>
      <div style={{ fontWeight: 600, color: "var(--slate-600)" }}>{title}</div>
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
      <b>Sources:</b>{" "}
      {items.map((c, i) => (
        <span key={i} className="badge badge-gray" style={{ marginRight: 6 }}>
          {c.doc}{c.section ? ` · §${c.section}` : ""}{c.page ? ` · p${c.page}` : ""}
        </span>
      ))}
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
