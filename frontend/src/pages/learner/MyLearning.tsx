import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Layout } from "../../components/Layout";
import { api, Enrolment } from "../../api/client";
import { Progress, StatusBadge, Empty, Spinner } from "../../components/ui";

export default function MyLearning() {
  const nav = useNavigate();
  const [items, setItems] = useState<Enrolment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.myLearning().then(setItems).finally(() => setLoading(false)); }, []);

  if (loading) return <Layout title="My learning"><Spinner label="Loading…" /></Layout>;

  return (
    <Layout title="My learning">
      {items.length === 0 ? (
        <div className="card"><Empty icon="🎓" title="You're not enrolled in any courses"
          hint="Browse the catalog and enrol to get started." /></div>
      ) : (
        <div className="grid grid-2">
          {items.map((e) => (
            <div key={e.course_id} className="card">
              <div className="card-pad">
                <div className="spread mb">
                  <span className="badge badge-blue">{e.subject_title}</span>
                  <StatusBadge status={e.status} />
                </div>
                <h4 style={{ margin: "0 0 12px" }}>{e.course_title}</h4>
                <div className="spread small mb">
                  <span className="muted">Progress</span>
                  <span><b>{e.progress_pct}%</b> <span className="muted">· {Math.round((e.time_spent_seconds || 0) / 60)} min on task</span></span>
                </div>
                <Progress pct={e.progress_pct} />
                <div className="row mt">
                  <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => nav(`/courses/${e.course_id}`)}>
                    {e.progress_pct === 0 ? "Start course" : e.status === "completed" ? "Review course" : "Resume →"}
                  </button>
                  {e.status === "completed" && (
                    <button className="btn btn-gold" onClick={() => nav("/certificates")}>🏅 Certificate</button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="muted small mt">
        <Link to="/catalog">← Back to catalog</Link>
      </p>
    </Layout>
  );
}
