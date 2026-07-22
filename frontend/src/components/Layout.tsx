import { NavLink, useNavigate } from "react-router-dom";
import { ReactNode } from "react";
import { motion } from "framer-motion";
import { useAuth } from "../auth/AuthContext";
import { IconName, IconTile } from "./icons";

const ADMIN_NAV: { to: string; label: string; ico: IconName; end?: boolean }[] = [
  { to: "/admin", label: "Overview", ico: "overview", end: true },
  { to: "/admin/materials", label: "Materials & AI", ico: "materials" },
  { to: "/admin/courses", label: "Courses & Review", ico: "courses" },
  { to: "/admin/analytics", label: "Analytics", ico: "analytics" },
  { to: "/admin/audit", label: "Audit log", ico: "audit" },
];
const LEARNER_NAV: { to: string; label: string; ico: IconName; end?: boolean }[] = [
  { to: "/catalog", label: "Course catalog", ico: "catalog" },
  { to: "/learning", label: "My learning", ico: "learning" },
  { to: "/certificates", label: "Certificates", ico: "certificates" },
];

function LogoMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M12 2L22 8.5V15.5L12 22L2 15.5V8.5L12 2Z" fill="currentColor" opacity="0.15" />
      <path d="M12 6L18 10V15L12 19L6 15V10L12 6Z" fill="currentColor" />
      <path d="M12 2L22 8.5V15.5L12 22L2 15.5V8.5L12 2Z" stroke="currentColor" strokeWidth="2" fill="none" />
    </svg>
  );
}

export function Layout({ title, children }: { title: string; children: ReactNode }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const isAdmin = user?.role === "admin";
  const items = isAdmin ? ADMIN_NAV : LEARNER_NAV;
  const initials = (user?.full_name || user?.email || "?").slice(0, 2).toUpperCase();

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><LogoMark /></div>
          <div>
            <div className="brand-name">Defense AI LMS</div>
            <div className="brand-sub">Training & Simulation</div>
          </div>
        </div>
        <div className="nav-label">{isAdmin ? "Administration" : "Learning"}</div>
        {items.map((it) => (
          <NavLink key={it.to} to={it.to} end={it.end}
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
            <IconTile name={it.ico} size="sm" tone={it.ico === "audit" ? "slate" : "blue"} />
            <span className="nav-item-label">{it.label}</span>
          </NavLink>
        ))}
        <div className="sidebar-foot">
          <div className="user-chip">
            <div className="avatar">{initials}</div>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: "var(--text-main)", fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis" }}>
                {user?.full_name || user?.email}
              </div>
              <div className="brand-sub">{user?.role}</div>
            </div>
          </div>
          <button className="btn btn-ghost btn-sm btn-block mt"
            onClick={() => { logout(); nav("/login"); }}>
            Sign out
          </button>
        </div>
      </aside>
      <div className="main">
        <div className="topbar">
          <div className="topbar-title">{title}</div>
          <div className="row" style={{ gap: 10 }}>
            <span className={`badge ${isAdmin ? "badge-blue" : "badge-green"}`}>{isAdmin ? "Admin mode" : "Learner mode"}</span>
            <span className="badge badge-gray">POC demo</span>
          </div>
        </div>
        <motion.div
          className="content"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] as const }}
        >
          {children}
        </motion.div>
      </div>
    </div>
  );
}
