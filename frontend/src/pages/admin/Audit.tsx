import { useEffect, useState } from "react";
import { Layout } from "../../components/Layout";
import { api } from "../../api/client";
import { Empty, Spinner } from "../../components/ui";
import { IconTile } from "../../components/icons";

const ACTION_TONE: Record<string, string> = {
  "course.publish": "badge-green", "enrolment.create": "badge-blue",
  "quiz.submit": "badge-amber", "chat.answer": "badge-gray",
};

function SkeletonAudit() {
  return (
    <table>
      <thead><tr><th>#</th><th>Action</th><th>Entity</th><th>Actor</th><th>Detail</th></tr></thead>
      <tbody>
        {Array.from({ length: 5 }).map((_, i) => (
          <tr key={i}>
            {Array.from({ length: 5 }).map((__, j) => (
              <td key={j}><div className="skeleton" style={{ width: j === 0 ? "40%" : "80%", height: 12, borderRadius: 4 }} /></td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function Audit() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.audit(100).then(setEvents).finally(() => setLoading(false)); }, []);

  return (
    <Layout title="Audit log">
      <div className="card">
        <div className="card-head">
          <div className="row">
            <IconTile name="audit" size="sm" tone="slate" />
            <h3 style={{ margin: 0 }}>Immutable activity log</h3>
          </div>
          <span className="muted small">chatbot · quizzes · enrolments · publishes · admin actions</span>
        </div>
        {loading ? <SkeletonAudit /> : events.length === 0 ? (
          <Empty icon={<IconTile name="audit" size="lg" tone="slate" />} title="No events yet" hint="Activity will appear here as the platform is used." />
        ) : (
          <table>
            <thead><tr><th>#</th><th>Action</th><th>Entity</th><th>Actor</th><th>Detail</th></tr></thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id}>
                  <td className="muted mono">{e.id}</td>
                  <td><span className={`badge ${ACTION_TONE[e.action] || "badge-gray"}`}>{e.action}</span></td>
                  <td className="muted">{e.entity}</td>
                  <td className="muted">{e.actor_id ?? "system"}</td>
                  <td className="small muted">{e.detail ? JSON.stringify(e.detail) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}
