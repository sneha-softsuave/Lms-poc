"""Procedurally generate the 5 preloaded 3D models as GLB files.

Authored from primitives (no third-party assets) so licensing is unambiguous and
everything is served locally (air-gap). Low-poly but recognizable equipment,
matching the model_key values seeded in app/components/models3d/seed.py.

Writes to <LOCAL_STORAGE_PATH>/models3d/<key>.glb, which the backend serves at
/media/models3d/<key>.glb.

Run: .venv/Scripts/python.exe scripts/generate_3d_models.py
"""

import os
import sys

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix, translation_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings  # noqa: E402

OUT_DIR = os.path.join(os.path.abspath(settings.LOCAL_STORAGE_PATH), "models3d")

# ── palette (RGBA 0–255) ──────────────────────────────────────────────────────
OLIVE = [85, 95, 55, 255]
GUNMETAL = [60, 65, 72, 255]
BLACK = [32, 34, 38, 255]
STEEL = [120, 128, 140, 255]
COPPER = [184, 138, 62, 255]
RED = [168, 55, 45, 255]
TIRE = [24, 24, 28, 255]
BLUE = [40, 70, 120, 255]
DARK = [45, 48, 55, 255]
YELLOW = [200, 165, 60, 255]


def _rot(axis, deg):
    return rotation_matrix(np.radians(deg), axis)


def box(extents, pos, color, rot=None):
    T = translation_matrix(pos)
    if rot is not None:
        T = T @ rot
    m = trimesh.creation.box(extents=extents, transform=T)
    m.visual.face_colors = color
    return m


def cyl(radius, height, pos, color, axis="z", extra=None):
    # trimesh cylinders run along Z; rotate to align with X or Y.
    T = translation_matrix(pos)
    if axis == "x":
        T = T @ _rot([0, 1, 0], 90)
    elif axis == "y":
        T = T @ _rot([1, 0, 0], 90)
    if extra is not None:
        T = T @ extra
    m = trimesh.creation.cylinder(radius=radius, height=height, sections=24, transform=T)
    m.visual.face_colors = color
    return m


def save(parts, key):
    scene = trimesh.Scene()
    for i, p in enumerate(parts):
        scene.add_geometry(p, node_name=f"{key}_{i}")
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{key}.glb")
    scene.export(path)
    size = os.path.getsize(path)
    print(f"  {key}.glb  ({len(parts)} parts, {size // 1024} KB)")


# ── 1) Small-arms trainer (rifle) — long axis X ───────────────────────────────
def rifle():
    return [
        box([1.4, 0.14, 0.18], [0.0, 0.0, 0.0], GUNMETAL),          # receiver
        box([0.5, 0.12, 0.14], [0.55, 0.0, 0.0], BLACK),            # handguard
        cyl(0.028, 0.95, [1.05, 0.02, 0.0], STEEL, axis="x"),       # barrel
        box([0.14, 0.34, 0.12], [0.02, -0.24, 0.0], OLIVE, _rot([0, 0, 1], -8)),  # magazine
        box([0.5, 0.16, 0.12], [-0.82, -0.02, 0.0], OLIVE),         # stock
        box([0.1, 0.26, 0.11], [-0.34, -0.16, 0.0], BLACK, _rot([0, 0, 1], 12)),  # pistol grip
        box([0.22, 0.06, 0.06], [0.2, 0.12, 0.0], BLACK),          # sight rail
    ]


# ── 2) Engine / powerpack (cutaway) ───────────────────────────────────────────
def engine():
    parts = [
        box([0.95, 0.7, 0.72], [0.0, 0.0, 0.0], STEEL),             # block
        box([1.0, 0.18, 0.78], [0.0, -0.46, 0.0], DARK),            # oil pan
    ]
    for x in (-0.3, -0.1, 0.1, 0.3):                                # pistons
        parts.append(cyl(0.11, 0.34, [x, 0.5, 0.0], COPPER, axis="y"))
    parts += [
        cyl(0.14, 0.22, [0.58, 0.12, 0.26], RED, axis="x"),         # coolant pump
        cyl(0.05, 0.5, [-0.55, 0.1, 0.2], GUNMETAL, axis="x"),      # intake pipe
        box([0.2, 0.3, 0.06], [0.0, 0.05, 0.42], GUNMETAL),         # cutaway face plate
    ]
    return parts


# ── 3) Portable generator set ─────────────────────────────────────────────────
def generator():
    parts = [
        box([1.1, 0.1, 0.72], [0.0, -0.32, 0.0], DARK),             # skid base
        box([0.62, 0.4, 0.6], [-0.28, 0.02, 0.0], GUNMETAL),        # engine block
        cyl(0.24, 0.5, [0.34, 0.02, 0.0], STEEL, axis="x"),         # alternator
        box([0.9, 0.16, 0.6], [0.0, 0.32, 0.0], BLUE),              # fuel tank
        cyl(0.04, 0.28, [-0.5, 0.32, 0.22], GUNMETAL, axis="y"),    # exhaust
    ]
    # tubular frame uprights + top rail
    for x, z in [(-0.52, -0.34), (-0.52, 0.34), (0.52, -0.34), (0.52, 0.34)]:
        parts.append(cyl(0.025, 0.85, [x, 0.05, z], YELLOW, axis="y"))
    parts.append(box([1.1, 0.04, 0.04], [0.0, 0.48, -0.34], YELLOW))
    parts.append(box([1.1, 0.04, 0.04], [0.0, 0.48, 0.34], YELLOW))
    return parts


# ── 4) Field radio / transceiver — long axis Y ────────────────────────────────
def radio():
    return [
        box([0.5, 0.72, 0.22], [0.0, 0.0, 0.0], OLIVE),             # body
        box([0.34, 0.2, 0.04], [0.0, 0.18, 0.12], BLACK),          # display
        cyl(0.05, 0.06, [-0.12, -0.2, 0.12], GUNMETAL, axis="z"),   # squelch knob
        cyl(0.05, 0.06, [0.12, -0.2, 0.12], GUNMETAL, axis="z"),    # volume knob
        cyl(0.016, 0.95, [0.18, 0.75, 0.0], STEEL, axis="y"),       # antenna
        box([0.3, 0.05, 0.06], [0.0, 0.4, 0.0], BLACK),            # carry handle
        box([0.5, 0.08, 0.22], [0.0, -0.38, 0.0], BLACK),          # battery pack
    ]


# ── 5) Utility / recovery vehicle — length X, width Z ─────────────────────────
def vehicle():
    parts = [
        box([1.7, 0.42, 0.85], [0.0, 0.34, 0.0], OLIVE),            # hull / body
        box([0.72, 0.42, 0.8], [-0.28, 0.76, 0.0], OLIVE),         # cabin
        box([0.5, 0.28, 0.72], [0.62, 0.42, 0.0], GUNMETAL),       # cargo/winch deck
        box([0.68, 0.26, 0.7], [-0.28, 0.78, 0.0], BLACK),        # windscreen (inset)
    ]
    for x in (-0.55, 0.55):                                          # 4 wheels
        for z in (-0.46, 0.46):
            parts.append(cyl(0.26, 0.2, [x, 0.2, z], TIRE, axis="z"))
    return parts


MODELS = {
    "rifle-trainer": rifle,
    "engine-cutaway": engine,
    "generator-set": generator,
    "field-radio": radio,
    "utility-vehicle": vehicle,
}


def main():
    print(f"Generating GLB models into {OUT_DIR}")
    for key, fn in MODELS.items():
        save(fn(), key)
    # sanity: reload each to confirm it's a valid GLB
    for key in MODELS:
        loaded = trimesh.load(os.path.join(OUT_DIR, f"{key}.glb"))
        assert loaded.geometry, f"{key} produced no geometry"
    print("All 5 GLB models generated and verified.")


if __name__ == "__main__":
    main()
