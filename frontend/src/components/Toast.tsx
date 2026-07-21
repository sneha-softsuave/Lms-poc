import { createContext, useContext, useState, ReactNode, useCallback } from "react";

type Kind = "ok" | "err" | "info";
interface ToastItem { id: number; msg: string; kind: Kind; }
interface ToastCtx { push: (msg: string, kind?: Kind) => void; }

const Ctx = createContext<ToastCtx>(null as any);
export const useToast = () => useContext(Ctx);

let counter = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((msg: string, kind: Kind = "info") => {
    const id = ++counter;
    setItems((x) => [...x, { id, msg, kind }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 4200);
  }, []);
  return (
    <Ctx.Provider value={{ push }}>
      {children}
      <div className="toast">
        {items.map((i) => (
          <div key={i.id} className={`toast-item ${i.kind === "ok" ? "ok" : i.kind === "err" ? "err" : ""}`}>
            {i.msg}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
