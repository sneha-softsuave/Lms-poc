"""Inspect a .glb and report coordinates in the viewer's NORMALISED model space.

The viewer scales every model into a 2-unit box centred on the origin (`Model`
in frontend/src/components/ModelViewer.tsx), so hotspot coordinates in
app/components/models3d/seed.py are stored in that space rather than in the
asset's own units. This script applies the identical transform:

    center = (bbox.min + bbox.max) / 2
    scale  = 2 / max(bbox.max - bbox.min)
    p_norm = (p - center) * scale

Use it when a .glb is re-exported or a new model is added — a re-export at a
different scale or origin silently moves every hotspot otherwise.

    python scripts/derive_hotspots.py media/models3d/aircraft-carrier.glb
    python scripts/derive_hotspots.py <file.glb> --point 1.2 0.4 -8.0

Without --point it lists each mesh node's normalised centre and size, which is
the quickest way to anchor a hotspot onto real geometry: a pin placed at a mesh
centroid is guaranteed to sit on the model.
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import trimesh


def normalisation(scene: trimesh.Scene):
    """Return (center, scale) matching the viewer's normalisation."""
    lo, hi = scene.bounds
    center = (lo + hi) / 2.0
    scale = 2.0 / float((hi - lo).max())
    return center, scale


def mesh_nodes(scene: trimesh.Scene, center, scale):
    """Yield (node_name, normalised_centre, normalised_size, triangles)."""
    for name, geom in scene.geometry.items():
        nodes = [n for n in scene.graph.nodes_geometry if scene.graph[n][1] == name]
        for nd in nodes or [name]:
            if nd in scene.graph.nodes_geometry:
                verts = trimesh.transform_points(geom.vertices, scene.graph[nd][0])
            else:
                verts = geom.vertices
            v = (verts - center) * scale
            lo, hi = v.min(axis=0), v.max(axis=0)
            tris = len(geom.faces) if hasattr(geom, "faces") else 0
            yield nd, (lo + hi) / 2.0, hi - lo, tris


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("glb", help="path to the .glb file")
    ap.add_argument("--point", nargs=3, type=float, metavar=("X", "Y", "Z"),
                    help="convert one point from asset space to normalised space")
    ap.add_argument("--limit", type=int, default=30, help="max mesh nodes to list")
    args = ap.parse_args()

    if not os.path.exists(args.glb):
        print(f"error: no such file: {args.glb}", file=sys.stderr)
        return 1

    scene = trimesh.load(args.glb)
    if not isinstance(scene, trimesh.Scene):
        scene = trimesh.Scene(scene)

    center, scale = normalisation(scene)
    lo, hi = scene.bounds
    print(f"{os.path.basename(args.glb)}")
    print(f"  asset extent : {(hi - lo).round(3).tolist()}")
    print(f"  center       : {center.round(4).tolist()}")
    print(f"  scale        : {scale:.6f}   (asset units -> normalised)")

    if args.point:
        p = (np.asarray(args.point, dtype=float) - center) * scale
        print(f"  point {args.point} -> [{p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f}]")
        return 0

    rows = sorted(mesh_nodes(scene, center, scale), key=lambda r: -r[3])
    print(f"  {len(rows)} mesh nodes (largest first):")
    print(f"    {'node':<38} {'centre':<28} {'size':<26} tris")
    for nd, c, s, tris in rows[:args.limit]:
        print(f"    {str(nd)[:37]:<38} {str(c.round(3).tolist()):<28} "
              f"{str(s.round(3).tolist()):<26} {tris:,}")
    if len(rows) > args.limit:
        print(f"    ... +{len(rows) - args.limit} more (use --limit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
