#!/usr/bin/env python3
"""
Seed 12 fake users with availability for today + next 2 days.
Safe to rerun (idempotent).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import db
from venues import VENUES
from datetime import date, timedelta

FAKE_USERS = [
    {
        "username": "alex_ro",
        "bio": "Love weekend football with friends, also enjoy morning runs and casual basketball pickup games.",
        "sports": "Football,Basketball,Running",
        "skill": "intermediate",
    },
    {
        "username": "maria_b",
        "bio": "Tennis enthusiast, competed at regional level. Play padel and a bit of volleyball too.",
        "sports": "Tennis,Padel,Volleyball",
        "skill": "advanced",
    },
    {
        "username": "stefan_c",
        "bio": "Just getting into sports, started football and basketball last year, now trying tennis.",
        "sports": "Football,Basketball,Tennis",
        "skill": "beginner",
    },
    {
        "username": "ioana_p",
        "bio": "Swimming is my therapy. Also enjoy basketball leagues and trail running on weekends.",
        "sports": "Swimming,Basketball,Running",
        "skill": "intermediate",
    },
    {
        "username": "andrei_m",
        "bio": "Big football fan, play basketball on weekends, recently picked up tennis at the park.",
        "sports": "Football,Basketball,Tennis",
        "skill": "intermediate",
    },
    {
        "username": "elena_v",
        "bio": "Former volleyball team captain. Love football and basketball pickup games after work.",
        "sports": "Football,Volleyball,Basketball",
        "skill": "advanced",
    },
    {
        "username": "radu_d",
        "bio": "Started cycling this spring. Also into football with colleagues and morning jogs.",
        "sports": "Football,Cycling,Running",
        "skill": "beginner",
    },
    {
        "username": "cristina_n",
        "bio": "Padel and tennis are my weekend go-tos. Also play football with my office team.",
        "sports": "Football,Padel,Tennis",
        "skill": "intermediate",
    },
    {
        "username": "bogdan_f",
        "bio": "Casual footballer who loves long cycling routes and occasional swimming sessions.",
        "sports": "Football,Swimming,Cycling",
        "skill": "beginner",
    },
    {
        "username": "ana_l",
        "bio": "Running enthusiast training for a half marathon. Also enjoy football and basketball.",
        "sports": "Football,Basketball,Running",
        "skill": "intermediate",
    },
    {
        "username": "mihai_t",
        "bio": "Competitive cyclist, avid football player, recreational swimmer. Always up for a match.",
        "sports": "Football,Cycling,Swimming",
        "skill": "advanced",
    },
    {
        "username": "diana_s",
        "bio": "Volleyball and tennis player since high school. Also play football for fun on weekends.",
        "sports": "Football,Volleyball,Tennis",
        "skill": "intermediate",
    },
]

# Per-user availability plan: list of (sport, time_windows) to create for each of 3 days
# Designed so Football has 10 players (min) and Basketball/Tennis also hit minimum
USER_AVAILABILITY = {
    "alex_ro":    [("Football", ["morning", "afternoon"]), ("Basketball", ["morning"]), ("Running", ["evening"])],
    "maria_b":    [("Tennis", ["morning", "afternoon"]), ("Padel", ["morning"]), ("Volleyball", ["evening"])],
    "stefan_c":   [("Football", ["morning"]), ("Basketball", ["morning", "afternoon"]), ("Tennis", ["evening"])],
    "ioana_p":    [("Swimming", ["morning"]), ("Basketball", ["afternoon"]), ("Running", ["morning"])],
    "andrei_m":   [("Football", ["morning", "evening"]), ("Basketball", ["morning"]), ("Tennis", ["afternoon"])],
    "elena_v":    [("Football", ["morning"]), ("Basketball", ["morning", "afternoon"]), ("Volleyball", ["evening"])],
    "radu_d":     [("Football", ["morning", "afternoon"]), ("Cycling", ["morning"]), ("Running", ["evening"])],
    "cristina_n": [("Football", ["morning"]), ("Tennis", ["morning", "afternoon"]), ("Padel", ["morning"])],
    "bogdan_f":   [("Football", ["morning", "afternoon"]), ("Swimming", ["morning"]), ("Cycling", ["evening"])],
    "ana_l":      [("Football", ["morning"]), ("Basketball", ["morning", "afternoon"]), ("Running", ["morning"])],
    "mihai_t":    [("Football", ["morning", "evening"]), ("Cycling", ["afternoon"]), ("Swimming", ["morning"])],
    "diana_s":    [("Football", ["morning"]), ("Volleyball", ["afternoon"]), ("Tennis", ["morning"])],
}


def seed():
    db.init_db()
    db.seed_venues(VENUES)

    today = date.today()
    dates = [today + timedelta(days=i) for i in range(3)]

    conn = db.get_conn()

    demo_hash = db.hash_password("demo123")
    for user_data in FAKE_USERS:
        uname = user_data["username"]
        # idempotent user creation — sets password on first insert only
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
            (uname, demo_hash),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM users WHERE username=?", (uname,)).fetchone()
        uid = row["id"]

        # upsert profile
        conn.execute("""INSERT OR IGNORE INTO profiles (user_id) VALUES (?)""", (uid,))
        conn.execute("""UPDATE profiles SET bio=?, sports=?, skill_level=? WHERE user_id=?""",
                     (user_data["bio"], user_data["sports"], user_data["skill"], uid))
        conn.commit()

        # availability: clear existing seed dates, then insert
        plan = USER_AVAILABILITY.get(uname, [])
        for d in dates:
            d_str = d.isoformat()
            for sport, windows in plan:
                for window in windows:
                    conn.execute("""DELETE FROM availability
                                    WHERE user_id=? AND sport=? AND date=? AND time_window=?""",
                                 (uid, sport, d_str, window))
                    conn.execute("""INSERT INTO availability (user_id, sport, date, time_window)
                                    VALUES (?,?,?,?)""",
                                 (uid, sport, d_str, window))
        conn.commit()

    conn.close()
    print(f"Seeded {len(FAKE_USERS)} users with availability for {[d.isoformat() for d in dates]}")
    print("Venues seeded:", len(VENUES))


if __name__ == "__main__":
    seed()
