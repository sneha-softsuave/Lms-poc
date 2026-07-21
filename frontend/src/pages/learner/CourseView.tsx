import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "../../components/Layout";
import { api, CourseTree, Lesson, ViewerPayload } from "../../api/client";
import { useToast } from "../../components/Toast";
import { Progress, Spinner } from "../../components/ui";
import { ModelViewer } from "../../components/ModelViewer";
import { Chatbot } from "../../components/Chatbot";
import { QuizPanel } from "../../components/QuizPanel";

type Tab = "lesson" | "3d" | "quiz";

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

  // Load 3D payload when the active lesson has a model & the 3D tab is opened.
  useEffect(() => {
    setViewer(null);
    if (activeLesson?.model3d_id) {
      api.lessonViewer(activeLesson.id).then(setViewer).catch(() => setViewer(null));
    }
  }, [activeLesson]);

  // Time-on-task (FR-5.7.1): send a heartbeat every 30s while enrolled & studying.
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
      toast.push(r.progress_pct === 100 ? "Course complete! 🎉 Certificate issued — see Certificates" : "Lesson completed", "ok");
    } catch (e: any) { toast.push(e.message, "err"); }
  }

  function openLesson(l: Lesson, moduleId: number) {
    setActiveLesson(l); setActiveModule(moduleId); setTab("lesson");
  }

  if (loading || !course) return <Layout title="Course"><Spinner label="Loading course…" /></Layout>;

  return (
    <Layout title={course.title}>
      <div className="spread mb">
        <div>
          <div className="row"><h2 style={{ margin: 0 }}>{course.title}</h2></div>
          <p className="muted" style={{ margin: "4px 0 0" }}>{course.description}</p>
        </div>
        {!enrolled ? (
          <button className="btn btn-primary" onClick={enrol}>Enrol to start</button>
        ) : (
          <div style={{ width: 200 }}>
            <div className="spread small"><span className="muted">Progress</span><b>{progress}%</b></div>
            <Progress pct={progress} />
          </div>
        )}
      </div>

      <div className="grid" style={{ gridTemplateColumns: "260px 1fr 340px", alignItems: "start" }}>
        {/* Lesson list */}
        <div className="card">
          <div className="card-head"><b>Course content</b></div>
          <div style={{ padding: "8px 0" }}>
            {course.modules.map((m) => (
              <div key={m.id}>
                <div className="nav-label" style={{ color: "var(--slate-500)", padding: "10px 16px 4px" }}>{m.title}</div>
                {m.lessons.map((l) => (
                  <div key={l.id} onClick={() => openLesson(l, m.id)}
                    className="spread" style={{
                      padding: "9px 16px", cursor: "pointer", fontSize: 14,
                      background: activeLesson?.id === l.id ? "var(--slate-100)" : undefined,
                      borderLeft: activeLesson?.id === l.id ? "3px solid var(--navy-700)" : "3px solid transparent",
                    }}>
                    <span>{l.title}</span>
                    {completed.has(l.id) && <span style={{ color: "var(--green)" }}>✓</span>}
                    {l.model3d_id && <span title="Has 3D model">🧊</span>}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Main panel */}
        <div>
          <div className="card">
            <div className="card-head" style={{ gap: 8 }}>
              <div className="row">
                <button className={`btn btn-sm ${tab === "lesson" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("lesson")}>Lesson</button>
                <button className={`btn btn-sm ${tab === "3d" ? "btn-primary" : "btn-ghost"}`}
                  disabled={!activeLesson?.model3d_id} onClick={() => setTab("3d")}>
                  Interactive 3D {activeLesson?.model3d_id ? "🧊" : ""}
                </button>
                <button className={`btn btn-sm ${tab === "quiz" ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab("quiz")}>Module quiz</button>
              </div>
            </div>
            <div className="card-pad">
              {tab === "lesson" && activeLesson && (
                <div>
                  <div className="spread mb">
                    <h3 style={{ margin: 0 }}>{activeLesson.title}</h3>
                    {activeLesson.source_ref?.page && <span className="badge badge-gray">source p{activeLesson.source_ref.page}</span>}
                  </div>
                  <p style={{ lineHeight: 1.7 }}>{activeLesson.body}</p>
                  {enrolled && (
                    <button className="btn btn-success mt" disabled={completed.has(activeLesson.id)} onClick={() => complete(activeLesson)}>
                      {completed.has(activeLesson.id) ? "✓ Completed" : "Mark lesson complete"}
                    </button>
                  )}
                </div>
              )}
              {tab === "3d" && (
                viewer ? <ModelViewer viewer={viewer} courseId={courseId} />
                  : <Spinner label="Loading 3D model…" />
              )}
              {tab === "quiz" && activeModule && <QuizPanel moduleId={activeModule} />}
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
