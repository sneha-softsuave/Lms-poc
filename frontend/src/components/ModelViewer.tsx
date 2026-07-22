import { Component, ReactNode, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree, useFrame } from "@react-three/fiber";
import { OrbitControls, Html, useGLTF, Bounds } from "@react-three/drei";
import * as THREE from "three";
import { api, ViewerPayload, Hotspot, ChatResponse } from "../api/client";
import { Citations, SlideOver, Spinner } from "./ui";
import { IconTile } from "./icons";

type Preset = "front" | "side" | "top" | "iso";
const PRESET_POS: Record<Preset, [number, number, number]> = {
  front: [0, 0.4, 3.2], side: [3.2, 0.4, 0], top: [0, 3.4, 0.001], iso: [2.5, 1.8, 2.5],
};

// Draco is disabled deliberately: drei defaults its decoder to
// https://www.gstatic.com/draco/... which would break the local-only asset
// requirement (see app/main.py). Meshopt's decoder ships inside three-stdlib,
// so the .glb files are compressed with meshopt instead.
function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url, false);

  // Source models arrive at wildly different scales (a rifle is ~9 units, a
  // carrier ~305). Normalise each model into a 2-unit box centred on the origin so
  // camera presets, hotspot coordinates and marker sizes are model-independent.
  // scripts/derive_hotspots.py applies this same transform when seeding.
  const fit = useMemo(() => {
    const box = new THREE.Box3().setFromObject(scene);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const s = 2 / Math.max(size.x, size.y, size.z);
    return { scale: s, position: center.multiplyScalar(-s).toArray() as [number, number, number] };
  }, [scene]);

  return (
    <group scale={fit.scale} position={fit.position}>
      <primitive object={scene} />
    </group>
  );
}

function PlaceholderModel() {
  return (
    <group>
      <mesh><boxGeometry args={[1.2, 0.8, 1.2]} /><meshStandardMaterial color="#94A3B8" metalness={0.3} roughness={0.5} /></mesh>
      <mesh position={[0, 0.6, 0]}><cylinderGeometry args={[0.25, 0.25, 0.5, 24]} /><meshStandardMaterial color="#2563EB" /></mesh>
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
  const targetPos = useMemo(() => new THREE.Vector3(), []);
  const targetLook = useMemo(() => new THREE.Vector3(), []);
  const moving = useRef(false);

  useEffect(() => {
    if (!controls) return;
    if (focus) {
      targetLook.set(...focus);
      targetPos.set(focus[0] + 1.4, focus[1] + 1.0, focus[2] + 1.4);
    } else {
      targetLook.set(0, 0, 0);
      targetPos.set(...PRESET_POS[preset]);
    }
    moving.current = true;
  }, [preset, focus, targetPos, targetLook, controls]);

  // Any drag / zoom / pan cancels the in-flight move so the learner keeps
  // free control of the camera instead of being pulled back to the preset.
  useEffect(() => {
    if (!controls) return;
    const release = () => { moving.current = false; };
    controls.addEventListener("start", release);
    return () => controls.removeEventListener("start", release);
  }, [controls]);

  useFrame(() => {
    if (!controls || !moving.current) return;
    camera.position.lerp(targetPos, 0.12);
    controls.target.lerp(targetLook, 0.12);
    controls.update();
    if (camera.position.distanceTo(targetPos) < 0.01 && controls.target.distanceTo(targetLook) < 0.01) {
      moving.current = false;
    }
  });

  return null;
}

function HotspotMarker({ h, active, onClick }: { h: Hotspot; active: boolean; onClick: () => void }) {
  const ref = useRef<THREE.Mesh>(null);
  const [hover, setHover] = useState(false);
  const target = useMemo(() => new THREE.Vector3(), []);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const s = active ? 1.6 : hover ? 1.3 : 1;
    ref.current.scale.lerp(target.setScalar(s), 0.12);
    // local offset only — the parent group already sits at h.position
    ref.current.position.y = Math.sin(clock.getElapsedTime() * 2 + h.position[0]) * 0.02;
  });

  return (
    <group position={h.position as [number, number, number]}>
      <mesh
        ref={ref}
        onClick={onClick}
        onPointerOver={() => setHover(true)}
        onPointerOut={() => setHover(false)}
      >
        <sphereGeometry args={[0.04, 16, 16]} />
        <meshStandardMaterial color={active ? "#2563EB" : "#3B82F6"} emissive={active ? "#2563EB" : "#000000"} emissiveIntensity={active ? 0.4 : 0} transparent opacity={0.85} />
      </mesh>
      {/* No distanceFactor: pins keep a constant screen size instead of
          ballooning over the model as the camera moves closer. */}
      <Html zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
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
  // Idle spin is a hint only: once the learner touches the model it stays off
  // for the rest of the session so manual inspection is never interrupted.
  const [autoRotate, setAutoRotate] = useState(true);
  const tookControl = useRef(false);
  function stopAutoRotate() { tookControl.current = true; setAutoRotate(false); }
  const glbUrl = viewer.glb_uri.replace(/^local:\/\//, "/media/").replace(/^s3:\/\/[^/]+\//, "/media/");
  const has3D = webglAvailable();

  // Bumped on every select/close so a response that lands after the learner
  // closed the panel (or picked another component) is discarded instead of
  // popping the panel back open.
  const reqId = useRef(0);

  async function selectComponent(h: Hotspot) {
    const id = ++reqId.current;
    setActive(h); setBusy(h.component); setExp(null); stopAutoRotate();
    try {
      const res = await api.explainComponent(courseId, viewer.lesson_id, h.component);
      if (reqId.current === id) setExp(res);
    } catch {
      if (reqId.current === id) setExp({ answer: null, grounded: false, citations: [], related_lessons: [], thread_id: 0 });
    } finally {
      if (reqId.current === id) setBusy(null);
    }
  }

  // The panel is open whenever `busy` or `exp` is set, so closing must clear
  // all of them — clearing `active` alone left it stuck open.
  function closePanel() {
    reqId.current++;
    setActive(null); setExp(null); setBusy(null);
  }

  if (!has3D) {
    return (
      <div>
        <Diagram2D viewer={viewer} onPick={(name) => selectComponent(viewer.hotspots.find((h) => h.component === name)!)} />
        <ExplainPanel exp={exp} busy={busy} title={active?.component} onClose={closePanel} />
      </div>
    );
  }

  return (
    <div>
      <div className="viewer-panel">
        <PresetToolbar preset={preset} active={!!active} onChange={(p) => { setPreset(p); closePanel(); if (!tookControl.current) setAutoRotate(true); }} />
        <Canvas camera={{ position: PRESET_POS.iso, fov: 45 }}>
          <ambientLight intensity={0.85} />
          <directionalLight position={[5, 8, 5]} intensity={1.0} castShadow />
          <directionalLight position={[-4, 3, -4]} intensity={0.4} color="#BFDBFE" />
          <Suspense fallback={<ModelLoader />}>
            <Bounds fit clip observe margin={1.2}>
              <ModelBoundary><Model url={glbUrl} /></ModelBoundary>
            </Bounds>
            {viewer.hotspots.map((h) => (
              <HotspotMarker key={h.hotspot_key} h={h} active={active?.hotspot_key === h.hotspot_key}
                onClick={() => selectComponent(h)} />
            ))}
          </Suspense>
          <OrbitControls makeDefault enablePan enableZoom enableRotate autoRotate={autoRotate} autoRotateSpeed={0.8} onStart={stopAutoRotate} />
          <CameraRig preset={preset} focus={active ? (active.position as [number, number, number]) : null} />
        </Canvas>
      </div>

      <div className="viewer-caption">
        <span className="muted">Drag to rotate · scroll to zoom · click a pin to inspect a component</span>
        <span className="badge badge-gray">{viewer.name}</span>
      </div>

      <ExplainPanel exp={exp} busy={busy} title={active?.component} onClose={closePanel} />
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
            <div className="card" style={{ background: "var(--warn-soft)", borderColor: "rgba(217,119,6,0.18)" }}>
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
          <rect x="80" y="80" width="240" height="90" rx={6} fill="var(--base-900)" stroke="var(--accent)" strokeWidth="2" />
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
          <button key={h.hotspot_key} className="btn btn-ghost btn-sm" onClick={() => onPick(h.component)}>
            <span className="row"><IconTile name="pin" size="sm" tone="slate" /> {h.component}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
