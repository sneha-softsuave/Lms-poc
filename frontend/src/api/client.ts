// Central API client for the Defense AI LMS backend.
const TOKEN_KEY = "dlms_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function req(path: string, opts: RequestInit = {}): Promise<any> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(opts.headers as any) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : res.text();
}

async function upload(path: string, file: File): Promise<any> {
  const fd = new FormData();
  fd.append("file", file);
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(path, { method: "POST", body: fd, headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ── types ─────────────────────────────────────────────────────────────────────
export interface User { id: number; email: string; full_name: string; role: string; }
export interface Doc { id: number; doc_code: string; filename: string; method: string; char_count: number; status: string; }
export interface Course { id: number; subject_id: number; title: string; description: string; objectives: string[]; version: number; status: string; }
export interface Lesson { id: number; title: string; body: string; order_index: number; source_ref: any; model3d_id: string | null; }
export interface Module { id: number; title: string; order_index: number; lessons: Lesson[]; }
export interface GlossaryTerm { id: number; term: string; definition: string; source_ref: any; }
export interface CourseTree extends Course { modules: Module[]; glossary: GlossaryTerm[]; }
export interface Question { id: number; qtype: string; stem: string; options: string[] | null; correct_answer: string; rationale: string; difficulty: string; review_status: string; quality_score: number; source_ref: any; }
export interface Enrolment { course_id: number; course_title: string; subject_title: string; status: string; progress_pct: number; time_spent_seconds: number; resume_lesson_id: number | null; }
export interface Certificate { serial: string; course_id: number; course_title: string; subject_title: string; learner_name: string; score_pct: number; issued_at: string; }
export interface ChatResponse { answer: string | null; grounded: boolean; citations: any[]; related_lessons: { lesson_id: number; title: string }[]; thread_id: number; }
export interface Model3D { id: number; model_key: string; name: string; glb_uri: string; suitable_for: string; }
export interface Hotspot { hotspot_key: string; component: string; position: [number, number, number]; source_ref: any; }
export interface ViewerPayload { lesson_id: number; model_key: string; name: string; glb_uri: string; hotspots: Hotspot[]; }

export const api = {
  // auth
  async login(email: string, password: string) {
    const r = await req("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    setToken(r.access_token);
    return r;
  },
  register: (email: string, password: string, full_name: string) =>
    req("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password, full_name }) }),
  me: (): Promise<User> => req("/api/v1/auth/me"),
  logout: () => setToken(null),

  // admin: ingestion + generation + review
  uploadDoc: (file: File): Promise<Doc> => upload("/api/v1/ingestion/upload", file),
  listDocs: (): Promise<Doc[]> => req("/api/v1/ingestion"),
  generateCourse: (docId: number): Promise<CourseTree> =>
    req(`/api/v1/course-generation/documents/${docId}/generate`, { method: "POST" }),
  listDrafts: (): Promise<Course[]> => req("/api/v1/review/drafts"),
  listAllCourses: (): Promise<Course[]> => req("/api/v1/review/courses"),
  reviewCourse: (courseId: number): Promise<CourseTree> => req(`/api/v1/review/courses/${courseId}`),
  courseQuestions: (courseId: number): Promise<Question[]> => req(`/api/v1/review/courses/${courseId}/questions`),
  approveQuestion: (qid: number) => req(`/api/v1/review/questions/${qid}/approve`, { method: "POST" }),
  rejectQuestion: (qid: number) => req(`/api/v1/review/questions/${qid}/reject`, { method: "POST" }),
  editQuestion: (qid: number, patch: any) => req(`/api/v1/review/questions/${qid}`, { method: "PATCH", body: JSON.stringify(patch) }),
  editLesson: (lid: number, patch: any) => req(`/api/v1/review/lessons/${lid}`, { method: "PATCH", body: JSON.stringify(patch) }),
  publishCourse: (courseId: number) => req(`/api/v1/review/courses/${courseId}/publish`, { method: "POST" }),
  unpublishCourse: (courseId: number) => req(`/api/v1/review/courses/${courseId}/unpublish`, { method: "POST" }),
  syncCourse: (courseId: number) => req(`/api/v1/admin/chatbot/courses/${courseId}/sync`, { method: "POST" }),

  // 3D
  listModels: (): Promise<Model3D[]> => req("/api/v1/models3d"),
  associateModel: (lessonId: number, model_key: string) =>
    req(`/api/v1/models3d/lessons/${lessonId}/associate`, { method: "POST", body: JSON.stringify({ model_key }) }),
  lessonViewer: (lessonId: number): Promise<ViewerPayload> => req(`/api/v1/models3d/lessons/${lessonId}/viewer`),

  // analytics + audit
  cohortProgress: () => req("/api/v1/admin/analytics/cohort-progress"),
  subjectMastery: () => req("/api/v1/admin/analytics/subject-mastery"),
  weakestTopics: () => req("/api/v1/admin/analytics/weakest-topics"),
  audit: (limit = 50) => req(`/api/v1/admin/audit?limit=${limit}`),

  // learner
  catalog: () => req("/api/v1/catalog/subjects"),
  catalogCourse: (courseId: number): Promise<CourseTree> => req(`/api/v1/catalog/courses/${courseId}`),
  enrol: (courseId: number) => req(`/api/v1/enrolments/courses/${courseId}`, { method: "POST" }),
  myLearning: (): Promise<Enrolment[]> => req("/api/v1/enrolments/me"),
  getLesson: (lessonId: number) => req(`/api/v1/learning/lessons/${lessonId}`),
  completeLesson: (lessonId: number) => req(`/api/v1/learning/lessons/${lessonId}/complete`, { method: "POST" }),
  heartbeat: (courseId: number, seconds: number) =>
    req(`/api/v1/learning/courses/${courseId}/heartbeat`, { method: "POST", body: JSON.stringify({ seconds }) }),
  myCertificates: (): Promise<Certificate[]> => req("/api/v1/certificates/me"),
  async downloadResultsCsv() {
    const headers: Record<string, string> = {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch("/api/v1/admin/analytics/export.csv", { headers });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "learning_results.csv";
    a.click();
    URL.revokeObjectURL(url);
  },

  // chatbot
  chat: (course_id: number, lesson_id: number | null, question: string, thread_id?: number): Promise<ChatResponse> =>
    req("/api/v1/chat", { method: "POST", body: JSON.stringify({ course_id, lesson_id, question, thread_id }) }),
  explainComponent: (course_id: number, lesson_id: number | null, component: string): Promise<ChatResponse> =>
    req("/api/v1/chat/explain-component", { method: "POST", body: JSON.stringify({ course_id, lesson_id, component }) }),

  // quiz
  getQuiz: (moduleId: number) => req(`/api/v1/quiz/modules/${moduleId}`),
  submitQuiz: (moduleId: number, answers: Record<string, string>) =>
    req(`/api/v1/quiz/modules/${moduleId}/submit`, { method: "POST", body: JSON.stringify({ answers }) }),
};
