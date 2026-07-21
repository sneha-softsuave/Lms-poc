import { useEffect, useState } from "react";
import { Layout } from "../../components/Layout";
import { api } from "../../api/client";
import { Empty, Spinner } from "../../components/ui";

const ACTION_TONE: Record<string, string> = {
  "course.publish": "badge-green", "enrolment.create": "badge-blue",
  "quiz.submit": "badge-amber", "chat.answer": "badge-gray",
};

export default function Audit() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.audit(100).then(setEvents).finally(() => setLoading(false)); }, []);

  return (
    <Layout title="Audit log">
      <div className="card">
        <div className="card-head">
          <h3 style={{ margin: 0 }}>Immutable activity log</h3>
          <span className="muted small">chatbot · quizzes · enrolments · publishes · admin actions</span>
        </div>
        {loading ? <Spinner label="Loading…" /> : events.length === 0 ? (
          <Empty icon="🛡" title="No events yet" hint="Activity will appear here as the platform is used." />
        ) : (
          <table>
            <thead><tr><th>#</th><th>Action</th><th>Entity</th><th>Actor</th><th>Detail</th></tr></thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id}>
                  <td className="muted">{e.id}</td>
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
