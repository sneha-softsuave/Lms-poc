import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api/client";
import { DifficultyBadge, Citations, Spinner, Empty, ScoreRing, Progress } from "./ui";
import { IconTile } from "./icons";
import { useToast } from "./Toast";

const slide = {
  initial: { opacity: 0, x: 20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -20 },
  transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] as const },
};

export function QuizPanel({ moduleId }: { moduleId: number }) {
  const toast = useToast();
  const [quiz, setQuiz] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [idx, setIdx] = useState(0);
  const [openRationale, setOpenRationale] = useState<Set<number>>(new Set());

  useEffect(() => {
    setResult(null); setAnswers({}); setLoading(true); setIdx(0); setOpenRationale(new Set());
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
    return <Empty icon={<IconTile name="course" size="lg" tone="slate" />} title="No quiz available" hint="This module has no approved questions yet." />;

  if (result) {
    return (
      <div>
        <motion.div
          className="card mb"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          style={{ background: result.passed ? "var(--ok-soft)" : "var(--error-soft)", borderColor: result.passed ? "rgba(43,182,115,0.25)" : "rgba(214,69,53,0.25)" }}
        >
          <div className="card-pad spread" style={{ alignItems: "flex-start" }}>
            <div>
              <div className="small muted" style={{ fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>Module result</div>
              <div className="stat-label">{result.correct} of {result.total} correct · pass mark {result.pass_mark}%</div>
            </div>
            <ScoreRing score={result.score_pct} size={110} />
            <span className={`badge ${result.passed ? "badge-green" : "badge-red"}`} style={{ fontSize: 15, padding: "8px 16px" }}>
              {result.passed ? "PASSED" : "NOT PASSED"}
            </span>
          </div>
        </motion.div>

        {result.results.map((r: any, i: number) => {
          const open = openRationale.has(i);
          return (
            <motion.div
              key={i}
              className="card mb"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: i * 0.05 }}
            >
              <div className="card-pad">
                <div className="spread mb">
                  <div className="row">
                    <span className="badge badge-gray">Q{i + 1}</span>
                    <DifficultyBadge level={r.difficulty || "basic"} />
                  </div>
                  <span className={`badge ${r.correct ? "badge-green" : "badge-red"}`}>{r.correct ? "Correct" : "Incorrect"}</span>
                </div>
                <div className="mb" style={{ fontWeight: 500 }}>{r.stem}</div>
                <div className="small" style={{ color: r.correct ? "var(--ok)" : "var(--text-muted)" }}>
                  Your answer: <b className="mono">{r.your_answer || "—"}</b>
                </div>
                {!r.correct && (
                  <div className="small" style={{ color: "var(--ok)" }}>
                    Correct answer: <b className="mono">{r.correct_answer}</b>
                  </div>
                )}
                <button
                  className="btn btn-ghost btn-sm mt"
                  onClick={() => setOpenRationale((s) => { const n = new Set(s); n.has(i) ? n.delete(i) : n.add(i); return n; })}
                >
                  {open ? "Hide rationale" : "Show rationale"}
                </button>
                <AnimatePresence>
                  {open && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      style={{ overflow: "hidden" }}
                    >
                      <div className="small muted mt" style={{ lineHeight: 1.65 }}>{r.rationale}</div>
                      <Citations items={r.source_ref ? [r.source_ref] : []} />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          );
        })}
        <button className="btn btn-ghost" onClick={() => { setResult(null); setAnswers({}); setIdx(0); }}>↺ Retake</button>
      </div>
    );
  }

  const qq = quiz.questions[idx];
  const progress = ((idx) / quiz.questions.length) * 100;

  return (
    <div>
      <div className="spread mb" style={{ alignItems: "flex-end" }}>
        <div>
          <div className="small muted" style={{ fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>Question {idx + 1} of {quiz.questions.length}</div>
          <div className="small" style={{ color: "var(--text-muted)" }}>Auto-graded · pass mark {quiz.pass_mark}%</div>
        </div>
        <DifficultyBadge level={qq.difficulty} />
      </div>
      <div style={{ marginBottom: 18 }}><Progress pct={progress} /></div>

      <div style={{ position: "relative", minHeight: 220 }}>
        <AnimatePresence mode="wait">
          <motion.div key={qq.id} {...slide}>
            <div className="card mb">
              <div className="card-pad">
                <div className="mb" style={{ fontSize: "var(--text-md)", fontWeight: 500, lineHeight: 1.5 }}>{qq.stem}</div>
                {qq.options ? (
                  <div className="quiz-options">
                    {qq.options.map((o: string, j: number) => {
                      const selected = answers[qq.id] === o;
                      return (
                        <label key={j} className={`quiz-option ${selected ? "selected" : ""}`}>
                          <input
                            type="radio"
                            name={`q${qq.id}`}
                            checked={selected}
                            onChange={() => setAnswers((a) => ({ ...a, [qq.id]: o }))}
                          />
                          <span className="quiz-option-marker">{String.fromCharCode(65 + j)}</span>
                          <span>{o}</span>
                        </label>
                      );
                    })}
                  </div>
                ) : (
                  <input className="input" placeholder="Your answer"
                    value={answers[qq.id] || ""} onChange={(e) => setAnswers((a) => ({ ...a, [qq.id]: e.target.value }))} />
                )}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="spread">
        <button className="btn btn-ghost" disabled={idx === 0} onClick={() => setIdx((i) => i - 1)}>Previous</button>
        {idx < quiz.questions.length - 1 ? (
          <button className="btn btn-primary" disabled={!answers[qq.id]} onClick={() => setIdx((i) => i + 1)}>Next question</button>
        ) : (
          <button className="btn btn-primary" disabled={busy || !answers[qq.id]} onClick={submit}>{busy ? "Grading…" : "Submit quiz"}</button>
        )}
      </div>
    </div>
  );
}
