import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = "showup.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        bio TEXT DEFAULT '',
        sports TEXT DEFAULT '',          -- comma-separated
        skill_level TEXT DEFAULT 'beginner',
        photo_path TEXT,
        lat REAL DEFAULT 44.4268,        -- Bucharest default
        lng REAL DEFAULT 26.1025,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        sport TEXT NOT NULL,
        date TEXT NOT NULL,              -- YYYY-MM-DD
        time_window TEXT NOT NULL,       -- 'morning'|'afternoon'|'evening'
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sport TEXT NOT NULL,
        date TEXT NOT NULL,
        time_window TEXT NOT NULL,
        captain_id INTEGER NOT NULL,
        venue_id INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS event_members (
        event_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        confirmed INTEGER DEFAULT 0,
        PRIMARY KEY(event_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS venues (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        sport_types TEXT NOT NULL,
        address TEXT,
        lat REAL,
        lng REAL,
        price_per_hour INTEGER DEFAULT 0
    );
    """)
    conn.commit()
    # idempotent migration: add proximity_matched to events if it doesn't exist yet
    try:
        conn.execute("ALTER TABLE events ADD COLUMN proximity_matched INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.close()

# --- user helpers ---
def create_user(username):
    conn = get_conn()
    try:
        cur = conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
        user_id = cur.lastrowid
        conn.execute("INSERT INTO profiles (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_name(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_profile(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_profile(user_id, bio, sports, skill_level, photo_path=None):
    conn = get_conn()
    if photo_path:
        conn.execute("""UPDATE profiles SET bio=?, sports=?, skill_level=?, photo_path=?
                        WHERE user_id=?""",
                     (bio, sports, skill_level, photo_path, user_id))
    else:
        conn.execute("""UPDATE profiles SET bio=?, sports=?, skill_level=?
                        WHERE user_id=?""",
                     (bio, sports, skill_level, user_id))
    conn.commit()
    conn.close()
    
    # --- availability helpers ---
def add_availability(user_id, sport, date, time_window):
    conn = get_conn()
    # avoid duplicate (same user/sport/date/window)
    conn.execute("""DELETE FROM availability
                    WHERE user_id=? AND sport=? AND date=? AND time_window=?""",
                 (user_id, sport, date, time_window))
    conn.execute("""INSERT INTO availability (user_id, sport, date, time_window)
                    VALUES (?,?,?,?)""", (user_id, sport, date, time_window))
    conn.commit()
    conn.close()

def get_user_availability(user_id, date=None):
    conn = get_conn()
    if date:
        rows = conn.execute("""SELECT * FROM availability
                               WHERE user_id=? AND date=?""",
                            (user_id, date)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM availability WHERE user_id=?",
                            (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_availability(date, sport=None):
    """Used by matcher."""
    conn = get_conn()
    if sport:
        rows = conn.execute("""SELECT a.*, p.skill_level, p.lat, p.lng, u.username
                               FROM availability a
                               JOIN profiles p ON a.user_id = p.user_id
                               JOIN users u ON a.user_id = u.id
                               WHERE a.date=? AND a.sport=?""",
                            (date, sport)).fetchall()
    else:
        rows = conn.execute("""SELECT a.*, p.skill_level, p.lat, p.lng, u.username
                               FROM availability a
                               JOIN profiles p ON a.user_id = p.user_id
                               JOIN users u ON a.user_id = u.id
                               WHERE a.date=?""", (date,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_availability_for_matching(date, time_window):
    conn = get_conn()
    rows = conn.execute("""SELECT a.*, u.username, p.lat, p.lng
                           FROM availability a
                           JOIN users u ON a.user_id = u.id
                           JOIN profiles p ON a.user_id = p.user_id
                           WHERE a.date=? AND a.time_window=?""",
                        (date, time_window)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- event helpers ---
def create_event(sport, date, time_window, captain_id, proximity_matched=0):
    conn = get_conn()
    cur = conn.execute("""INSERT INTO events (sport, date, time_window, captain_id, status, proximity_matched)
                          VALUES (?,?,?,?,'pending',?)""",
                       (sport, date, time_window, captain_id, proximity_matched))
    event_id = cur.lastrowid
    conn.commit()
    conn.close()
    return event_id

def add_event_member(event_id, user_id):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO event_members (event_id, user_id) VALUES (?,?)",
                 (event_id, user_id))
    conn.commit()
    conn.close()

def get_event(event_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_events(user_id):
    conn = get_conn()
    rows = conn.execute("""SELECT e.*
                           FROM events e
                           JOIN event_members em ON e.id = em.event_id
                           WHERE em.user_id = ?
                           ORDER BY e.date DESC, e.time_window""",
                        (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_event_members_detail(event_id):
    conn = get_conn()
    rows = conn.execute("""SELECT em.user_id, em.confirmed, u.username
                           FROM event_members em
                           JOIN users u ON em.user_id = u.id
                           WHERE em.event_id = ?""",
                        (event_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_event_members_profiles(event_id):
    """Returns members with full profile data for AI compatibility scoring."""
    conn = get_conn()
    rows = conn.execute("""SELECT u.username, p.bio, p.sports, p.skill_level
                           FROM event_members em
                           JOIN users u ON em.user_id = u.id
                           JOIN profiles p ON em.user_id = p.user_id
                           WHERE em.event_id = ?""",
                        (event_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_discoverable_events(user_id):
    """Events the user is NOT a member of, date >= today, with captain name, member count, venue lat/lng."""
    conn = get_conn()
    today = datetime.today().strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT e.*,
               u.username  AS captain_username,
               COUNT(em.user_id) AS member_count,
               v.lat       AS venue_lat,
               v.lng       AS venue_lng
        FROM events e
        JOIN users u ON e.captain_id = u.id
        JOIN event_members em ON e.id = em.event_id
        LEFT JOIN venues v ON e.venue_id = v.id
        WHERE e.date >= ?
          AND e.id NOT IN (
              SELECT event_id FROM event_members WHERE user_id = ?
          )
        GROUP BY e.id
        ORDER BY e.date ASC, e.time_window ASC
    """, (today, user_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def count_pending_for_user(user_id):
    """Count of future/today events where user hasn't confirmed."""
    conn = get_conn()
    today = datetime.today().strftime("%Y-%m-%d")
    row = conn.execute("""SELECT COUNT(*) AS n
                          FROM event_members em
                          JOIN events e ON em.event_id = e.id
                          WHERE em.user_id=? AND em.confirmed=0 AND e.date>=?""",
                       (user_id, today)).fetchone()
    conn.close()
    return row["n"]

def get_user_pending_event_ids(user_id):
    """Set of event IDs where user is unconfirmed and event date >= today."""
    conn = get_conn()
    today = datetime.today().strftime("%Y-%m-%d")
    rows = conn.execute("""SELECT em.event_id
                           FROM event_members em
                           JOIN events e ON em.event_id = e.id
                           WHERE em.user_id=? AND em.confirmed=0 AND e.date>=?""",
                        (user_id, today)).fetchall()
    conn.close()
    return {r["event_id"] for r in rows}

def update_event_member_confirmation(event_id, user_id, confirmed):
    conn = get_conn()
    conn.execute("UPDATE event_members SET confirmed=? WHERE event_id=? AND user_id=?",
                 (confirmed, event_id, user_id))
    conn.commit()
    conn.close()

def update_event_venue(event_id, venue_id):
    conn = get_conn()
    conn.execute("UPDATE events SET venue_id=? WHERE id=?", (venue_id, event_id))
    conn.commit()
    conn.close()

# --- message helpers ---
def get_event_messages(event_id):
    conn = get_conn()
    rows = conn.execute("""SELECT m.*, u.username
                           FROM messages m
                           JOIN users u ON m.user_id = u.id
                           WHERE m.event_id = ?
                           ORDER BY m.created_at ASC""",
                        (event_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_message(event_id, user_id, content):
    conn = get_conn()
    conn.execute("INSERT INTO messages (event_id, user_id, content) VALUES (?,?,?)",
                 (event_id, user_id, content))
    conn.commit()
    conn.close()

# --- venue helpers ---
def seed_venues(venues_list):
    conn = get_conn()
    for v in venues_list:
        conn.execute("""INSERT OR IGNORE INTO venues (id, name, sport_types, address, lat, lng, price_per_hour)
                        VALUES (?,?,?,?,?,?,?)""",
                     (v["id"], v["name"], ",".join(v["sport_types"]),
                      v["address"], v["lat"], v["lng"], v["price_per_hour"]))
    conn.commit()
    conn.close()