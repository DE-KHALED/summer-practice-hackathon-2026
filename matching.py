import random
import db

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

def run_matching(date, time_window):
    """
    Match users available on date/time_window.
    Creates events + members in db. Returns list of new event IDs.
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
        random.shuffle(users)
        while len(users) >= min_size:
            group = users[:max_size]
            users = users[max_size:]
            captain = random.choice(group)
            event_id = db.create_event(sport, date, time_window, captain["user_id"])
            for u in group:
                db.add_event_member(event_id, u["user_id"])
            created_ids.append(event_id)

    return created_ids
