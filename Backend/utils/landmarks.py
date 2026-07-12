"""
AEGIS — Fixed Landmark Gazetteer
Pre-seeded landmarks for Hyderabad, India with known coordinates.
The Geolocation Agent matches extracted location text against this list
before falling back to Google Maps API — deterministic and demo-safe.
"""

# Format: "landmark_keyword": (latitude, longitude)
# Keys are lowercase for fuzzy matching
LANDMARKS: dict[str, tuple[float, float]] = {
    # Major landmarks
    "charminar": (17.3616, 78.4747),
    "hussain sagar": (17.4239, 78.4738),
    "tank bund": (17.4254, 78.4744),
    "necklace road": (17.4180, 78.4694),
    "secunderabad railway station": (17.4337, 78.5016),
    "secunderabad station": (17.4337, 78.5016),

    # Tech / business areas
    "hitech city": (17.4435, 78.3772),
    "hitec city": (17.4435, 78.3772),
    "gachibowli": (17.4260, 78.3353),
    "gachibowli stadium": (17.4260, 78.3353),
    "madhapur": (17.4400, 78.3863),
    "kondapur": (17.4577, 78.3715),
    "jubilee hills": (17.4325, 78.4076),
    "banjara hills": (17.4138, 78.4380),
    "financial district": (17.4216, 78.3380),

    # Residential / transit areas
    "lb nagar": (17.3457, 78.5522),
    "dilsukhnagar": (17.3687, 78.5249),
    "mehdipatnam": (17.3950, 78.4422),
    "kukatpally": (17.4849, 78.3990),
    "ameerpet": (17.4375, 78.4483),
    "begumpet": (17.4440, 78.4707),
    "miyapur": (17.4969, 78.3548),
    "uppal": (17.3988, 78.5594),
    "habsiguda": (17.4090, 78.5307),

    # Hospitals / emergency-relevant
    "osmania hospital": (17.3671, 78.4757),
    "gandhi hospital": (17.4025, 78.4750),
    "nims hospital": (17.3934, 78.3914),
    "yashoda hospital": (17.4120, 78.4500),

    # Water bodies / flood-prone areas
    "musi river": (17.3760, 78.4780),
    "musi bridge": (17.3760, 78.4780),
    "hussain sagar lake": (17.4239, 78.4738),
    "durgam cheruvu": (17.4315, 78.3832),
    "saroornagar lake": (17.3590, 78.5290),
    "nacharam lake": (17.4148, 78.5467),

    # Bridges
    "purana pul": (17.3690, 78.4630),
    "chaderghat bridge": (17.3730, 78.4850),
    "old bridge": (17.3690, 78.4630),
    "main bridge": (17.3730, 78.4850),
}


def lookup_landmark(query: str) -> tuple[str, float, float] | None:
    """
    Fuzzy match a query string against the landmark table.
    Returns (landmark_name, lat, lng) or None if no match found.

    Matching strategy:
    1. Exact key match (lowercase)
    2. Key contained in query
    3. Query contained in key
    """
    query_lower = query.lower().strip()

    # Exact match
    if query_lower in LANDMARKS:
        lat, lng = LANDMARKS[query_lower]
        return (query_lower, lat, lng)

    # Key contained in query (e.g., query="near charminar area" matches "charminar")
    best_match = None
    best_len = 0
    for key, (lat, lng) in LANDMARKS.items():
        if key in query_lower and len(key) > best_len:
            best_match = (key, lat, lng)
            best_len = len(key)

    if best_match:
        return best_match

    # Query contained in key (e.g., query="nims" matches "nims hospital")
    for key, (lat, lng) in LANDMARKS.items():
        if query_lower in key:
            return (key, lat, lng)

    return None
