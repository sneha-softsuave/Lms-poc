import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Layout } from "../../components/Layout";
import { api, Doc } from "../../api/client";
import { useToast } from "../../components/Toast";
import { StatusBadge, Empty, Spinner, Progress } from "../../components/ui";
import { Button } from "../../components/Button";
import { IconTile } from "../../components/icons";

// Generation is a 20–40s AI call with no server-side progress stream. Narrating
// the stages beats a frozen spinner: the user can see it is still working.
const GEN_STAGES = [
  "Reading the extracted text…",
  "Identifying subjects & learning objectives…",
  "Drafting modules and lessons…",
  "Writing and scoring quiz questions…",
  "Assembling the draft course…",
];

export default function Materials() {
  const toast = useToast();
  const nav = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState<number | null>(null);
  const [stage, setStage] = useState(0);
  const [drag, setDrag] = useState(false);

  useEffect(() => {
    if (generating === null) { setStage(0); return; }
    // Advance through the narration but stop on the last stage — never claim
    // it finished a step the backend may still be on.
    const t = setInterval(() => setStage((s) => Math.min(s + 1, GEN_STAGES.length - 1)), 7000);
    return () => clearInterval(t);
  }, [generating]);

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
    setStage(0);
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

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDrag(false);
    if (uploading) return;
    const file = e.dataTransfer.files?.[0];
    if (file) onUpload(file);
  }

  return (
    <Layout title="Materials & AI Course Generation">
      <div className="card mb">
        <div className="card-pad">
          <div className="row" style={{ marginBottom: 8 }}>
            <IconTile name="upload" size="md" tone="blue" />
          </div>
          <h3 style={{ marginBottom: 6 }}>Upload source material</h3>
          <p className="muted small">
            PDF, DOCX, PPTX or TXT (scanned PDFs are OCR'd). The platform extracts the text with
            page/section provenance, then AI turns it into a structured draft course.
          </p>

          <input ref={fileRef} type="file" accept=".pdf,.docx,.pptx,.txt" style={{ display: "none" }}
            onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])} />

          <motion.div
            className={`upload-zone ${drag ? "drag-active" : ""} ${uploading ? "uploading" : ""}`}
            onClick={() => { if (!uploading) fileRef.current?.click(); }}
            onDragOver={(e) => { e.preventDefault(); if (!uploading) setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={handleDrop}
            whileHover={uploading ? undefined : { scale: 1.005 }}
            whileTap={uploading ? undefined : { scale: 0.995 }}
          >
            <div className="upload-zone-icon">
              {uploading ? <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
                         : <IconTile name="upload" size="lg" tone="blue" />}
            </div>
            <div className="upload-zone-title">{uploading ? "Uploading & extracting text…" : drag ? "Drop file to upload" : "Click or drag a file here"}</div>
            <div className="upload-zone-hint">PDF, DOCX, PPTX, TXT · scanned PDFs are OCR'd</div>
            {uploading && (
              <motion.div className="upload-progress" initial={{ width: "0%" }} animate={{ width: "100%" }} transition={{ duration: 2.5, ease: [0.16, 1, 0.3, 1] as const }}>
                <Progress pct={100} />
              </motion.div>
            )}
          </motion.div>
        </div>
      </div>

      <AnimatePresence>
        {generating !== null && (
          <motion.div
            className="job-banner"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <span className="spinner" style={{ width: 22, height: 22 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="job-banner-title">
                Generating course from {docs.find((d) => d.id === generating)?.filename || "document"}
              </div>
              <AnimatePresence mode="wait">
                <motion.div
                  key={stage}
                  className="job-stage"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.18 }}
                >
                  {GEN_STAGES[stage]}
                </motion.div>
              </AnimatePresence>
            </div>
            <span className="badge badge-blue mono">STEP {stage + 1}/{GEN_STAGES.length}</span>
            <span className="muted small">typically 20–40s · you'll land on the draft</span>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="card">
        <div className="card-head"><h3 style={{ margin: 0 }}>Uploaded documents</h3></div>
        {loading ? <Spinner label="Loading…" /> : docs.length === 0 ? (
          <Empty icon={<IconTile name="document" size="lg" tone="slate" />} title="No materials yet" hint="Upload a document to begin." />
        ) : (
          <table>
            <thead><tr><th>Code</th><th>File</th><th>Extraction</th><th>Size</th><th>Status</th><th></th></tr></thead>
            <tbody>
              <AnimatePresence>
                {docs.map((d) => (
                  <motion.tr
                    key={d.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <td><b className="mono">{d.doc_code}</b></td>
                    <td>{d.filename}</td>
                    <td><span className="badge badge-gray mono">{d.method}</span></td>
                    <td className="muted mono">{d.char_count.toLocaleString()} chars</td>
                    <td><StatusBadge status={d.status} /></td>
                    <td style={{ textAlign: "right" }}>
                      <Button
                        variant="gold"
                        size="sm"
                        loading={generating === d.id}
                        loadingText="Generating…"
                        disabled={generating !== null}
                        onClick={() => generate(d)}
                      >
                        Generate course
                      </Button>
                    </td>
                  </motion.tr>
                ))}
              </AnimatePresence>
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
