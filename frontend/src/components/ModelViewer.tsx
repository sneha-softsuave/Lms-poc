import { Component, ReactNode, Suspense, useEffect, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Html, useGLTF, Bounds } from "@react-three/drei";
import * as THREE from "three";
import { api, ViewerPayload, Hotspot, ChatResponse } from "../api/client";
import { Citations } from "./ui";

function Model({ url }: { url: string }) {
  const gltf = useGLTF(url);
  return <primitive object={gltf.scene} />;
}

// Fallback mesh if a GLB fails to load — keeps the scene usable.
function PlaceholderModel() {
  return (
    <group>
      <mesh><boxGeometry args={[1.2, 0.8, 1.2]} /><meshStandardMaterial color="#24466f" metalness={0.3} roughness={0.5} /></mesh>
      <mesh position={[0, 0.6, 0]}><cylinderGeometry args={[0.25, 0.25, 0.5, 24]} /><meshStandardMaterial color="#c9a227" /></mesh>
    </group>
  );
}

class ModelBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <PlaceholderModel /> : this.props.children; }
}

type Preset = "front" | "side" | "top" | "iso";
const PRESET_POS: Record<Preset, [number, number, number]> = {
  front: [0, 0.4, 3.2], side: [3.2, 0.4, 0], top: [0, 3.4, 0.001], iso: [2.5, 1.8, 2.5],
};

// Drives the camera to a preset angle or focuses a selected hotspot.
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

// In-scene clickable hotspot pin at its 3D position (PRD 4.4.2).
function HotspotMarker({ h, active, onClick }: { h: Hotspot; active: boolean; onClick: () => void }) {
  const ref = useRef<THREE.Mesh>(null);
  return (
    <group position={h.position as [number, number, number]}>
      <mesh ref={ref} onClick={onClick} scale={active ? 1.6 : 1}>
        <sphereGeometry args={[0.05, 16, 16]} />
        <meshStandardMaterial color={active ? "#c9a227" : "#ff5252"} emissive={active ? "#c9a227" : "#000000"} emissiveIntensity={active ? 0.6 : 0} />
      </mesh>
      <Html distanceFactor={9} style={{ pointerEvents: "none" }}>
        <div style={{
          background: active ? "#c9a227" : "#0b1a2f", color: active ? "#0b1a2f" : "#fff",
          padding: "2px 7px", borderRadius: 5, fontSize: 11, fontWeight: 600, whiteSpace: "nowrap",
          transform: "translate(10px,-10px)", boxShadow: "0 1px 4px rgba(0,0,0,.4)",
        }}>{h.component}</div>
      </Html>
    </group>
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

  // FR-5.4.5: graceful degradation to a 2D diagram where 3D is unsupported.
  if (!has3D) {
    return (
      <div>
        <Diagram2D viewer={viewer} onPick={(name) => selectComponent(viewer.hotspots.find((h) => h.component === name)!)} />
        <ExplainCard exp={exp} busy={busy} />
      </div>
    );
  }

  return (
    <div>
      <div style={{ height: 360, background: "#0b1a2f", borderRadius: 12, overflow: "hidden", position: "relative" }}>
        <div style={{ position: "absolute", top: 10, right: 10, zIndex: 2, display: "flex", gap: 4 }}>
          {(["front", "side", "top", "iso"] as Preset[]).map((p) => (
            <button key={p} onClick={() => { setPreset(p); setActive(null); }}
              className="btn btn-sm" style={{
                padding: "3px 9px", fontSize: 12, textTransform: "capitalize",
                background: preset === p && !active ? "#c9a227" : "#ffffff22", color: "#fff", border: "none",
              }}>{p}</button>
          ))}
        </div>
        <Canvas camera={{ position: PRESET_POS.iso, fov: 45 }}>
          <ambientLight intensity={0.75} />
          <directionalLight position={[5, 5, 5]} intensity={1.1} />
          <Suspense fallback={<Html center><span style={{ color: "#fff" }}>Loading 3D…</span></Html>}>
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

      <div className="spread mt">
        <div className="muted small">🖱 Drag to rotate · scroll to zoom · click a red pin to inspect a component</div>
        <span className="badge badge-gray">{viewer.name}</span>
      </div>

      <div className="pill-row mt">
        {viewer.hotspots.map((h) => (
          <button key={h.hotspot_key}
            className={`btn btn-sm ${active?.hotspot_key === h.hotspot_key ? "btn-gold" : "btn-ghost"}`}
            disabled={!!busy} onClick={() => selectComponent(h)}>
            📍 {h.component}{busy === h.component ? " …" : ""}
          </button>
        ))}
      </div>

      <ExplainCard exp={exp} busy={busy} />
    </div>
  );
}

function ExplainCard({ exp, busy }: { exp: ChatResponse | null; busy: string | null }) {
  if (busy && !exp) return <div className="card mt"><div className="card-pad muted small">Explaining {busy}…</div></div>;
  if (!exp) return null;
  return (
    <div className="card mt">
      <div className="card-pad">
        {exp.grounded ? (
          <>
            <div className="badge badge-green mb">Grounded explanation</div>
            <p style={{ margin: "0 0 6px" }}>{exp.answer}</p>
            <Citations items={exp.citations} />
          </>
        ) : <div className="muted">Not covered by the course material.</div>}
      </div>
    </div>
  );
}

// 2D schematic fallback: labelled hotspots on a simple diagram (FR-5.4.5).
function Diagram2D({ viewer, onPick }: { viewer: ViewerPayload; onPick: (name: string) => void }) {
  return (
    <div>
      <div className="badge badge-amber mb">3D unavailable on this device — showing a schematic</div>
      <div style={{ background: "#0b1a2f", borderRadius: 12, padding: 20 }}>
        <svg viewBox="0 0 400 240" style={{ width: "100%", height: 220 }}>
          <rect x="80" y="80" width="240" height="90" rx="10" fill="#24466f" stroke="#c9a227" strokeWidth="2" />
          <text x="200" y="130" fill="#fff" fontSize="13" textAnchor="middle">{viewer.name}</text>
          {viewer.hotspots.map((h, i) => {
            const x = 100 + (i * 220) / Math.max(1, viewer.hotspots.length);
            return (
              <g key={h.hotspot_key} style={{ cursor: "pointer" }} onClick={() => onPick(h.component)}>
                <circle cx={x} cy={60} r={7} fill="#ff5252" />
                <line x1={x} y1={67} x2={x} y2={82} stroke="#ff5252" strokeWidth="1.5" />
                <text x={x} y={48} fill="#cdd8e6" fontSize="11" textAnchor="middle">{h.component}</text>
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
