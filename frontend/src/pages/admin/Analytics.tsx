import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Layout } from "../../components/Layout";
import { api } from "../../api/client";
import { useToast } from "../../components/Toast";
import { Progress, Empty, Spinner } from "../../components/ui";
import { Icon } from "../../components/icons";
import { IconTile } from "../../components/icons";

function MiniBar({ value, color = "var(--accent)", label, sub }: { value: number; color?: string; label: string; sub?: string }) {
  return (
    <div className="mb">
      <div className="spread small mb">
        <span style={{ fontWeight: 500 }}>{label}</span>
        <span className="mono" style={{ color: "var(--text-muted)" }}>{value}%</span>
      </div>
      <div className="progress" style={{ height: 10, background: "var(--base-700)" }}>
        <motion.span
          style={{ background: color, boxShadow: `0 0 10px ${color}` }}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] as const }}
        />
      </div>
      {sub && <div className="small dim mt">{sub}</div>}
    </div>
  );
}

export default function Analytics() {
  const toast = useToast();
  const [cohort, setCohort] = useState<any[]>([]);
  const [mastery, setMastery] = useState<any[]>([]);
  const [weakest, setWeakest] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [exported, setExported] = useState(false);

  useEffect(() => {
    Promise.all([api.cohortProgress(), api.subjectMastery(), api.weakestTopics()])
      .then(([c, m, w]) => { setCohort(c); setMastery(m); setWeakest(w); })
      .finally(() => setLoading(false));
  }, []);

  async function exportCsv() {
    try {
      await api.downloadResultsCsv();
      setExported(true);
      toast.push("Results exported", "ok");
      setTimeout(() => setExported(false), 2200);
    }
    catch (e: any) { toast.push(e.message, "err"); }
  }

  const stats = useMemo(() => {
    const totalEnrolled = cohort.reduce((s, c) => s + (c.enrolled || 0), 0);
    const avgProgress = cohort.length ? Math.round(cohort.reduce((s, c) => s + (c.avg_progress_pct || 0), 0) / cohort.length) : 0;
    const totalCompleted = cohort.reduce((s, c) => s + (c.completed || 0), 0);
    return { courses: cohort.length, enrolled: totalEnrolled, avgProgress, completed: totalCompleted };
  }, [cohort]);

  if (loading) return <Layout title="Analytics"><Spinner label="Loading…" /></Layout>;

  return (
    <Layout title="Analytics">
      <div className="grid grid-4 mb">
        <motion.div className="card stat" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
          <div className="stat-val">{stats.courses}</div>
          <div className="stat-label">Active courses</div>
        </motion.div>
        <motion.div className="card stat" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25, delay: 0.05 }}>
          <div className="stat-val">{stats.enrolled.toLocaleString()}</div>
          <div className="stat-label">Total enrolments</div>
        </motion.div>
        <motion.div className="card stat" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25, delay: 0.1 }}>
          <div className="stat-val">{stats.avgProgress}%</div>
          <div className="stat-label">Avg progress</div>
        </motion.div>
        <motion.div className="card stat" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25, delay: 0.15 }}>
          <div className="stat-val">{stats.completed.toLocaleString()}</div>
          <div className="stat-label">Completed</div>
        </motion.div>
      </div>

      <div className="card mb">
        <div className="card-head">
          <div className="row">
            <IconTile name="analytics" size="sm" tone="blue" />
            <h3 style={{ margin: 0 }}>Cohort progress by course</h3>
          </div>
          <button className={`btn btn-sm ${exported ? "btn-success" : "btn-ghost"}`} onClick={exportCsv}>
            <AnimatePresence mode="wait">
              {exported ? (
                <motion.span key="ok" className="row" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}><Icon name="check" /> Exported</motion.span>
              ) : (
                <motion.span key="export" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 4 }}>⭳ Export results (CSV)</motion.span>
              )}
            </AnimatePresence>
          </button>
        </div>
        {cohort.length === 0 ? <Empty icon={<IconTile name="analytics" size="lg" tone="slate" />} title="No data yet" hint="Publish a course and have learners enrol." /> : (
          <table>
            <thead><tr><th>Course</th><th>Subject</th><th>Enrolled</th><th style={{ width: 220 }}>Avg progress</th><th>Completed</th></tr></thead>
            <tbody>
              {cohort.map((c) => (
                <tr key={c.course_id}>
                  <td><b>{c.course_title}</b></td>
                  <td className="muted">{c.subject_title}</td>
                  <td className="mono">{c.enrolled}</td>
                  <td><div className="row"><div style={{ flex: 1 }}><Progress pct={c.avg_progress_pct} /></div><span className="small mono">{c.avg_progress_pct}%</span></div></td>
                  <td className="mono">{c.completed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div className="card">
          <div className="card-head"><h3 style={{ margin: 0 }}>Subject mastery</h3><span className="muted small mono">avg quiz score</span></div>
          {mastery.length === 0 ? <Empty icon={<IconTile name="award" size="lg" tone="slate" />} title="No quiz attempts yet" /> : (
            <div className="card-pad">
              {mastery.map((m) => (
                <MiniBar
                  key={m.subject_title}
                  label={m.subject_title}
                  value={m.avg_score_pct}
                  color={m.avg_score_pct < 60 ? "var(--error)" : m.avg_score_pct < 80 ? "var(--warn)" : "var(--ok)"}
                  sub={`${m.attempts} attempt${m.attempts === 1 ? "" : "s"}`}
                />
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-head"><h3 style={{ margin: 0 }}>Weakest topics</h3><span className="muted small mono">lowest-scoring modules</span></div>
          {weakest.length === 0 ? <Empty icon={<IconTile name="chart" size="lg" tone="slate" />} title="No quiz attempts yet" /> : (
            <table>
              <thead><tr><th>Module</th><th>Course</th><th>Avg score</th></tr></thead>
              <tbody>
                {weakest.map((w) => (
                  <tr key={w.module_id}>
                    <td><b>{w.module_title}</b></td>
                    <td className="muted">{w.course_title}</td>
                    <td><span className={`badge ${w.avg_score_pct < 60 ? "badge-red" : w.avg_score_pct < 80 ? "badge-amber" : "badge-green"}`}>{w.avg_score_pct}%</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </Layout>
  );
}
