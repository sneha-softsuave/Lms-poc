import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Layout } from "../../components/Layout";
import { api, CourseTree, Lesson, ViewerPayload } from "../../api/client";
import { useToast } from "../../components/Toast";
import { ProgressRing, Spinner, StepIndicator } from "../../components/ui";
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
  const [progress, setProgress] = useState(0);
  const [completed, setCompleted] = useState<Set<number>>(new Set());
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
  const [activeModule, setActiveModule] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("lesson");
  const [viewer, setViewer] = useState<ViewerPayload | null>(null);
  const [loading, setLoading] = useState(true);

  const allLessons = useMemo(() => course?.modules.flatMap((m) => m.lessons) || [], [course]);
  const lessonIndex = useMemo(() => activeLesson ? allLessons.findIndex((l) => l.id === activeLesson.id) : -1, [activeLesson, allLessons]);

  async function load() {
    try {
      const c = await api.catalogCourse(courseId);
      setCourse(c);
      const first = c.modules[0]?.lessons[0] || null;
      setActiveLesson(first);
      setActiveModule(c.modules[0]?.id ?? null);
      const mine = await api.myLearning().catch(() => []);
      const e = mine.find((m: any) => m.course_id === courseId);
      if (e) { setEnrolled(true); setProgress(e.progress_pct); }
    } catch (e: any) { toast.push(e.message, "err"); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [courseId]);

  useEffect(() => {
    setViewer(null);
    if (activeLesson?.model3d_id) {
      api.lessonViewer(activeLesson.id).then(setViewer).catch(() => setViewer(null));
    }
  }, [activeLesson]);

  useEffect(() => {
    if (!enrolled) return;
    const t = setInterval(() => { api.heartbeat(courseId, 30).catch(() => {}); }, 30000);
    return () => clearInterval(t);
  }, [enrolled, courseId]);

  async function enrol() {
    try { await api.enrol(courseId); setEnrolled(true); toast.push("Enrolled", "ok"); }
    catch (e: any) { toast.push(e.message, "err"); }
  }

  async function complete(lesson: Lesson) {
    try {
      const r = await api.completeLesson(lesson.id);
      setProgress(r.progress_pct);
      setCompleted((s) => new Set(s).add(lesson.id));
      toast.push(r.progress_pct === 100 ? "Course complete! Certificate issued — see Certificates" : "Lesson completed", "ok");
    } catch (e: any) { toast.push(e.message, "err"); }
  }

  function openLesson(l: Lesson, moduleId: number) {
    setActiveLesson(l); setActiveModule(moduleId); setTab("lesson");
  }

  if (loading || !course) return <Layout title="Course"><Spinner label="Loading course…" /></Layout>;

  return (
    <Layout title={course.title}>
      <div className="spread mb" style={{ alignItems: "flex-start" }}>
        <div>
          <div className="row"><h2 style={{ margin: 0 }}>{course.title}</h2></div>
          <p className="muted" style={{ margin: "4px 0 0" }}>{course.description}</p>
        </div>
        {!enrolled ? (
          <button className="btn btn-primary" onClick={enrol}>Enrol to start</button>
        ) : (
          <div className="row" style={{ gap: 12 }}>
            <div style={{ textAlign: "right" }}>
              <div className="small muted" style={{ fontFamily: "var(--font-mono)", textTransform: "uppercase" }}>Course progress</div>
              <div className="small" style={{ color: "var(--text-muted)" }}>{progress}% complete</div>
            </div>
            <ProgressRing pct={progress} size={52} stroke={5} />
          </div>
        )}
      </div>

      <StepIndicator steps={STEPS} current={tab} onChange={(id) => setTab(id as Tab)} />

      <div className="grid mt" style={{ gridTemplateColumns: "260px 1fr 340px", alignItems: "start" }}>
        {/* Lesson list */}
        <div className="card" style={{ overflow: "hidden" }}>
          <div className="card-head"><b>Course content</b></div>
          <div style={{ padding: "8px 0" }}>
            {course.modules.map((m) => (
              <div key={m.id}>
                <div className="nav-label" style={{ color: "var(--text-dim)", padding: "10px 16px 4px" }}>{m.title}</div>
                {m.lessons.map((l) => {
                  const isActive = activeLesson?.id === l.id;
                  const isCompleted = completed.has(l.id);
                  const isCurrent = isActive && !isCompleted;
                  return (
                    <div key={l.id} onClick={() => openLesson(l, m.id)}
                      className="spread"
                      style={{
                        padding: "9px 14px 9px 16px", cursor: "pointer", fontSize: 14,
                        background: isActive ? "rgba(74, 139, 223, 0.10)" : undefined,
                        borderLeft: isActive ? "3px solid var(--accent)" : "3px solid transparent",
                        transition: "background 150ms ease-out",
                      }}>
                      <span className={isActive ? "accent-text" : "muted"} style={{ fontWeight: isActive ? 600 : 400 }}>{l.title}</span>
                      <span className="row" style={{ gap: 6 }}>
                        {isCompleted && <span style={{ color: "var(--ok)", fontSize: 14 }}><Icon name="check" /></span>}
                        {isCurrent && <span style={{ color: "var(--accent)", fontSize: 10 }}>●</span>}
                        {l.model3d_id && <span title="Has 3D model" style={{ color: "var(--text-dim)", fontSize: 12 }}><IconTile name="cube" size="sm" tone="slate" /></span>}
                      </span>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {/* Main panel */}
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
                  <motion.div key="lesson" {...stepTransition}>
                    <div className="spread mb">
                      <h3 style={{ margin: 0 }}>{activeLesson.title}</h3>
                      {activeLesson.source_ref?.page && <span className="badge badge-gray">source p{activeLesson.source_ref.page}</span>}
                    </div>
                    <p style={{ lineHeight: 1.75, color: "var(--text-main)" }}>{activeLesson.body}</p>
                    {enrolled && (
                      <button className="btn btn-success mt" disabled={completed.has(activeLesson.id)} onClick={() => complete(activeLesson)}>
                        {completed.has(activeLesson.id) ? <span className="row"><Icon name="check" /> Completed</span> : "Mark lesson complete"}
                      </button>
                    )}
                  </motion.div>
                )}
                {tab === "3d" && (
                  <motion.div key="3d" {...stepTransition}>
                    {viewer ? <ModelViewer viewer={viewer} courseId={courseId} />
                      : <Spinner label="Loading 3D model…" />}
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
              <div className="card-head"><b>Glossary</b></div>
              <div className="card-pad">
                {course.glossary.map((g) => (
                  <div key={g.id} className="mb"><b>{g.term}</b> <span className="muted small">— {g.definition}</span></div>
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
