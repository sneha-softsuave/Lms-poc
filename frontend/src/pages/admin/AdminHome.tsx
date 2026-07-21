import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../../components/Layout";
import { api } from "../../api/client";
import { Spinner } from "../../components/ui";

function Stat({ ico, val, label, tone }: { ico: string; val: any; label: string; tone: string }) {
  return (
    <div className="card stat">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="stat-ico" style={{ background: `var(--${tone}-soft)`, color: `var(--${tone})` }}>{ico}</div>
      </div>
      <div className="stat-val mt">{val}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default function AdminHome() {
  const [cohort, setCohort] = useState<any[]>([]);
  const [docs, setDocs] = useState<any[]>([]);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.cohortProgress(), api.listDocs(), api.listDrafts()])
      .then(([c, d, dr]) => { setCohort(c); setDocs(d); setDrafts(dr); })
      .finally(() => setLoading(false));
  }, []);

  const publishedCount = cohort.length;
  const enrolled = cohort.reduce((s, c) => s + (c.enrolled || 0), 0);
  const completed = cohort.reduce((s, c) => s + (c.completed || 0), 0);

  if (loading) return <Layout title="Overview"><Spinner label="Loading dashboard…" /></Layout>;

  return (
    <Layout title="Administration overview">
      <div className="grid grid-4 mb">
        <Stat ico="📄" val={docs.length} label="Uploaded documents" tone="blue" />
        <Stat ico="📝" val={drafts.length} label="Draft courses to review" tone="amber" />
        <Stat ico="📚" val={publishedCount} label="Published courses" tone="green" />
        <Stat ico="🎓" val={enrolled} label="Total enrolments" tone="blue" />
      </div>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div className="card">
          <div className="card-head"><h3 style={{ margin: 0 }}>Course engagement</h3><Link className="small" to="/admin/analytics">View analytics →</Link></div>
          {cohort.length === 0 ? (
            <div className="card-pad muted">No published courses yet. <Link to="/admin/materials">Generate one →</Link></div>
          ) : (
            <table>
              <thead><tr><th>Course</th><th>Enrolled</th><th>Avg progress</th><th>Completed</th></tr></thead>
              <tbody>
                {cohort.map((c) => (
                  <tr key={c.course_id}>
                    <td><b>{c.course_title}</b><div className="muted small">{c.subject_title}</div></td>
                    <td>{c.enrolled}</td>
                    <td>{c.avg_progress_pct}%</td>
                    <td>{c.completed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <div className="card-head"><h3 style={{ margin: 0 }}>Quick actions</h3></div>
          <div className="card-pad">
            <Link to="/admin/materials" className="btn btn-primary btn-block mb">📤 Upload material & generate a course</Link>
            <Link to="/admin/courses" className="btn btn-ghost btn-block mb">📚 Review & publish draft courses</Link>
            <Link to="/admin/analytics" className="btn btn-ghost btn-block mb">📊 Cohort analytics & weakest topics</Link>
            <Link to="/admin/audit" className="btn btn-ghost btn-block">🛡 Audit log</Link>
            <div className="divider" />
            <p className="muted small" style={{ margin: 0 }}>
              Workflow: upload → generate → review & approve questions → publish. Published courses
              appear in the learner catalog and are indexed for the doubt-clearing chatbot.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}
