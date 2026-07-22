import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Layout } from "../../components/Layout";
import { api, Enrolment } from "../../api/client";
import { ProgressRing, StatusBadge, Empty, Spinner } from "../../components/ui";
import { IconTile } from "../../components/icons";

export default function MyLearning() {
  const nav = useNavigate();
  const [items, setItems] = useState<Enrolment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.myLearning().then(setItems).finally(() => setLoading(false)); }, []);

  if (loading) return <Layout title="My learning"><Spinner label="Loading…" /></Layout>;

  return (
    <Layout title="My learning">
      {items.length === 0 ? (
        <div className="card"><Empty icon={<IconTile name="learning" size="lg" tone="slate" />} title="You're not enrolled in any courses"
          hint="Browse the catalog and enrol to get started." /></div>
      ) : (
        <div className="grid grid-2">
          {items.map((e, i) => (
            <motion.div
              key={e.course_id}
              className="card"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: i * 0.06 }}
            >
              <div className="card-pad">
                <div className="spread mb">
                  <span className="badge badge-blue">{e.subject_title}</span>
                  <StatusBadge status={e.status} />
                </div>
                <h4 style={{ margin: "0 0 12px" }}>{e.course_title}</h4>
                <div className="spread" style={{ alignItems: "flex-start" }}>
                  <div style={{ flex: 1 }}>
                    <div className="spread small mb">
                      <span className="muted mono">PROGRESS</span>
                      <span className="mono" style={{ color: "var(--text-muted)" }}>{Math.round((e.time_spent_seconds || 0) / 60)} min</span>
                    </div>
                    <div className="row">
                      <div style={{ flex: 1 }}><ProgressRing pct={e.progress_pct} size={48} stroke={4} /></div>
                    </div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 130 }}>
                    <button className="btn btn-primary btn-sm btn-block" onClick={() => nav(`/courses/${e.course_id}`)}>
                      {e.progress_pct === 0 ? "Start" : e.status === "completed" ? "Review" : "Resume →"}
                    </button>
                    {e.status === "completed" && (
                      <button className="btn btn-gold btn-sm btn-block" onClick={() => nav("/certificates")}>
                        <span className="row"><IconTile name="certificates" size="sm" tone="slate" /> Certificate</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
      <p className="muted small mt">
        <Link to="/catalog">← Back to catalog</Link>
      </p>
    </Layout>
  );
}
