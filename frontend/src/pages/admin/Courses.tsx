import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../../components/Layout";
import { api, Course } from "../../api/client";
import { StatusBadge, Empty, Spinner, SkeletonText } from "../../components/ui";
import { IconTile } from "../../components/icons";

function SkeletonRow({ cols = 4 }: { cols?: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i}><div className="skeleton" style={{ width: i === 0 ? "70%" : "80%", height: 12, borderRadius: 4 }} /></td>
      ))}
    </tr>
  );
}

function SkeletonTable() {
  return (
    <table>
      <thead><tr><th>Course</th><th>Objectives</th><th>Version</th><th>Status</th><th></th></tr></thead>
      <tbody>
        <SkeletonRow cols={5} />
        <SkeletonRow cols={5} />
        <SkeletonRow cols={5} />
      </tbody>
    </table>
  );
}

export default function Courses() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listAllCourses().then(setCourses).finally(() => setLoading(false));
  }, []);

  const drafts = courses.filter((c) => c.status === "draft");
  const live = courses.filter((c) => c.status !== "draft");

  function Table({ rows, cta }: { rows: Course[]; cta: string }) {
    return (
      <table>
        <thead><tr><th>Course</th><th>Objectives</th><th>Version</th><th>Status</th><th></th></tr></thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.id}>
              <td><b>{c.title}</b><div className="muted small">{c.description}</div></td>
              <td className="muted">{c.objectives?.length || 0} objectives</td>
              <td className="mono">v{c.version}</td>
              <td><StatusBadge status={c.status} /></td>
              <td style={{ textAlign: "right" }}>
                <Link to={`/admin/courses/${c.id}`} className="btn btn-primary btn-sm">{cta} →</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  if (loading) {
    return (
      <Layout title="Courses & Review">
        <div className="card mb">
          <div className="card-head"><h3 style={{ margin: 0 }}>Draft courses awaiting review</h3></div>
          <SkeletonTable />
        </div>
        <div className="card">
          <div className="card-head"><h3 style={{ margin: 0 }}>Published & live courses</h3></div>
          <SkeletonTable />
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Courses & Review">
      <div className="card mb">
        <div className="card-head">
          <div className="row">
            <IconTile name="course" size="sm" tone="amber" />
            <h3 style={{ margin: 0 }}>Draft courses awaiting review</h3>
          </div>
          <Link to="/admin/materials" className="btn btn-primary btn-sm">＋ Generate from material</Link>
        </div>
        {drafts.length === 0 ? (
          <Empty icon={<IconTile name="course" size="lg" tone="slate" />} title="No drafts" hint="Generate a course from an uploaded document." />
        ) : <Table rows={drafts} cta="Review" />}
      </div>

      <div className="card">
        <div className="card-head">
          <div className="row">
            <IconTile name="book" size="sm" tone="green" />
            <h3 style={{ margin: 0 }}>Published & live courses</h3>
          </div>
          <span className="muted small">edit lessons, add / change 3D models, unpublish</span>
        </div>
        {live.length === 0 ? (
          <Empty icon={<IconTile name="book" size="lg" tone="slate" />} title="No published courses yet" hint="Publish a draft to make it live." />
        ) : <Table rows={live} cta="Manage" />}
      </div>
      <p className="muted small mt">
        Published courses stay editable — open one to attach or change the 3D model on any lesson;
        changes apply to learners immediately.
      </p>
    </Layout>
  );
}
