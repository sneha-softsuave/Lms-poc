import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../../components/Layout";
import { api, Doc } from "../../api/client";
import { useToast } from "../../components/Toast";
import { StatusBadge, Empty, Spinner } from "../../components/ui";

export default function Materials() {
  const toast = useToast();
  const nav = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    try { setDocs(await api.listDocs()); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  async function onUpload(file: File) {
    setUploading(true);
    try {
      const doc = await api.uploadDoc(file);
      toast.push(`Extracted ${doc.char_count.toLocaleString()} chars from ${doc.filename}`, "ok");
      await load();
    } catch (e: any) {
      toast.push(e.message, "err");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function generate(doc: Doc) {
    setGenerating(doc.id);
    try {
      const course = await api.generateCourse(doc.id);
      toast.push(`Draft course generated: ${course.title}`, "ok");
      nav(`/admin/courses/${course.id}`);
    } catch (e: any) {
      toast.push(e.message.includes("api_key") || e.message.includes("401")
        ? "AI provider not configured — set your API key in .env" : e.message, "err");
    } finally {
      setGenerating(null);
    }
  }

  return (
    <Layout title="Materials & AI Course Generation">
      <div className="card mb">
        <div className="card-pad">
          <h3>Upload source material</h3>
          <p className="muted small">
            PDF, DOCX, PPTX or TXT (scanned PDFs are OCR'd). The platform extracts the text with
            page/section provenance, then AI turns it into a structured draft course.
          </p>
          <input ref={fileRef} type="file" accept=".pdf,.docx,.pptx,.txt" style={{ display: "none" }}
            onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])} />
          <button className="btn btn-primary mt" disabled={uploading} onClick={() => fileRef.current?.click()}>
            {uploading ? "Uploading & extracting…" : "＋ Upload material"}
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h3 style={{ margin: 0 }}>Uploaded documents</h3></div>
        {loading ? <Spinner label="Loading…" /> : docs.length === 0 ? (
          <Empty icon="📄" title="No materials yet" hint="Upload a document to begin." />
        ) : (
          <table>
            <thead><tr><th>Code</th><th>File</th><th>Extraction</th><th>Size</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td><b>{d.doc_code}</b></td>
                  <td>{d.filename}</td>
                  <td><span className="badge badge-gray">{d.method}</span></td>
                  <td className="muted">{d.char_count.toLocaleString()} chars</td>
                  <td><StatusBadge status={d.status} /></td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn btn-gold btn-sm" disabled={generating === d.id}
                      onClick={() => generate(d)}>
                      {generating === d.id ? "Generating…" : "✨ Generate course"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <p className="muted small mt">
        Generation calls the configured AI provider (Claude or OpenAI). It typically takes 20–40s and
        produces a draft course you then review and publish.
      </p>
    </Layout>
  );
}
