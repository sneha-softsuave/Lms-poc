import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Layout } from "../../components/Layout";
import { api, CourseTree, Question, Model3D } from "../../api/client";
import { useToast } from "../../components/Toast";
import { StatusBadge, DifficultyBadge, Citations, Spinner, Section } from "../../components/ui";
import { Icon, IconTile } from "../../components/icons";

export default function CourseReview() {
  const { id } = useParams();
  const courseId = Number(id);
  const nav = useNavigate();
  const toast = useToast();
  const [course, setCourse] = useState<CourseTree | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [models, setModels] = useState<Model3D[]>([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());

  async function load() {
    const [c, q, m] = await Promise.all([
      api.reviewCourse(courseId), api.courseQuestions(courseId), api.listModels(),
    ]);
    setCourse(c); setQuestions(q); setModels(m); setLoading(false);
  }
  useEffect(() => { load(); }, [courseId]);

  const pending = questions.filter((q) => q.review_status === "pending").length;

  async function setStatus(qid: number, action: "approve" | "reject") {
    try {
      await (action === "approve" ? api.approveQuestion(qid) : api.rejectQuestion(qid));
      setQuestions((qs) => qs.map((q) => q.id === qid ? { ...q, review_status: action === "approve" ? "approved" : "rejected" } : q));
    } catch (e: any) { toast.push(e.message, "err"); }
  }

  async function bulkApprove() {
    const ids = questions.filter((q) => q.review_status === "pending").map((q) => q.id);
    for (const qid of ids) await api.approveQuestion(qid);
    toast.push(`Approved ${ids.length} questions`, "ok");
    load();
  }

  async function attachModel(lessonId: number, key: string) {
    try {
      await api.associateModel(lessonId, key);
      toast.push(key ? "3D model attached" : "Model detached", "ok");
      setCourse((c) => c && ({ ...c, modules: c.modules.map((m) => ({ ...m, lessons: m.lessons.map((l) => l.id === lessonId ? { ...l, model3d_id: key } : l) })) }));
    } catch (e: any) { toast.push(e.message, "err"); }
  }

  async function publish() {
    setPublishing(true);
    try {
      await api.publishCourse(courseId);
      await api.syncCourse(courseId).catch(() => {});
      toast.push("Course published & indexed for the chatbot", "ok");
      nav("/admin/courses");
    } catch (e: any) { toast.push(e.message, "err"); }
    finally { setPublishing(false); }
  }

  async function unpublish() {
    setPublishing(true);
    try {
      await api.unpublishCourse(courseId);
      toast.push("Course unpublished (hidden from catalog)", "ok");
      setCourse((c) => c && ({ ...c, status: "unpublished" }));
    } catch (e: any) { toast.push(e.message, "err"); }
    finally { setPublishing(false); }
  }

  function toggleModule(mid: number) {
    setCollapsed((s) => { const n = new Set(s); n.has(mid) ? n.delete(mid) : n.add(mid); return n; });
  }

  if (loading || !course) return <Layout title="Course review"><Spinner label="Loading course…" /></Layout>;

  const isPublished = course.status === "published";

  return (
    <Layout title={isPublished ? "Manage course" : "Review & publish"}>
      <div className="card mb">
        <div className="card-pad spread" style={{ alignItems: "flex-start" }}>
          <div>
            <div className="row">
              <h2 style={{ margin: 0 }}>{course.title}</h2>
              <StatusBadge status={course.status} />
              <span className="muted small mono">v{course.version}</span>
            </div>
            <p className="muted" style={{ margin: "6px 0 0" }}>{course.description}</p>
            <div className="pill-row mt">
              {course.objectives?.map((o, i) => <span key={i} className="badge badge-blue"><span className="row"><Icon name="award" /> {o}</span></span>)}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            {isPublished ? (
              <>
                <button className="btn btn-ghost" disabled={publishing} onClick={unpublish}>
                  {publishing ? "…" : "Unpublish"}
                </button>
                <div className="muted small mt">Live in the catalog</div>
              </>
            ) : (
              <>
                <button className="btn btn-success" disabled={publishing || pending > 0} onClick={publish}>
                  {publishing ? "Publishing…" : <span className="row"><Icon name="check" /> Publish course</span>}
                </button>
                <div className="muted small mt">
                  {pending > 0 ? `${pending} question(s) still pending` : "All questions reviewed"}
                </div>
              </>
            )}
          </div>
        </div>
        {isPublished && (
          <div className="card-pad" style={{ borderTop: "1px solid var(--border)", background: "var(--ok-soft)" }}>
            <b style={{ color: "var(--ok)" }}>Editing a live course.</b>{" "}
            <span className="small">3D model changes below apply to learners immediately — no re-publish needed.</span>
          </div>
        )}
      </div>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        {/* Modules & lessons */}
        <div>
          <h3>Modules & lessons</h3>
          {course.modules.map((m) => {
            const isCollapsed = collapsed.has(m.id);
            return (
              <div key={m.id} className="card mb">
                <button
                  className="card-head tree-node"
                  onClick={() => toggleModule(m.id)}
                  type="button"
                  style={{ width: "100%", background: "transparent", border: "none", cursor: "pointer" }}
                >
                  <div className="row">
                    <span style={{ color: "var(--accent)", fontSize: 12, transition: "transform 200ms" }} className={isCollapsed ? "" : "expanded"}>▶</span>
                    <b>{m.title}</b>
                  </div>
                  <span className="muted small mono">{m.lessons.length} lessons</span>
                </button>
                <AnimatePresence initial={false}>
                  {!isCollapsed && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] as const }}
                      style={{ overflow: "hidden" }}
                    >
                      <div className="card-pad">
                        {m.lessons.map((l) => (
                          <div key={l.id} className="mb tree-leaf" style={{ paddingBottom: 12, borderBottom: "1px solid var(--border)" }}>
                            <div className="spread">
                              <b>{l.title}</b>
                              {l.source_ref?.page && <span className="badge badge-gray mono">p{l.source_ref.page}</span>}
                            </div>
                            <p className="small muted" style={{ margin: "4px 0 8px" }}>{l.body}</p>
                            <div className="row small">
                              <span className="label" style={{ margin: 0 }}>3D model</span>
                              <select className="select" style={{ width: "auto", padding: "5px 8px" }}
                                value={l.model3d_id || ""} onChange={(e) => attachModel(l.id, e.target.value)}>
                                <option value="">— none —</option>
                                {models.map((mo) => <option key={mo.model_key} value={mo.model_key}>{mo.name}</option>)}
                              </select>
                            </div>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}

          {course.glossary?.length > 0 && (
            <Section title="Glossary" action={<span className="muted small mono">{course.glossary.length} terms</span>}>
              {course.glossary.map((g) => (
                <div key={g.id} className="mb"><b>{g.term}</b> <span className="muted small">— {g.definition}</span></div>
              ))}
            </Section>
          )}
        </div>

        {/* Question bank */}
        <div>
          <div className="spread mb">
            <h3 style={{ margin: 0 }}>Quiz bank ({questions.length})</h3>
            {pending > 0 && <button className="btn btn-gold btn-sm" onClick={bulkApprove}>Approve all pending</button>}
          </div>
          {questions.map((q, i) => (
            <motion.div
              key={q.id}
              className="card mb"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: i * 0.03 }}
            >
              <div className="card-pad">
                <div className="spread mb">
                  <div className="row">
                    <span className="badge badge-gray mono">{q.qtype.toUpperCase()}</span>
                    <DifficultyBadge level={q.difficulty} />
                    <span className="badge badge-blue mono">Q{q.quality_score}</span>
                    {q.review_status === "pending" && <span className="badge badge-amber">AI-generated</span>}
                  </div>
                  <StatusBadge status={q.review_status} />
                </div>
                <b>{q.stem}</b>
                {q.options && (
                  <ul className="small" style={{ margin: "8px 0", paddingLeft: 18 }}>
                    {q.options.map((o, idx) => (
                      <li key={idx} style={{ color: o === q.correct_answer ? "var(--ok)" : undefined, fontWeight: o === q.correct_answer ? 700 : 400 }}>
                        {o} {o === q.correct_answer && <span style={{ color: "var(--ok)", marginLeft: 4, display: "inline-block", verticalAlign: "middle" }}><Icon name="check" /></span>}
                      </li>
                    ))}
                  </ul>
                )}
                <div className="small muted">Answer: <b className="mono">{q.correct_answer}</b> — {q.rationale}</div>
                <Citations items={q.source_ref ? [q.source_ref] : []} />
                {q.review_status === "pending" && (
                  <div className="row mt">
                    <button className="btn btn-success btn-sm" onClick={() => setStatus(q.id, "approve")}>Approve</button>
                    <button className="btn btn-danger btn-sm" onClick={() => setStatus(q.id, "reject")}>Reject</button>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </Layout>
  );
}
