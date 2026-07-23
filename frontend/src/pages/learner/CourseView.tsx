import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Layout } from "../../components/Layout";
import { api, CourseTree, Lesson, ViewerPayload } from "../../api/client";
import { useToast } from "../../components/Toast";
import { Empty, ProgressRing, Spinner, StepIndicator } from "../../components/ui";
import { Button } from "../../components/Button";
import { LessonBody } from "../../components/Prose";
import { Icon, IconTile } from "../../components/icons";
import { ModelViewer } from "../../components/ModelViewer";
import { Chatbot } from "../../components/Chatbot";
import { QuizPanel } from "../../components/QuizPanel";

type Tab = "lesson" | "3d" | "quiz";

const STEPS = [
  { id: "lesson", label: "Lesson" },
  { id: "3d", label: "Interactive 3D" },
  { id: "quiz", label: "Module quiz" },
];

const stepTransition = {
  initial: { opacity: 0, x: 12 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -12 },
  transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] as const },
};

export default function CourseView() {
  const { id } = useParams();
  const courseId = Number(id);
  const nav = useNavigate();
  const toast = useToast();
  const [course, setCourse] = useState<CourseTree | null>(null);
  const [enrolled, setEnrolled] = useState(false);
  const [enrolling, setEnrolling] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [completed, setCompleted] = useState<Set<number>>(new Set());
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
  const [activeModule, setActiveModule] = useState<number | null>(null);
  const [openModules, setOpenModules] = useState<Set<number>>(new Set());
  const [tab, setTab] = useState<Tab>("lesson");
  const [viewer, setViewer] = useState<ViewerPayload | null>(null);
  const [viewerState, setViewerState] = useState<"none" | "loading" | "ready" | "error">("none");
  const [loading, setLoading] = useState(true);

  // Flat lesson order (with its owning module) drives prev/next and "lesson n of N".
  const flatLessons = useMemo(
    () => course?.modules.flatMap((m) => m.lessons.map((l) => ({ lesson: l, moduleId: m.id, moduleTitle: m.title }))) || [],
    [course]
  );
  const lessonIndex = useMemo(
    () => (activeLesson ? flatLessons.findIndex((x) => x.lesson.id === activeLesson.id) : -1),
    [activeLesson, flatLessons]
  );
  const activeModuleTitle = lessonIndex >= 0 ? flatLessons[lessonIndex].moduleTitle : "";

  async function load() {
    try {
      const c = await api.catalogCourse(courseId);
      setCourse(c);
      const first = c.modules[0]?.lessons[0] || null;
      setActiveLesson(first);
      setActiveModule(c.modules[0]?.id ?? null);
      // Start with every module open — the tree is the map of the course.
      setOpenModules(new Set(c.modules.map((m) => m.id)));
      const mine = await api.myLearning().catch(() => []);
      const e = mine.find((m: any) => m.course_id === courseId);
      if (e) { setEnrolled(true); setProgress(e.progress_pct); }
    } catch (e: any) { toast.push(e.message, "err"); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [courseId]);

  // "none" (no model attached) has to be distinct from "loading", otherwise the
  // spinner sits there forever on lessons that simply have no model.
  useEffect(() => {
    setViewer(null);
    if (!activeLesson?.model3d_id) { setViewerState("none"); return; }
    let cancelled = false;
    setViewerState("loading");
    api.lessonViewer(activeLesson.id)
      .then((v) => { if (!cancelled) { setViewer(v); setViewerState("ready"); } })
      .catch(() => { if (!cancelled) { setViewer(null); setViewerState("error"); } });
    // guards against a slow response for a previously-selected lesson landing late
    return () => { cancelled = true; };
  }, [activeLesson]);

  useEffect(() => {
    if (!enrolled) return;
    const t = setInterval(() => { api.heartbeat(courseId, 30).catch(() => {}); }, 30000);
    return () => clearInterval(t);
  }, [enrolled, courseId]);

  async function enrol() {
    setEnrolling(true);
    try { await api.enrol(courseId); setEnrolled(true); toast.push("Enrolled", "ok"); }
    catch (e: any) { toast.push(e.message, "err"); }
    finally { setEnrolling(false); }
  }

  async function complete(lesson: Lesson) {
    setCompleting(true);
    try {
      const r = await api.completeLesson(lesson.id);
      setProgress(r.progress_pct);
      setCompleted((s) => new Set(s).add(lesson.id));
      toast.push(r.progress_pct === 100 ? "Course complete! Certificate issued — see Certificates" : "Lesson completed", "ok");
    } catch (e: any) { toast.push(e.message, "err"); }
    finally { setCompleting(false); }
  }

  function openLesson(l: Lesson, moduleId: number) {
    setActiveLesson(l); setActiveModule(moduleId); setTab("lesson");
  }

  function goRelative(delta: number) {
    const next = flatLessons[lessonIndex + delta];
    if (next) openLesson(next.lesson, next.moduleId);
  }

  function toggleModule(mid: number) {
    setOpenModules((s) => { const n = new Set(s); n.has(mid) ? n.delete(mid) : n.add(mid); return n; });
  }

  if (loading || !course) return <Layout title="Course"><Spinner label="Loading course…" /></Layout>;

  const totalLessons = flatLessons.length;

  return (
    <Layout title={course.title}>
      <div className="spread mb" style={{ alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <div className="row"><h2 style={{ margin: 0 }}>{course.title}</h2></div>
          <p className="muted" style={{ margin: "4px 0 0", maxWidth: "72ch" }}>{course.description}</p>
        </div>
        {!enrolled ? (
          <Button variant="primary" loading={enrolling} loadingText="Enrolling…" onClick={enrol}>
            Enrol to start
          </Button>
        ) : (
          <div className="row" style={{ gap: 12 }}>
            <div style={{ textAlign: "right" }}>
              <div className="small muted" style={{ fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>Course progress</div>
              <div className="small" style={{ color: "var(--text-muted)" }}>
                {completed.size} of {totalLessons} lessons done
              </div>
            </div>
            <ProgressRing pct={progress} size={52} stroke={5} />
          </div>
        )}
      </div>

      <StepIndicator steps={STEPS} current={tab} onChange={(id) => setTab(id as Tab)} />

      <div className="grid mt course-layout" style={{ gridTemplateColumns: "280px 1fr 340px", alignItems: "start" }}>
        {/* ── Course content tree ── */}
        <div className="card" style={{ overflow: "hidden", position: "sticky", top: 20 }}>
          <div className="card-head" style={{ padding: "12px 16px" }}>
            <div className="row" style={{ gap: 8 }}>
              <IconTile name="layers" size="sm" tone="blue" />
              <b style={{ fontSize: "var(--text-sm)" }}>Course content</b>
            </div>
            <span className="mono" style={{ fontSize: "var(--text-2xs)", color: "var(--text-dim)" }}>
              {course.modules.length} MOD · {totalLessons} LESSONS
            </span>
          </div>
          <div className="toc">
            {course.modules.map((m, mi) => {
              const open = openModules.has(m.id);
              const doneCount = m.lessons.filter((l) => completed.has(l.id)).length;
              const allDone = doneCount === m.lessons.length && m.lessons.length > 0;
              return (
                <div key={m.id} className={`toc-module ${allDone ? "done" : ""}`}>
                  <button className="toc-module-head" type="button" onClick={() => toggleModule(m.id)} aria-expanded={open}>
                    <span className={`toc-caret ${open ? "open" : ""}`}>▶</span>
                    <span className="toc-module-idx">{allDone ? <Icon name="check" /> : String(mi + 1).padStart(2, "0")}</span>
                    <span className="toc-module-title" title={m.title}>{m.title}</span>
                    <span className="toc-module-meta">{doneCount}/{m.lessons.length}</span>
                  </button>
                  <div className="toc-module-bar">
                    <span style={{ width: `${m.lessons.length ? (doneCount / m.lessons.length) * 100 : 0}%` }} />
                  </div>
                  <AnimatePresence initial={false}>
                    {open && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] as const }}
                        style={{ overflow: "hidden" }}
                      >
                        {m.lessons.map((l, li) => {
                          const isActive = activeLesson?.id === l.id;
                          const isDone = completed.has(l.id);
                          return (
                            <button
                              key={l.id}
                              type="button"
                              onClick={() => openLesson(l, m.id)}
                              className={`toc-lesson ${isActive ? "active" : ""} ${isDone ? "done" : ""}`}
                              aria-current={isActive || undefined}
                            >
                              <span className="toc-lesson-mark">{isDone ? <Icon name="check" /> : li + 1}</span>
                              <span className="toc-lesson-title" title={l.title}>{l.title}</span>
                              {l.model3d_id && (
                                <span className="toc-lesson-flag" title="Includes a 3D model"><Icon name="cube" /></span>
                              )}
                            </button>
                          );
                        })}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Main panel ── */}
        <div>
          <div className="card" style={{ minHeight: 480 }}>
            <div className="card-head" style={{ gap: 8, justifyContent: "flex-start" }}>
              <span className="badge badge-gray" style={{ textTransform: "none" }}>Step {STEPS.findIndex((s) => s.id === tab) + 1} of {STEPS.length}</span>
              <span className="small muted" style={{ fontFamily: "var(--font-mono)" }}>
                {tab === "lesson" && activeLesson?.title}
                {tab === "3d" && (activeLesson?.model3d_id ? "Interactive 3D model" : "No model for this lesson")}
                {tab === "quiz" && "Knowledge check"}
              </span>
            </div>
            <div className="card-pad" style={{ position: "relative" }}>
              <AnimatePresence mode="wait">
                {tab === "lesson" && activeLesson && (
                  <motion.div key={activeLesson.id} {...stepTransition}>
                    {/* Heading block — eyebrow, title, rule — reads as structure,
                        the prose below reads as content. */}
                    <div className="lesson-eyebrow">
                      <span>Lesson {lessonIndex + 1} of {totalLessons}</span>
                      <span className="sep">·</span>
                      <span>{activeModuleTitle}</span>
                      {completed.has(activeLesson.id) && (
                        <span className="badge badge-green" style={{ marginLeft: 4 }}>
                          <Icon name="check" /> Completed
                        </span>
                      )}
                      {activeLesson.source_ref?.page && (
                        <span className="badge badge-gray" style={{ marginLeft: 4 }}>source p{activeLesson.source_ref.page}</span>
                      )}
                    </div>
                    <h3 className="lesson-title">{activeLesson.title}</h3>
                    <div className="lesson-rule" />

                    <LessonBody body={activeLesson.body} />

                    <div className="lesson-foot">
                      <div className="row" style={{ gap: 8 }}>
                        <Button size="sm" variant="ghost" disabled={lessonIndex <= 0} onClick={() => goRelative(-1)}>
                          ← Previous
                        </Button>
                        <Button size="sm" variant="ghost" disabled={lessonIndex >= totalLessons - 1} onClick={() => goRelative(1)}>
                          Next lesson →
                        </Button>
                      </div>
                      {enrolled && (
                        <Button
                          variant="success"
                          loading={completing}
                          loadingText="Saving progress…"
                          disabled={completed.has(activeLesson.id)}
                          icon={completed.has(activeLesson.id) ? <Icon name="check" /> : undefined}
                          onClick={() => complete(activeLesson)}
                        >
                          {completed.has(activeLesson.id) ? "Completed" : "Mark lesson complete"}
                        </Button>
                      )}
                    </div>
                  </motion.div>
                )}
                {tab === "3d" && (
                  <motion.div key="3d" {...stepTransition}>
                    {viewerState === "ready" && viewer ? (
                      <ModelViewer viewer={viewer} courseId={courseId} />
                    ) : viewerState === "loading" ? (
                      <Spinner label="Loading 3D model…" />
                    ) : viewerState === "error" ? (
                      <Empty
                        icon={<IconTile name="cube" tone="amber" />}
                        title="This 3D model could not be loaded"
                        hint="The model is attached to this lesson but its data could not be fetched. Try again, or continue with the lesson text."
                      />
                    ) : (
                      <Empty
                        icon={<IconTile name="cube" tone="slate" />}
                        title="No 3D model for this lesson"
                        hint="An administrator can attach one from the preloaded model library. The lesson text and knowledge check are unaffected."
                      />
                    )}
                  </motion.div>
                )}
                {tab === "quiz" && activeModule && (
                  <motion.div key="quiz" {...stepTransition}>
                    <QuizPanel moduleId={activeModule} />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {course.glossary?.length > 0 && tab === "lesson" && (
            <div className="card mt">
              <div className="card-head">
                <div className="row" style={{ gap: 8 }}>
                  <IconTile name="book" size="sm" tone="slate" />
                  <b>Glossary</b>
                </div>
                <span className="mono" style={{ fontSize: "var(--text-2xs)", color: "var(--text-dim)" }}>
                  {course.glossary.length} TERMS
                </span>
              </div>
              <div className="card-pad" style={{ display: "grid", gap: 10 }}>
                {course.glossary.map((g) => (
                  <div key={g.id} style={{ display: "grid", gridTemplateColumns: "160px 1fr", gap: 12, alignItems: "baseline" }}>
                    <b style={{ fontSize: "var(--text-sm)" }}>{g.term}</b>
                    <span className="muted small" style={{ lineHeight: 1.6 }}>{g.definition}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Chatbot */}
        <Chatbot courseId={courseId} lessonId={activeLesson?.id ?? null} />
      </div>

      <p className="muted small mt"><a onClick={() => nav("/catalog")} style={{ cursor: "pointer" }}>← Back to catalog</a></p>
    </Layout>
  );
}
