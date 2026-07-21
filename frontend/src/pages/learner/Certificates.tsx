import { useEffect, useState } from "react";
import { Layout } from "../../components/Layout";
import { api, Certificate } from "../../api/client";
import { Empty, Spinner } from "../../components/ui";

export default function Certificates() {
  const [certs, setCerts] = useState<Certificate[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<Certificate | null>(null);

  useEffect(() => { api.myCertificates().then(setCerts).finally(() => setLoading(false)); }, []);

  if (loading) return <Layout title="Certificates"><Spinner label="Loading…" /></Layout>;

  return (
    <Layout title="Certificates">
      {certs.length === 0 ? (
        <div className="card"><Empty icon="🏅" title="No certificates yet"
          hint="Complete a course to earn a completion certificate." /></div>
      ) : (
        <div className="grid grid-2">
          {certs.map((c) => (
            <div key={c.serial} className="card">
              <div className="card-pad">
                <div className="spread mb"><span className="badge badge-green">Completed</span><span className="muted small">{c.serial}</span></div>
                <h4 style={{ margin: "0 0 4px" }}>{c.course_title}</h4>
                <div className="muted small">{c.subject_title}</div>
                <div className="spread mt"><span className="small">Score {c.score_pct}%</span>
                  <button className="btn btn-primary btn-sm" onClick={() => setView(c)}>View certificate</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {view && <CertModal cert={view} onClose={() => setView(null)} />}
    </Layout>
  );
}

function CertModal({ cert, onClose }: { cert: Certificate; onClose: () => void }) {
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "#0b1a2fcc", display: "grid", placeItems: "center", zIndex: 40 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: 620, maxWidth: "92vw", background: "#fff", borderRadius: 14, padding: 8 }}>
        <div style={{ border: "3px double var(--gold)", borderRadius: 10, padding: "36px 40px", textAlign: "center" }}>
          <div className="brand-sub" style={{ color: "var(--slate-500)" }}>Defense AI Training & Simulation Platform</div>
          <h2 style={{ marginTop: 18, color: "var(--navy-900)" }}>Certificate of Completion</h2>
          <p className="muted" style={{ margin: "6px 0 18px" }}>This certifies that</p>
          <div style={{ fontSize: 24, fontWeight: 800, color: "var(--navy-800)" }}>{cert.learner_name}</div>
          <p className="muted" style={{ margin: "16px 0 4px" }}>has successfully completed</p>
          <div style={{ fontSize: 18, fontWeight: 700 }}>{cert.course_title}</div>
          <div className="muted small">{cert.subject_title}</div>
          <div className="spread mt-lg" style={{ marginTop: 28 }}>
            <div className="small"><b>Score</b><div className="muted">{cert.score_pct}%</div></div>
            <div className="small"><b>Serial</b><div className="muted">{cert.serial}</div></div>
            <div className="small"><b>Issued</b><div className="muted">{new Date(cert.issued_at).toLocaleDateString()}</div></div>
          </div>
        </div>
        <div className="row" style={{ justifyContent: "flex-end", padding: 12 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => window.print()}>Print</button>
          <button className="btn btn-primary btn-sm" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
