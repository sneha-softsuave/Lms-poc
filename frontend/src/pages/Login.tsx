import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api/client";
import { useToast } from "../components/Toast";
import { IconTile } from "../components/icons";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("admin@defense-lms.org");
  const [password, setPassword] = useState("admin12345");
  const [fullName, setFullName] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    try {
      if (mode === "register") {
        await api.register(email, password, fullName);
        toast.push("Account created — signing in", "ok");
      }
      const u = await login(email, password);
      nav(u.role === "admin" ? "/admin" : "/catalog");
    } catch (e: any) {
      toast.push(e.message || "Sign-in failed", "err");
    } finally {
      setBusy(false);
    }
  }

  function fill(role: "admin" | "learner") {
    if (role === "admin") { setEmail("admin@defense-lms.org"); setPassword("admin12345"); setMode("login"); }
    else { setEmail("cadet@defense-lms.org"); setPassword("cadet12345"); }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-brand">
        <div className="brand" style={{ padding: 0, marginBottom: 32 }}>
          <div className="brand-mark" style={{ width: 48, height: 48, fontSize: 20 }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L22 8.5V15.5L12 22L2 15.5V8.5L12 2Z" fill="currentColor" opacity="0.15" />
              <path d="M12 6L18 10V15L12 19L6 15V10L12 6Z" fill="currentColor" />
              <path d="M12 2L22 8.5V15.5L12 22L2 15.5V8.5L12 2Z" stroke="currentColor" strokeWidth="2" fill="none" />
            </svg>
          </div>
          <div>
            <div className="brand-name" style={{ fontSize: 22 }}>Defense AI LMS</div>
            <div className="brand-sub">Training & Simulation Platform</div>
          </div>
        </div>
        <h1 style={{ color: "var(--text-main)", fontSize: 36, maxWidth: 520, lineHeight: 1.15 }}>
          Turn manuals into trackable, interactive courses.
        </h1>
        <p style={{ color: "var(--text-muted)", maxWidth: 480, fontSize: 16 }}>
          Upload source material and the platform auto-generates subjects, courses and quizzes.
          Learners study self-paced with an in-lesson AI doubt-clearing tutor and interactive 3D
          equipment — all grounded in the source, with citations.
        </p>
        <div className="pill-row mt-lg">
          {["AI course generation", "Grounded chatbot", "Interactive 3D", "Progress & analytics", "Air-gap ready"].map((f) => (
            <span key={f} className="badge" style={{ background: "rgba(74, 139, 223, 0.14)", color: "var(--accent-bright)", borderColor: "rgba(74, 139, 223, 0.22)" }}>{f}</span>
          ))}
        </div>
      </div>

      <div className="auth-form">
        <div className="auth-card">
          <div className="row" style={{ marginBottom: 8 }}>
            <IconTile name="shield" size="md" tone="slate" />
          </div>
          <h2 style={{ marginBottom: 6 }}>{mode === "login" ? "Sign in" : "Create account"}</h2>
          <p className="muted small mb">{mode === "login" ? "Access your training dashboard." : "Register as a learner."}</p>

          {mode === "register" && (
            <div className="mb">
              <label className="label">Full name</label>
              <input className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Jane Doe" />
            </div>
          )}
          <div className="mb">
            <label className="label">Email</label>
            <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="mb">
            <label className="label">Password</label>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()} />
          </div>
          <button className="btn btn-primary btn-block" disabled={busy} onClick={submit}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account & sign in"}
          </button>

          <div className="small mt" style={{ textAlign: "center" }}>
            {mode === "login" ? (
              <>New learner? <a onClick={() => setMode("register")} style={{ cursor: "pointer" }}>Create an account</a></>
            ) : (
              <>Have an account? <a onClick={() => setMode("login")} style={{ cursor: "pointer" }}>Sign in</a></>
            )}
          </div>

          <div className="demo-creds mt-lg">
            <b style={{ color: "var(--text-main)" }}>Demo accounts</b>
            <div className="spread mt" style={{ gap: 8 }}>
              <span>Admin · full authoring</span>
              <button className="btn btn-ghost btn-sm" onClick={() => fill("admin")}>Use</button>
            </div>
            <div className="spread" style={{ gap: 8, marginTop: 6 }}>
              <span>Learner · study & quizzes</span>
              <button className="btn btn-ghost btn-sm" onClick={() => fill("learner")}>Use</button>
            </div>
            <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
              (Register the learner once if it doesn't exist yet.)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
