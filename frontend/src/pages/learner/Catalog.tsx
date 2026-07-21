import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../../components/Layout";
import { api } from "../../api/client";
import { useToast } from "../../components/Toast";
import { Empty, Spinner } from "../../components/ui";

export default function Catalog() {
  const nav = useNavigate();
  const toast = useToast();
  const [groups, setGroups] = useState<any[]>([]);
  const [enrolled, setEnrolled] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);

  async function load() {
    const [cat, mine] = await Promise.all([api.catalog(), api.myLearning().catch(() => [])]);
    setGroups(cat);
    setEnrolled(new Set(mine.map((m: any) => m.course_id)));
    setLoading(false);
  }
  useEffect(() => { load(); }, []);

  async function enrol(courseId: number) {
    try {
      await api.enrol(courseId);
      setEnrolled((s) => new Set(s).add(courseId));
      toast.push("Enrolled — find it in My learning", "ok");
    } catch (e: any) { toast.push(e.message, "err"); }
  }

  if (loading) return <Layout title="Course catalog"><Spinner label="Loading catalog…" /></Layout>;

  const total = groups.reduce((s, g) => s + g.courses.length, 0);

  return (
    <Layout title="Course catalog">
      {total === 0 ? (
        <div className="card"><Empty icon="🗂" title="No published courses yet"
          hint="An administrator needs to upload material, generate a course, and publish it." /></div>
      ) : groups.map((g) => (
        <div key={g.subject_id} className="mb-lg" style={{ marginBottom: 28 }}>
          <div className="spread mb">
            <h3 style={{ margin: 0 }}>{g.subject_title}</h3>
            <span className="muted small">{g.courses.length} course(s)</span>
          </div>
          <div className="grid grid-3">
            {g.courses.map((c: any) => (
              <div key={c.id} className="card">
                <div className="card-pad">
                  <span className="badge badge-blue mb">{g.subject_title}</span>
                  <h4 style={{ margin: "6px 0" }}>{c.title}</h4>
                  <p className="small muted" style={{ minHeight: 40 }}>{c.description}</p>
                  <div className="row mt">
                    {enrolled.has(c.id) ? (
                      <button className="btn btn-success btn-sm btn-block" onClick={() => nav(`/courses/${c.id}`)}>Continue →</button>
                    ) : (
                      <>
                        <button className="btn btn-primary btn-sm" onClick={() => enrol(c.id)}>Enrol</button>
                        <button className="btn btn-ghost btn-sm" onClick={() => nav(`/courses/${c.id}`)}>Preview</button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </Layout>
  );
}
