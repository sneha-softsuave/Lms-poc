"""Seed the fixed library of 5 preloaded 3D models (PRD 4.4.1).

GLB assets are served locally (glb_uri points at the local/MinIO object store,
NO external CDN). For the POC the URIs are placeholders under the asset prefix;
drop the real optimized .glb files there. One sample hotspot per model shows the
component-explainer wiring.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.models3d.db_models import Model3D, ModelHotspot

logger = logging.getLogger(__name__)

ASSET_PREFIX = "local://models3d"  # served locally; swap for s3://<bucket>/models3d in MinIO

def _hs(key, component, pos, doc, section, page):
    return {"hotspot_key": key, "component": component, "position": pos,
            "source_ref": {"doc": doc, "section": section, "page": page}}


# Hotspot positions are matched to the generated GLB geometry (scripts/generate_3d_models.py)
# and carry a source_ref (PRD 4.4.2). The component explainer also cites the course
# material at answer time via retrieval.
PRELOADED = [
    {
        "model_key": "utility-vehicle",
        "name": "Utility / recovery vehicle",
        "suitable_for": "Vehicle mechanics — assemblies, first-line checks",
        "hotspots": [
            _hs("hs-hull", "Hull", [0.0, 0.34, 0.0], "EQUIP-VEH", "Hull & chassis", 4),
            _hs("hs-cabin", "Crew cabin", [-0.28, 0.76, 0.0], "EQUIP-VEH", "Crew compartment", 6),
            _hs("hs-wheel", "Road wheel", [0.55, 0.2, 0.46], "EQUIP-VEH", "Running gear", 9),
        ],
    },
    {
        "model_key": "engine-cutaway",
        "name": "Engine / powerpack (cutaway)",
        "suitable_for": "Powerpack — engine overview, cooling, lubrication",
        "hotspots": [
            _hs("hs-pump", "Coolant pump", [0.58, 0.12, 0.26], "EQUIP-ENG", "Cooling system", 41),
            _hs("hs-piston", "Piston", [0.1, 0.55, 0.0], "EQUIP-ENG", "Powerpack overview", 18),
            _hs("hs-pan", "Oil pan", [0.0, -0.46, 0.0], "EQUIP-ENG", "Lubrication", 33),
        ],
    },
    {
        "model_key": "generator-set",
        "name": "Portable generator set",
        "suitable_for": "Field power — generator operation & maintenance",
        "hotspots": [
            _hs("hs-alt", "Alternator", [0.34, 0.02, 0.0], "EQUIP-GEN", "Power generation", 12),
            _hs("hs-tank", "Fuel tank", [0.0, 0.32, 0.0], "EQUIP-GEN", "Fuel system", 15),
            _hs("hs-engine", "Engine", [-0.28, 0.02, 0.0], "EQUIP-GEN", "Prime mover", 8),
        ],
    },
    {
        "model_key": "field-radio",
        "name": "Field radio / transceiver",
        "suitable_for": "Field communications — controls & connectors",
        "hotspots": [
            _hs("hs-sq", "Squelch knob", [-0.12, -0.2, 0.12], "EQUIP-RAD", "Controls", 5),
            _hs("hs-ant", "Antenna", [0.18, 0.75, 0.0], "EQUIP-RAD", "Antenna & connectors", 7),
            _hs("hs-disp", "Display", [0.0, 0.18, 0.12], "EQUIP-RAD", "Operation", 3),
        ],
    },
    {
        "model_key": "rifle-trainer",
        "name": "Small-arms trainer (generic rifle)",
        "suitable_for": "Weapon handling — parts, assembly, safety",
        "hotspots": [
            _hs("hs-barrel", "Barrel", [1.0, 0.05, 0.0], "EQUIP-SA", "Barrel assembly", 3),
            _hs("hs-mag", "Magazine", [0.02, -0.24, 0.0], "EQUIP-SA", "Feed & magazine", 4),
            _hs("hs-bolt", "Bolt carrier", [0.0, 0.05, 0.0], "EQUIP-SA", "Receiver & bolt", 2),
        ],
    },
]


async def seed_models(db: AsyncSession) -> int:
    """Idempotent: create missing models and refresh hotspots on existing ones
    (so re-running picks up new/updated hotspots without wiping the DB)."""
    from sqlalchemy.orm import selectinload

    result = await db.execute(select(Model3D).options(selectinload(Model3D.hotspots)))
    by_key = {m.model_key: m for m in result.scalars().all()}
    created = 0
    for entry in PRELOADED:
        model = by_key.get(entry["model_key"])
        if model is None:
            model = Model3D(model_key=entry["model_key"], name=entry["name"],
                            glb_uri=f"{ASSET_PREFIX}/{entry['model_key']}.glb",
                            suitable_for=entry["suitable_for"])
            db.add(model)
            created += 1
        # refresh hotspots to match the current definition
        model.hotspots.clear()
        for hs in entry["hotspots"]:
            model.hotspots.append(ModelHotspot(
                hotspot_key=hs["hotspot_key"], component=hs["component"],
                position=hs["position"], source_ref=hs.get("source_ref")))
    await db.commit()
    if created:
        logger.info("Seeded %d preloaded 3D models", created)
    return created
