import { useEffect, useState } from "react";
import { api } from "../api/client";
import { DifficultyBadge, Citations, Spinner, Empty } from "./ui";
import { useToast } from "./Toast";

export function QuizPanel({ moduleId }: { moduleId: number }) {
  const toast = useToast();
  const [quiz, setQuiz] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setResult(null); setAnswers({}); setLoading(true);
    api.getQuiz(moduleId).then(setQuiz).catch(() => setQuiz(null)).finally(() => setLoading(false));
  }, [moduleId]);

  async function submit() {
    setBusy(true);
    try { setResult(await api.submitQuiz(moduleId, answers)); }
    catch (e: any) { toast.push(e.message, "err"); }
    finally { setBusy(false); }
  }

  if (loading) return <Spinner label="Loading quiz…" />;
  if (!quiz || quiz.questions.length === 0)
    return <Empty icon="📝" title="No quiz available" hint="This module has no approved questions yet." />;

  if (result) {
    return (
      <div>
        <div className="card mb" style={{ background: result.passed ? "var(--green-soft)" : "var(--red-soft)" }}>
          <div className="card-pad spread">
            <div>
              <div className="stat-val">{result.score_pct}%</div>
              <div className="stat-label">{result.correct} of {result.total} correct · pass mark {result.pass_mark}%</div>
            </div>
            <span className={`badge ${result.passed ? "badge-green" : "badge-red"}`} style={{ fontSize: 15, padding: "8px 16px" }}>
              {result.passed ? "PASSED" : "NOT PASSED"}
            </span>
          </div>
        </div>
        {result.results.map((r: any, i: number) => (
          <div key={i} className="card mb">
            <div className="card-pad">
              <div className="spread mb">
                <b>Q{i + 1}</b>
                <span className={`badge ${r.correct ? "badge-green" : "badge-red"}`}>{r.correct ? "Correct" : "Incorrect"}</span>
              </div>
              <div className="small">Your answer: <b>{r.your_answer || "—"}</b></div>
              {!r.correct && <div className="small">Correct answer: <b style={{ color: "var(--green)" }}>{r.correct_answer}</b></div>}
              <div className="small muted mt">{r.rationale}</div>
              <Citations items={r.source_ref ? [r.source_ref] : []} />
            </div>
          </div>
        ))}
        <button className="btn btn-ghost" onClick={() => { setResult(null); setAnswers({}); }}>↺ Retake</button>
      </div>
    );
  }

  return (
    <div>
      <p className="muted small">{quiz.questions.length} questions · auto-graded · pass mark {quiz.pass_mark}%</p>
      {quiz.questions.map((qq: any, i: number) => (
        <div key={qq.id} className="card mb">
          <div className="card-pad">
            <div className="spread mb"><b>Q{i + 1}</b><DifficultyBadge level={qq.difficulty} /></div>
            <div className="mb">{qq.stem}</div>
            {qq.options ? (
              <div>
                {qq.options.map((o: string, j: number) => (
                  <label key={j} className="row" style={{ padding: "6px 0", cursor: "pointer" }}>
                    <input type="radio" name={`q${qq.id}`} checked={answers[qq.id] === o}
                      onChange={() => setAnswers((a) => ({ ...a, [qq.id]: o }))} />
                    {o}
                  </label>
                ))}
              </div>
            ) : (
              <input className="input" placeholder="Your answer"
                value={answers[qq.id] || ""} onChange={(e) => setAnswers((a) => ({ ...a, [qq.id]: e.target.value }))} />
            )}
          </div>
        </div>
      ))}
      <button className="btn btn-primary" disabled={busy} onClick={submit}>{busy ? "Grading…" : "Submit quiz"}</button>
    </div>
  );
}
