import { useEffect, useState } from "react";
import { Layout } from "../../components/Layout";
import { api } from "../../api/client";
import { useToast } from "../../components/Toast";
import { Progress, Empty, Spinner } from "../../components/ui";

export default function Analytics() {
  const toast = useToast();
  const [cohort, setCohort] = useState<any[]>([]);
  const [mastery, setMastery] = useState<any[]>([]);
  const [weakest, setWeakest] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.cohortProgress(), api.subjectMastery(), api.weakestTopics()])
      .then(([c, m, w]) => { setCohort(c); setMastery(m); setWeakest(w); })
      .finally(() => setLoading(false));
  }, []);

  async function exportCsv() {
    try { await api.downloadResultsCsv(); toast.push("Results exported", "ok"); }
    catch (e: any) { toast.push(e.message, "err"); }
  }

  if (loading) return <Layout title="Analytics"><Spinner label="Loading…" /></Layout>;

  return (
    <Layout title="Analytics">
      <div className="card mb">
        <div className="card-head">
          <h3 style={{ margin: 0 }}>Cohort progress by course</h3>
          <button className="btn btn-ghost btn-sm" onClick={exportCsv}>⭳ Export results (CSV)</button>
        </div>
        {cohort.length === 0 ? <Empty icon="📊" title="No data yet" hint="Publish a course and have learners enrol." /> : (
          <table>
            <thead><tr><th>Course</th><th>Subject</th><th>Enrolled</th><th style={{ width: 220 }}>Avg progress</th><th>Completed</th></tr></thead>
            <tbody>
              {cohort.map((c) => (
                <tr key={c.course_id}>
                  <td><b>{c.course_title}</b></td>
                  <td className="muted">{c.subject_title}</td>
                  <td>{c.enrolled}</td>
                  <td><div className="row"><div style={{ flex: 1 }}><Progress pct={c.avg_progress_pct} /></div><span className="small">{c.avg_progress_pct}%</span></div></td>
                  <td>{c.completed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div className="card">
          <div className="card-head"><h3 style={{ margin: 0 }}>Subject mastery</h3><span className="muted small">avg quiz score</span></div>
          {mastery.length === 0 ? <Empty icon="🎯" title="No quiz attempts yet" /> : (
            <div className="card-pad">
              {mastery.map((m) => (
                <div key={m.subject_title} className="mb">
                  <div className="spread"><b>{m.subject_title}</b><span className="small">{m.avg_score_pct}% · {m.attempts} attempts</span></div>
                  <Progress pct={m.avg_score_pct} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-head"><h3 style={{ margin: 0 }}>Weakest topics</h3><span className="muted small">lowest-scoring modules</span></div>
          {weakest.length === 0 ? <Empty icon="📉" title="No quiz attempts yet" /> : (
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
