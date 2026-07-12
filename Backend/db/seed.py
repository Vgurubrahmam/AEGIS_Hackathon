"""
AEGIS — Database Seed Script
Seeds resources, and historical incidents for RAG.
Run automatically on first startup via main.py lifespan.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.models import Resource, Incident, generate_uuid, utc_now
from datetime import timedelta

logger = logging.getLogger("aegis.seed")


# ── Seed Resources (Hyderabad) ───────────────────────────────────────────────

SEED_RESOURCES = [
    # Medical
    {"name": "Ambulance Unit Alpha", "type": "medical", "latitude": 17.3671, "longitude": 78.4757, "contact_phone": "+917799136844"},
    {"name": "Ambulance Unit Bravo", "type": "medical", "latitude": 17.4025, "longitude": 78.4750, "contact_phone": "+917799136844"},
    {"name": "Medical Response Team 1", "type": "medical", "latitude": 17.3934, "longitude": 78.3914, "contact_phone": "+917799136844"},

    # Rescue
    {"name": "Rescue Boat Team 1", "type": "rescue", "latitude": 17.3760, "longitude": 78.4780, "contact_phone": "+917799136844"},
    {"name": "Rescue Squad Alpha", "type": "rescue", "latitude": 17.4254, "longitude": 78.4744, "contact_phone": "+917799136844"},
    {"name": "Urban Search & Rescue", "type": "rescue", "latitude": 17.4435, "longitude": 78.3772, "contact_phone": "+917799136844"},

    # Food
    {"name": "Food Distribution Van 1", "type": "food", "latitude": 17.4375, "longitude": 78.4483, "contact_phone": "+917799136844"},
    {"name": "Community Kitchen Mobile", "type": "food", "latitude": 17.3687, "longitude": 78.5249, "contact_phone": "+917799136844"},

    # Shelter
    {"name": "Emergency Shelter - Gachibowli Stadium", "type": "shelter", "latitude": 17.4260, "longitude": 78.3353, "contact_phone": "+917799136844"},
    {"name": "Relief Camp - LB Nagar Community Hall", "type": "shelter", "latitude": 17.3457, "longitude": 78.5522, "contact_phone": "+917799136844"},
]


# ── Seed Historical Incidents (for RAG / ChromaDB) ──────────────────────────

SEED_HISTORICAL_INCIDENTS = [
    {
        "raw_text": "Flooding near Musi River bridge, families stuck on rooftops, water level rising fast. Need rescue boats urgently.",
        "severity": "critical",
        "need_type": "rescue",
        "landmark_name": "musi river",
        "latitude": 17.3760,
        "longitude": 78.4780,
        "status": "resolved",
    },
    {
        "raw_text": "Old man collapsed near Charminar market area. Not breathing properly. Please send ambulance.",
        "severity": "critical",
        "need_type": "medical",
        "landmark_name": "charminar",
        "latitude": 17.3616,
        "longitude": 78.4747,
        "status": "resolved",
    },
    {
        "raw_text": "Many families displaced by waterlogging in Dilsukhnagar. No food or clean water available since yesterday. Around 30 people.",
        "severity": "high",
        "need_type": "food",
        "landmark_name": "dilsukhnagar",
        "latitude": 17.3687,
        "longitude": 78.5249,
        "status": "resolved",
    },
    {
        "raw_text": "Building partially collapsed near Mehdipatnam bus stop after heavy rains. People trapped inside. Fire brigade needed.",
        "severity": "critical",
        "need_type": "rescue",
        "landmark_name": "mehdipatnam",
        "latitude": 17.3950,
        "longitude": 78.4422,
        "status": "resolved",
    },
    {
        "raw_text": "Need shelter urgently. Our house in Kukatpally is flooded completely. Family of 6 with small children and elderly.",
        "severity": "high",
        "need_type": "shelter",
        "landmark_name": "kukatpally",
        "latitude": 17.4849,
        "longitude": 78.3990,
        "status": "resolved",
    },
]


async def seed_resources(session: AsyncSession) -> None:
    """Seed resources if table is empty."""
    count = await session.scalar(select(func.count()).select_from(Resource))
    if count > 0:
        logger.info(f"Resources table already has {count} rows, skipping seed.")
        return

    for r in SEED_RESOURCES:
        resource = Resource(
            id=generate_uuid(),
            name=r["name"],
            type=r["type"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            status="available",
            contact_phone=r["contact_phone"],
        )
        session.add(resource)

    await session.commit()
    logger.info(f"Seeded {len(SEED_RESOURCES)} resources.")


async def seed_historical_incidents(session: AsyncSession) -> list[dict]:
    """
    Seed historical incidents if table is empty.
    Returns list of dicts for ChromaDB seeding.
    """
    count = await session.scalar(select(func.count()).select_from(Incident))
    if count > 0:
        logger.info(f"Incidents table already has {count} rows, skipping seed.")
        return []

    seeded = []
    base_time = utc_now() - timedelta(days=7)  # Historical incidents from a week ago

    for i, inc in enumerate(SEED_HISTORICAL_INCIDENTS):
        incident = Incident(
            id=generate_uuid(),
            raw_text=inc["raw_text"],
            sender_phone=f"+9199000000{i:02d}",
            status=inc["status"],
            severity=inc["severity"],
            need_type=inc["need_type"],
            landmark_name=inc["landmark_name"],
            latitude=inc["latitude"],
            longitude=inc["longitude"],
            created_at=base_time + timedelta(hours=i * 3),
            updated_at=base_time + timedelta(hours=i * 3 + 1),
        )
        session.add(incident)
        seeded.append({
            "id": incident.id,
            "text": inc["raw_text"],
            "severity": inc["severity"],
            "need_type": inc["need_type"],
            "landmark": inc["landmark_name"],
        })

    await session.commit()
    logger.info(f"Seeded {len(SEED_HISTORICAL_INCIDENTS)} historical incidents.")
    return seeded


async def run_seed(session: AsyncSession) -> list[dict]:
    """Run all seed operations. Returns historical incidents for ChromaDB seeding."""
    await seed_resources(session)
    return await seed_historical_incidents(session)
