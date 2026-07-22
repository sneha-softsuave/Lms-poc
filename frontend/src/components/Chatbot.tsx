import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api, ChatResponse } from "../api/client";

interface Turn { q: string; res: ChatResponse; }

function CitationChip({ c, idx }: { c: any; idx: number }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="citation-chip-wrap">
      <button className="citation-chip" onClick={() => setOpen((v) => !v)} type="button">
        <span className="citation-idx">[{idx + 1}]</span>
        <span className="citation-ref">{c.doc}{c.section ? ` · §${c.section}` : ""}{c.page ? ` · p${c.page}` : ""}</span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="citation-snippet"
            initial={{ opacity: 0, height: 0, marginTop: 0 }}
            animate={{ opacity: 1, height: "auto", marginTop: 6 }}
            exit={{ opacity: 0, height: 0, marginTop: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="small dim">Source reference from <b>{c.doc}</b>{c.section && <span>, section {c.section}</span>}{c.page && <span>, page {c.page}</span>}.</div>
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  );
}

function TypingDots() {
  return (
    <div className="typing-dots">
      <span /><span /><span />
    </div>
  );
}

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
    <div className="card chatbot-console" style={{ position: "sticky", top: 20 }}>
      <div className="card-head chatbot-head">
        <div className="row">
          <span className="chatbot-status" />
          <h3 style={{ margin: 0 }}>Doubt-clearing tutor</h3>
        </div>
        <span className="badge badge-green">grounded</span>
      </div>
      <div className="chatbot-feed">
        {turns.length === 0 && (
          <div className="chatbot-empty">
            <div className="big">◈</div>
            <p className="muted small">Ask anything about this course. Answers are grounded in the source material and cited — the tutor says "not covered" rather than guessing.</p>
          </div>
        )}
        {turns.map((t, i) => (
          <div key={i} className="chatbot-turn">
            <div className="chatbot-user">
              <span className="chatbot-avatar user">YOU</span>
              <motion.div
                className="chatbot-bubble user-bubble"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
              >
                {t.q}
              </motion.div>
            </div>
            <div className="chatbot-assistant">
              <span className="chatbot-avatar assistant">AI</span>
              <motion.div
                className={`chatbot-bubble assistant-bubble ${t.res.grounded ? "" : "abstained"}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: 0.08 }}
              >
                {!t.res.grounded && (
                  <div className="badge badge-amber mb" style={{ display: "inline-flex" }}>Not covered</div>
                )}
                <div className="chatbot-answer">{t.res.answer}</div>
                {t.res.citations.length > 0 && (
                  <div className="chatbot-citations">
                    {t.res.citations.map((c, ci) => <CitationChip key={ci} c={c} idx={ci} />)}
                  </div>
                )}
                {!t.res.grounded && t.res.related_lessons.length > 0 && (
                  <div className="small muted mt">Related: {t.res.related_lessons.map((l) => l.title).join(", ")}</div>
                )}
              </motion.div>
            </div>
            {busy && i === turns.length - 1 && (
              <div className="chatbot-assistant">
                <span className="chatbot-avatar assistant">AI</span>
                <div className="chatbot-bubble assistant-bubble"><TypingDots /></div>
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="chatbot-input">
        <input
          className="input"
          value={q}
          placeholder="e.g. what is the range of the LMG?"
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
        />
        <button className="btn btn-primary" disabled={busy} onClick={ask}>{busy ? "…" : "Ask"}</button>
      </div>
    </div>
  );
}
