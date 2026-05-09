import math
import random
import db
from venues import VENUES

SPORT_SIZES = {
    "Football":   (10, 14),
    "Basketball": (6, 10),
    "Volleyball": (8, 12),
    "Tennis":     (2, 4),
    "Padel":      (4, 4),
    "Running":    (2, 8),
    "Cycling":    (2, 8),
    "Swimming":   (2, 6),
}

def _haversine(lat1, lng1, lat2, lng2):
    """Returns great-circle distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))

def _centroid(users):
    lat = sum(u["lat"] for u in users) / len(users)
    lng = sum(u["lng"] for u in users) / len(users)
    return lat, lng

def run_matching(date, time_window):
    """
    Match users available on date/time_window.
    When candidates exceed max_size, sorts by Haversine distance to the
    group centroid so the geographically closest players form each game.
    Auto-assigns the nearest compatible venue to every created event.
    Returns list of created event IDs.
    """
    rows = db.get_all_availability_for_matching(date, time_window)

    # group by sport, deduplicate per user
    by_sport = {}
    seen = set()
    for row in rows:
        key = (row["sport"], row["user_id"])
        if key in seen:
            continue
        seen.add(key)
        by_sport.setdefault(row["sport"], []).append(row)

    created_ids = []
    for sport, users in by_sport.items():
        min_size, max_size = SPORT_SIZES.get(sport, (2, 8))
        if len(users) < min_size:
            continue

        # proximity sort only when there are more candidates than one group can hold
        use_proximity = len(users) > max_size
        if use_proximity:
            clat, clng = _centroid(users)
            users.sort(key=lambda u: _haversine(u["lat"], u["lng"], clat, clng))
        else:
            random.shuffle(users)

        sport_venues = [v for v in VENUES if sport in v["sport_types"]]

        while len(users) >= min_size:
            group = users[:max_size]
            users = users[max_size:]
            captain = random.choice(group)
            event_id = db.create_event(
                sport, date, time_window, captain["user_id"],
                proximity_matched=1 if use_proximity else 0,
            )
            for u in group:
                db.add_event_member(event_id, u["user_id"])

            # auto-assign closest compatible venue
            if sport_venues:
                glat, glng = _centroid(group)
                closest = min(sport_venues,
                              key=lambda v: _haversine(glat, glng, v["lat"], v["lng"]))
                db.update_event_venue(event_id, closest["id"])

            created_ids.append(event_id)

    return created_ids
