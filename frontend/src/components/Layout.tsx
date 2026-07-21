import { NavLink, useNavigate } from "react-router-dom";
import { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";

const ADMIN_NAV = [
  { to: "/admin", label: "Overview", ico: "▤", end: true },
  { to: "/admin/materials", label: "Materials & AI", ico: "📤" },
  { to: "/admin/courses", label: "Courses & Review", ico: "📚" },
  { to: "/admin/analytics", label: "Analytics", ico: "📊" },
  { to: "/admin/audit", label: "Audit log", ico: "🛡" },
];
const LEARNER_NAV = [
  { to: "/catalog", label: "Course catalog", ico: "🗂" },
  { to: "/learning", label: "My learning", ico: "🎓" },
  { to: "/certificates", label: "Certificates", ico: "🏅" },
];

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
          <div className="brand-mark">◆</div>
          <div>
            <div className="brand-name">Defense AI LMS</div>
            <div className="brand-sub">Training & Simulation</div>
          </div>
        </div>
        <div className="nav-label">{isAdmin ? "Administration" : "Learning"}</div>
        {items.map((it) => (
          <NavLink key={it.to} to={it.to} end={(it as any).end}
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
            <span className="ico">{it.ico}</span> {it.label}
          </NavLink>
        ))}
        <div className="sidebar-foot">
          <div className="user-chip">
            <div className="avatar">{initials}</div>
            <div style={{ minWidth: 0 }}>
              <div style={{ color: "#fff", fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis" }}>
                {user?.full_name || user?.email}
              </div>
              <div className="brand-sub">{user?.role}</div>
            </div>
          </div>
          <button className="btn btn-ghost btn-sm btn-block mt" style={{ color: "#cdd8e6", borderColor: "#1b3557" }}
            onClick={() => { logout(); nav("/login"); }}>
            Sign out
          </button>
        </div>
      </aside>
      <div className="main">
        <div className="topbar">
          <div className="topbar-title">{title}</div>
          <span className="badge badge-gray">POC demo</span>
        </div>
        <div className="content">{children}</div>
      </div>
    </div>
  );
}
