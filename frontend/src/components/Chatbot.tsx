import { useState } from "react";
import { api, ChatResponse } from "../api/client";
import { Citations } from "./ui";

interface Turn { q: string; res: ChatResponse; }

export function Chatbot({ courseId, lessonId }: { courseId: number; lessonId: number | null }) {
  const [q, setQ] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [thread, setThread] = useState<number | undefined>();
  const [busy, setBusy] = useState(false);

  async function ask() {
    if (!q.trim()) return;
    const question = q;
    setQ(""); setBusy(true);
    try {
      const res = await api.chat(courseId, lessonId, question, thread);
      setThread(res.thread_id);
      setTurns((t) => [...t, { q: question, res }]);
    } catch (e: any) {
      setTurns((t) => [...t, { q: question, res: { answer: `⚠ ${e.message}`, grounded: true, citations: [], related_lessons: [], thread_id: thread || 0 } }]);
    } finally { setBusy(false); }
  }

  return (
    <div className="card" style={{ position: "sticky", top: 20 }}>
      <div className="card-head">
        <div className="row"><span>💬</span><h3 style={{ margin: 0 }}>Doubt-clearing tutor</h3></div>
        <span className="badge badge-green">grounded</span>
      </div>
      <div className="card-pad" style={{ maxHeight: 380, overflowY: "auto" }}>
        {turns.length === 0 && (
          <p className="muted small">Ask anything about this course. Answers are grounded in the source
            material and cited — the tutor says "not covered" rather than guessing.</p>
        )}
        {turns.map((t, i) => (
          <div key={i} className="mb">
            <div className="badge badge-blue mb">You</div>
            <div className="small mb">{t.q}</div>
            {t.res.grounded ? (
              <div className="card" style={{ background: "var(--slate-50)" }}>
                <div className="card-pad" style={{ padding: 12 }}>
                  <div className="small">{t.res.answer}</div>
                  <Citations items={t.res.citations} />
                </div>
              </div>
            ) : (
              <div className="card" style={{ background: "var(--amber-soft)" }}>
                <div className="card-pad" style={{ padding: 12 }}>
                  <div className="small"><b>Not covered by the material.</b></div>
                  {t.res.related_lessons.length > 0 && (
                    <div className="small muted mt">Related: {t.res.related_lessons.map((l) => l.title).join(", ")}</div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="card-pad" style={{ borderTop: "1px solid var(--slate-100)" }}>
        <div className="row">
          <input className="input" value={q} placeholder="e.g. what is the range of the LMG?"
            onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} />
          <button className="btn btn-primary" disabled={busy} onClick={ask}>{busy ? "…" : "Ask"}</button>
        </div>
      </div>
    </div>
  );
}
