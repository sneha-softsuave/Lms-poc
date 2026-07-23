import { Fragment, ReactNode } from "react";

/**
 * Lesson bodies come back from the generator as plain text — usually a short
 * paragraph, sometimes light markdown (headings, bullets, **bold**). This
 * renders either shape with a real typographic hierarchy so a heading never
 * reads like body copy.
 */

type Block =
  | { kind: "heading"; level: 2 | 3; text: string }
  | { kind: "para"; text: string; lead?: boolean }
  | { kind: "bullets"; items: string[]; ordered?: boolean };

const HEADING_RE = /^(#{1,4})\s+(.*)$/;
const BULLET_RE = /^\s*([-*•])\s+(.*)$/;
const ORDERED_RE = /^\s*(\d+)[.)]\s+(.*)$/;

/** A short line ending in a colon reads as a label, not a sentence. */
function isLabelHeading(line: string) {
  return line.length <= 80 && /:$/.test(line.trim()) && !/[.!?]/.test(line.slice(0, -1));
}

export function parseBlocks(body: string): Block[] {
  const blocks: Block[] = [];
  const chunks = body.replace(/\r\n/g, "\n").split(/\n{2,}/);
  let firstPara = true;

  for (const chunk of chunks) {
    const lines = chunk.split("\n").map((l) => l.trimEnd()).filter((l) => l.trim() !== "");
    if (!lines.length) continue;

    let buffer: string[] = [];
    const flush = () => {
      if (!buffer.length) return;
      blocks.push({ kind: "para", text: buffer.join(" "), lead: firstPara });
      firstPara = false;
      buffer = [];
    };

    let bullets: string[] = [];
    let ordered = false;
    const flushBullets = () => {
      if (!bullets.length) return;
      blocks.push({ kind: "bullets", items: bullets, ordered });
      bullets = [];
    };

    for (const line of lines) {
      const h = HEADING_RE.exec(line);
      const b = BULLET_RE.exec(line);
      const o = ORDERED_RE.exec(line);

      if (h) {
        flush(); flushBullets();
        blocks.push({ kind: "heading", level: h[1].length <= 2 ? 2 : 3, text: h[2].trim() });
      } else if (b || o) {
        flush();
        ordered = !!o;
        bullets.push((b ? b[2] : o![2]).trim());
      } else if (isLabelHeading(line)) {
        flush(); flushBullets();
        blocks.push({ kind: "heading", level: 3, text: line.trim().replace(/:$/, "") });
      } else {
        flushBullets();
        buffer.push(line.trim());
      }
    }
    flush();
    flushBullets();
  }

  return blocks;
}

/** Inline markdown: **bold** and `code`. */
function inline(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (/^\*\*[^*]+\*\*$/.test(p)) return <strong key={i}>{p.slice(2, -2)}</strong>;
    if (/^`[^`]+`$/.test(p)) return <code key={i} className="prose-code">{p.slice(1, -1)}</code>;
    return <Fragment key={i}>{p}</Fragment>;
  });
}

export function LessonBody({ body }: { body: string }) {
  if (!body?.trim()) {
    return <p className="prose-empty">This lesson has no written content yet.</p>;
  }
  const blocks = parseBlocks(body);

  return (
    <div className="prose">
      {blocks.map((b, i) => {
        if (b.kind === "heading") {
          return b.level === 2
            ? <h4 key={i} className="prose-h2">{inline(b.text)}</h4>
            : <h5 key={i} className="prose-h3">{inline(b.text)}</h5>;
        }
        if (b.kind === "bullets") {
          const items = b.items.map((it, j) => <li key={j}>{inline(it)}</li>);
          return b.ordered
            ? <ol key={i} className="prose-list">{items}</ol>
            : <ul key={i} className="prose-list">{items}</ul>;
        }
        return <p key={i} className={b.lead ? "prose-lead" : undefined}>{inline(b.text)}</p>;
      })}
    </div>
  );
}
