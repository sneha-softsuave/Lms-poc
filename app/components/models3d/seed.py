"""Seed the fixed library of preloaded 3D models (PRD 4.4.1).

GLB assets are served locally (glb_uri points at the local/MinIO object store,
NO external CDN) from <LOCAL_STORAGE_PATH>/models3d/<model_key>.glb.

Four entries are procedural placeholders from scripts/generate_3d_models.py; the
remaining four are real assets, meshopt-compressed (NOT Draco — its decoder is
CDN-hosted, which the air-gap requirement forbids). See scripts/derive_hotspots.py
for how the hotspot coordinates below are obtained.
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


# Hotspot positions are in NORMALISED model space: the viewer scales every GLB
# into a 2-unit box centred on the origin (see `Model` in ModelViewer.tsx), so a
# coordinate here means the same thing whether the source asset was authored at
# 9 units (a rifle) or 305 (a carrier). Regenerate with scripts/derive_hotspots.py
# if a .glb is ever re-exported. Each carries a source_ref (PRD 4.4.2); the
# component explainer also cites the course material at answer time via retrieval.
PRELOADED = [
    {
        "model_key": "utility-vehicle",
        "name": "Utility / recovery vehicle",
        "suitable_for": "Vehicle mechanics — assemblies, first-line checks",
        "hotspots": [
            _hs("hs-hull", "Hull", [-0.012, -0.134, 0.0], "EQUIP-VEH", "Hull & chassis", 4),
            _hs("hs-cabin", "Crew cabin", [-0.337, 0.355, 0.0], "EQUIP-VEH", "Crew compartment", 6),
            _hs("hs-wheel", "Road wheel", [0.628, -0.297, 0.535], "EQUIP-VEH", "Running gear", 9),
        ],
    },
    {
        "model_key": "engine-cutaway",
        "name": "Engine / powerpack (cutaway)",
        "suitable_for": "Powerpack — engine overview, cooling, lubrication",
        "hotspots": [
            _hs("hs-pump", "Coolant pump", [0.852, 0.081, 0.309], "EQUIP-ENG", "Cooling system", 41),
            _hs("hs-piston", "Piston", [0.208, 0.658, -0.04], "EQUIP-ENG", "Powerpack overview", 18),
            _hs("hs-pan", "Oil pan", [0.074, -0.698, -0.04], "EQUIP-ENG", "Lubrication", 33),
        ],
    },
    {
        "model_key": "generator-set",
        "name": "Portable generator set",
        "suitable_for": "Field power — generator operation & maintenance",
        "hotspots": [
            _hs("hs-alt", "Alternator", [0.576, -0.072, 0.0], "EQUIP-GEN", "Power generation", 12),
            _hs("hs-tank", "Fuel tank", [0.0, 0.436, 0.0], "EQUIP-GEN", "Fuel system", 15),
            _hs("hs-engine", "Engine", [-0.475, -0.072, 0.0], "EQUIP-GEN", "Prime mover", 8),
        ],
    },
    {
        "model_key": "field-radio",
        "name": "Field radio / transceiver",
        "suitable_for": "Field communications — controls & connectors",
        "hotspots": [
            _hs("hs-sq", "Squelch knob", [-0.146, -0.733, 0.122], "EQUIP-RAD", "Controls", 5),
            _hs("hs-ant", "Antenna", [0.219, 0.422, -0.024], "EQUIP-RAD", "Antenna & connectors", 7),
            _hs("hs-disp", "Display", [0.0, -0.271, 0.122], "EQUIP-RAD", "Operation", 3),
        ],
    },
    # ── Real assets below. Coordinates derived from the actual mesh geometry:
    # the AK's muzzle sits at Z -0.90 and its stock at +Z; the F-14's nose is at
    # +X (its vertical stabilisers are at X -0.93); the carrier's bow is at +Z
    # (the ski-jump ramp rises there).
    {
        "model_key": "rifle-trainer",
        "name": "Small-arms trainer (AK-pattern rifle)",
        "suitable_for": "Weapon handling — parts, assembly, safety",
        "hotspots": [
            _hs("hs-barrel", "Barrel", [0.0, 0.2, -0.9], "EQUIP-SA", "Barrel assembly", 3),
            _hs("hs-gas", "Gas tube / handguard", [0.0, 0.19, -0.5], "EQUIP-SA", "Gas system", 6),
            _hs("hs-mag", "Magazine", [0.0, -0.12, -0.08], "EQUIP-SA", "Feed & magazine", 4),
            _hs("hs-bolt", "Bolt carrier", [0.0, 0.21, 0.12], "EQUIP-SA", "Receiver & bolt", 2),
            _hs("hs-stock", "Stock", [0.0, 0.12, 0.45], "EQUIP-SA", "Stock & furniture", 7),
        ],
    },
    {
        "model_key": "crew-served-gun",
        "name": "Crew-served gun",
        "suitable_for": "Crew-served weapons — mounting, laying, stoppages",
        # NOTE: this asset's meshes are unnamed (Object_2..Object_7) and the
        # silhouette is ambiguous, so these anchor on real mesh centroids —
        # the pins land on geometry, but the labels want a visual check.
        "hotspots": [
            _hs("hs-body", "Receiver / body", [-0.008, -0.011, -0.034], "EQUIP-CSW", "Receiver group", 5),
            _hs("hs-sight", "Sighting unit", [0.123, 0.204, -0.011], "EQUIP-CSW", "Sights & laying", 9),
            _hs("hs-mount", "Mount / grip", [-0.088, -0.156, 0.349], "EQUIP-CSW", "Mounting", 12),
        ],
    },
    {
        "model_key": "fighter-aircraft",
        "name": "Carrier-borne fighter (F-14 pattern)",
        "suitable_for": "Airframe familiarisation — major assemblies",
        "hotspots": [
            _hs("hs-nose", "Nose / radome", [0.9, 0.0, 0.0], "EQUIP-AIR", "Forward fuselage", 4),
            _hs("hs-cockpit", "Cockpit", [0.45, 0.08, 0.0], "EQUIP-AIR", "Crew station", 7),
            _hs("hs-wing", "Variable-geometry wing", [-0.4, 0.0, 0.75], "EQUIP-AIR", "Wing & sweep", 11),
            _hs("hs-tail", "Vertical stabiliser", [-0.93, 0.22, 0.17], "EQUIP-AIR", "Empennage", 14),
            _hs("hs-engine", "Engine / exhaust", [-0.85, -0.05, 0.1], "EQUIP-AIR", "Propulsion", 18),
        ],
    },
    {
        "model_key": "aircraft-carrier",
        "name": "Aircraft carrier (Kuznetsov pattern)",
        "suitable_for": "Ship familiarisation — flight deck, island, armament",
        "hotspots": [
            _hs("hs-ramp", "Ski-jump ramp", [0.0, 0.03, 0.95], "EQUIP-SHP", "Flight deck", 6),
            _hs("hs-p700", "P-700 launcher deck", [-0.01, -0.047, 0.573], "EQUIP-SHP", "Missile armament", 21),
            _hs("hs-island", "Island / superstructure", [-0.19, 0.085, -0.28], "EQUIP-SHP", "Island & bridge", 9),
            _hs("hs-hangar", "Hangar deck", [-0.018, -0.07, -0.113], "EQUIP-SHP", "Hangar & lifts", 13),
            _hs("hs-ciws", "Kashtan CIWS", [0.151, -0.027, -0.872], "EQUIP-SHP", "Close-in defence", 25),
            _hs("hs-rbu", "RBU-12000 launcher", [0.149, -0.046, -0.913], "EQUIP-SHP", "ASW armament", 27),
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
        else:
            # refresh metadata too, so renaming a model or repointing its asset
            # takes effect on re-seed instead of only on a fresh database
            model.name = entry["name"]
            model.suitable_for = entry["suitable_for"]
            model.glb_uri = f"{ASSET_PREFIX}/{entry['model_key']}.glb"
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
