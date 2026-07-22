import { Component, ReactNode, Suspense, useEffect, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Html, useGLTF, Bounds } from "@react-three/drei";
import * as THREE from "three";
import { api, ViewerPayload, Hotspot, ChatResponse } from "../api/client";
import { Citations, SlideOver, Spinner } from "./ui";

type Preset = "front" | "side" | "top" | "iso";
const PRESET_POS: Record<Preset, [number, number, number]> = {
  front: [0, 0.4, 3.2], side: [3.2, 0.4, 0], top: [0, 3.4, 0.001], iso: [2.5, 1.8, 2.5],
};

function Model({ url }: { url: string }) {
  const gltf = useGLTF(url);
  return <primitive object={gltf.scene} />;
}

function PlaceholderModel() {
  return (
    <group>
      <mesh><boxGeometry args={[1.2, 0.8, 1.2]} /><meshStandardMaterial color="#33506D" metalness={0.3} roughness={0.5} /></mesh>
      <mesh position={[0, 0.6, 0]}><cylinderGeometry args={[0.25, 0.25, 0.5, 24]} /><meshStandardMaterial color="#4A8BDF" /></mesh>
    </group>
  );
}

class ModelBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <PlaceholderModel /> : this.props.children; }
}

function CameraRig({ preset, focus }: { preset: Preset; focus: [number, number, number] | null }) {
  const { camera, controls } = useThree() as any;
  useEffect(() => {
    if (!controls) return;
    if (focus) {
      const [x, y, z] = focus;
      controls.target.set(x, y, z);
      camera.position.set(x + 1.4, y + 1.0, z + 1.4);
    } else {
      controls.target.set(0, 0, 0);
      camera.position.set(...PRESET_POS[preset]);
    }
    controls.update();
  }, [preset, focus, camera, controls]);
  return null;
}

function HotspotMarker({ h, active, onClick }: { h: Hotspot; active: boolean; onClick: () => void }) {
  const ref = useRef<THREE.Mesh>(null);
  return (
    <group position={h.position as [number, number, number]}>
      <mesh ref={ref} onClick={onClick} scale={active ? 1.6 : 1}>
        <sphereGeometry args={[0.04, 16, 16]} />
        <meshStandardMaterial color={active ? "#4A8BDF" : "#4A8BDF"} emissive={active ? "#4A8BDF" : "#000000"} emissiveIntensity={active ? 0.6 : 0} transparent opacity={0.85} />
      </mesh>
      <Html distanceFactor={9} style={{ pointerEvents: "none" }}>
        <button className={`hotspot-pin ${active ? "active" : ""}`} onClick={onClick} type="button" style={{ pointerEvents: "auto" }}>
          <span className="hotspot-pulse" />
          <span className="hotspot-dot" />
          <span className="hotspot-label">{h.component}</span>
        </button>
      </Html>
    </group>
  );
}

function PresetToolbar({ preset, active, onChange }: { preset: Preset; active: boolean; onChange: (p: Preset) => void }) {
  return (
    <div className="viewer-hud">
      {(["front", "side", "top", "iso"] as Preset[]).map((p) => (
        <button
          key={p}
          className={preset === p && !active ? "active" : ""}
          onClick={() => onChange(p)}
          type="button"
        >
          {p}
        </button>
      ))}
    </div>
  );
}

function ModelLoader() {
  return (
    <Html center>
      <div className="model-loader">
        <div className="model-loader-cube">
          <span /><span /><span /><span />
          <div className="model-loader-scan" />
        </div>
        <span>Building geometry…</span>
      </div>
    </Html>
  );
}

function webglAvailable(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl") || c.getContext("experimental-webgl")));
  } catch { return false; }
}

export function ModelViewer({ viewer, courseId }: { viewer: ViewerPayload; courseId: number }) {
  const [exp, setExp] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [preset, setPreset] = useState<Preset>("iso");
  const [active, setActive] = useState<Hotspot | null>(null);
  const glbUrl = viewer.glb_uri.replace(/^local:\/\//, "/media/").replace(/^s3:\/\/[^/]+\//, "/media/");
  const has3D = webglAvailable();

  async function selectComponent(h: Hotspot) {
    setActive(h); setBusy(h.component); setExp(null);
    try { setExp(await api.explainComponent(courseId, viewer.lesson_id, h.component)); }
    catch { setExp({ answer: null, grounded: false, citations: [], related_lessons: [], thread_id: 0 }); }
    finally { setBusy(null); }
  }

  if (!has3D) {
    return (
      <div>
        <Diagram2D viewer={viewer} onPick={(name) => selectComponent(viewer.hotspots.find((h) => h.component === name)!)} />
        <ExplainPanel exp={exp} busy={busy} title={active?.component} onClose={() => setActive(null)} />
      </div>
    );
  }

  return (
    <div>
      <div className="viewer-panel">
        <PresetToolbar preset={preset} active={!!active} onChange={(p) => { setPreset(p); setActive(null); }} />
        <Canvas camera={{ position: PRESET_POS.iso, fov: 45 }}>
          <ambientLight intensity={0.75} />
          <directionalLight position={[5, 5, 5]} intensity={1.1} />
          <Suspense fallback={<ModelLoader />}>
            <Bounds fit clip observe margin={1.2}>
              <ModelBoundary><Model url={glbUrl} /></ModelBoundary>
            </Bounds>
            {viewer.hotspots.map((h) => (
              <HotspotMarker key={h.hotspot_key} h={h} active={active?.hotspot_key === h.hotspot_key}
                onClick={() => selectComponent(h)} />
            ))}
          </Suspense>
          <OrbitControls makeDefault enablePan enableZoom enableRotate />
          <CameraRig preset={preset} focus={active ? (active.position as [number, number, number]) : null} />
        </Canvas>
      </div>

      <div className="viewer-caption">
        <span className="muted">🖱 Drag to rotate · scroll to zoom · click a pin to inspect a component</span>
        <span className="badge badge-gray">{viewer.name}</span>
      </div>

      <ExplainPanel exp={exp} busy={busy} title={active?.component} onClose={() => setActive(null)} />
    </div>
  );
}

function ExplainPanel({ exp, busy, title, onClose }: { exp: ChatResponse | null; busy: string | null; title?: string; onClose: () => void }) {
  const open = !!(busy || exp);
  return (
    <SlideOver open={open} onClose={onClose} title={busy ? `Explaining ${busy}…` : title ? `Component: ${title}` : "Component details"}>
      {busy && !exp && (
        <div className="row" style={{ paddingTop: 40, justifyContent: "center" }}>
          <Spinner label={`Analyzing ${busy}…`} />
        </div>
      )}
      {exp && (
        <div>
          {exp.grounded ? (
            <>
              <div className="badge badge-green mb">Grounded explanation</div>
              <p style={{ margin: "0 0 12px", lineHeight: 1.65 }}>{exp.answer}</p>
              <Citations items={exp.citations} />
            </>
          ) : (
            <div className="card" style={{ background: "var(--warn-soft)", borderColor: "rgba(212,160,23,0.25)" }}>
              <div className="card-pad">
                <div className="badge badge-amber mb">Not covered</div>
                <div className="small">This component is not addressed by the course material.</div>
                {exp.related_lessons.length > 0 && (
                  <div className="small muted mt">Related lessons: {exp.related_lessons.map((l) => l.title).join(", ")}</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </SlideOver>
  );
}

function Diagram2D({ viewer, onPick }: { viewer: ViewerPayload; onPick: (name: string) => void }) {
  return (
    <div>
      <div className="badge badge-amber mb">3D unavailable on this device — showing a schematic</div>
      <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border)", borderRadius: 12, padding: 20 }}>
        <svg viewBox="0 0 400 240" style={{ width: "100%", height: 220 }}>
          <rect x="80" y="80" width="240" height="90" rx={6} fill="var(--base-700)" stroke="var(--accent)" strokeWidth="2" />
          <text x="200" y="130" fill="var(--text-main)" fontSize="13" textAnchor="middle" fontFamily="var(--font-sans)">{viewer.name}</text>
          {viewer.hotspots.map((h, i) => {
            const x = 100 + (i * 220) / Math.max(1, viewer.hotspots.length);
            return (
              <g key={h.hotspot_key} style={{ cursor: "pointer" }} onClick={() => onPick(h.component)}>
                <circle cx={x} cy={60} r={7} fill="var(--accent)" />
                <line x1={x} y1={67} x2={x} y2={82} stroke="var(--accent)" strokeWidth="1.5" />
                <text x={x} y={48} fill="var(--text-muted)" fontSize="11" textAnchor="middle" fontFamily="var(--font-mono)">{h.component}</text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="pill-row mt">
        {viewer.hotspots.map((h) => (
          <button key={h.hotspot_key} className="btn btn-ghost btn-sm" onClick={() => onPick(h.component)}>📍 {h.component}</button>
        ))}
      </div>
    </div>
  );
}
