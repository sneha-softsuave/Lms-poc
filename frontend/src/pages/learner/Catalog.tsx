import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Layout } from "../../components/Layout";
import { api } from "../../api/client";
import { useToast } from "../../components/Toast";
import { Empty, Spinner, SkeletonCard, Progress } from "../../components/ui";
import { Button } from "../../components/Button";
import { IconTile } from "../../components/icons";

export default function Catalog() {
  const nav = useNavigate();
  const toast = useToast();
  const [groups, setGroups] = useState<any[]>([]);
  const [enrolled, setEnrolled] = useState<Set<number>>(new Set());
  const [enrolling, setEnrolling] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [subject, setSubject] = useState<number | null>(null);  // null = all subjects

  async function load() {
    const [cat, mine] = await Promise.all([api.catalog(), api.myLearning().catch(() => [])]);
    setGroups(cat);
    setEnrolled(new Set(mine.map((m: any) => m.course_id)));
    setLoading(false);
  }
  useEffect(() => { load(); }, []);

  async function enrol(courseId: number) {
    setEnrolling(courseId);
    try {
      await api.enrol(courseId);
      setEnrolled((s) => new Set(s).add(courseId));
      toast.push("Enrolled — find it in My learning", "ok");
    } catch (e: any) { toast.push(e.message, "err"); }
    finally { setEnrolling(null); }
  }

  if (loading) {
    return (
      <Layout title="Course catalog">
        <div className="mb-lg">
          <div className="skeleton mb" style={{ width: 220, height: 24 }} />
          <div className="grid grid-4">
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
        </div>
      </Layout>
    );
  }

  // Flattened deliberately: courses are grouped one-per-subject on the API, so
  // rendering a grid per subject gave a single card per row — a vertical list.
  // One grid over every course fills all four columns before wrapping; the
  // subject survives as the badge on each card and as the filter chips.
  const all = groups.flatMap((g: any) =>
    g.courses.map((c: any) => ({ ...c, subject_id: g.subject_id, subject_title: g.subject_title })));
  const visible = subject === null ? all : all.filter((c) => c.subject_id === subject);

  return (
    <Layout title="Course catalog">
      {all.length === 0 ? (
        <div className="card"><Empty icon={<IconTile name="catalog" size="lg" tone="slate" />} title="No published courses yet"
          hint="An administrator needs to upload material, generate a course, and publish it." /></div>
      ) : (
        <>
          <div className="spread mb-lg wrap">
            <div className="row">
              <IconTile name="book" size="sm" tone="blue" />
              <h3 style={{ margin: 0 }}>All courses</h3>
              <span className="badge badge-gray mono">{visible.length} course(s)</span>
            </div>
            {groups.length > 1 && (
              <div className="row wrap">
                <button className={`chip${subject === null ? " chip-on" : ""}`}
                  onClick={() => setSubject(null)}>All subjects</button>
                {groups.map((g: any) => (
                  <button key={g.subject_id} className={`chip${subject === g.subject_id ? " chip-on" : ""}`}
                    onClick={() => setSubject(g.subject_id)}>{g.subject_title}</button>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-4">
            {visible.map((c: any, ci: number) => (
              <motion.div
                key={c.id}
                className="card card-hoverable"
                style={{ display: "flex", flexDirection: "column" }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: Math.min(ci, 7) * 0.05 }}
              >
                {/* column + margin-top:auto on the actions keeps every Enrol button on
                    the same baseline, whatever the title/description wrap to at 4-up */}
                <div className="card-pad" style={{ display: "flex", flexDirection: "column", flex: 1 }}>
                  <div className="spread mb">
                    <span className="badge badge-blue clamp-2">{c.subject_title}</span>
                    {enrolled.has(c.id) && <span className="badge badge-green">Enrolled</span>}
                  </div>
                  <h4 className="clamp-2" style={{ margin: "6px 0" }}>{c.title}</h4>
                  <p className="small muted clamp-3" style={{ minHeight: 54, margin: 0 }}>{c.description}</p>
                  <div className="row" style={{ marginTop: "auto", paddingTop: 14 }}>
                    {enrolled.has(c.id) ? (
                      <Button variant="success" size="sm" block onClick={() => nav(`/courses/${c.id}`)}>Continue →</Button>
                    ) : (
                      <>
                        <Button variant="primary" size="sm" loading={enrolling === c.id} loadingText="Enrolling…"
                          onClick={() => enrol(c.id)}>Enrol</Button>
                        <Button variant="ghost" size="sm" disabled={enrolling === c.id}
                          onClick={() => nav(`/courses/${c.id}`)}>Preview</Button>
                      </>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </>
      )}
    </Layout>
  );
}
