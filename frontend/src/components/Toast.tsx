import { createContext, useContext, useState, ReactNode, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";

type Kind = "ok" | "err" | "info";
interface ToastItem { id: number; msg: string; kind: Kind; }
interface ToastCtx { push: (msg: string, kind?: Kind) => void; }

const Ctx = createContext<ToastCtx>(null as any);
export const useToast = () => useContext(Ctx);

let counter = 0;

const GLYPH: Record<Kind, string> = { ok: "✓", err: "!", info: "i" };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setItems((x) => x.filter((i) => i.id !== id));
  }, []);

  const push = useCallback((msg: string, kind: Kind = "info") => {
    const id = ++counter;
    setItems((x) => [...x, { id, msg, kind }]);
    // Errors linger — they usually need reading and often acting on.
    setTimeout(() => dismiss(id), kind === "err" ? 7000 : 4200);
  }, [dismiss]);

  return (
    <Ctx.Provider value={{ push }}>
      {children}
      <div className="toast">
        <AnimatePresence initial={false}>
          {items.map((i) => (
            <motion.div
              key={i.id}
              layout
              className={`toast-item ${i.kind === "ok" ? "ok" : i.kind === "err" ? "err" : ""}`}
              initial={{ opacity: 0, x: 24, scale: 0.96 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 24, scale: 0.96 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] as const }}
              role={i.kind === "err" ? "alert" : "status"}
            >
              <span className={`toast-glyph ${i.kind}`}>{GLYPH[i.kind]}</span>
              <span className="toast-msg">{i.msg}</span>
              <button className="toast-close" onClick={() => dismiss(i.id)} aria-label="Dismiss">×</button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  );
}
