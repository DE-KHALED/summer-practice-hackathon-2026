# 🏃 ShowUp2Move

> Spontaneous sports. Just show up.

A smart social sports-matching platform that turns "I want to play today" into a real organized game in 30 seconds. Built solo for the **Summer Practice Hackathon 2026**.

🌐 **Live demo:** [your-streamlit-url-here](hhttps://summer-practice-hackathon-2026-cgegucotprw9chtyfasd8f.streamlit.app/
📦 **Stack:** Streamlit · Python · SQLite · Gemini AI · Folium · bcrypt

---

## The Problem

Modern schedules destroy fixed sports groups. People want to play, but coordinating one game takes more energy than the game itself. Most apps assume recurring commitments — that's not real life. Real life is: you wake up Saturday wanting to play _today_.

**ShowUp2Move's insight:** spontaneous sports needs zero-friction matching plus AI-driven group fit, not better calendars.

---

## What It Does

| Feature                         | How it works                                                                                               |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 🔐 **Secure auth**              | Username + bcrypt-hashed passwords (same standard banks use)                                               |
| ✨ **AI bio extraction**        | Gemini reads your bio in plain English and auto-fills your sports + skill level                            |
| 🗓️ **One-tap availability**     | "ShowUpToday?" picker — pick a day, time window, and sport. One tap                                        |
| 🤝 **Smart matching**           | Group-size aware (Football 10–14, Tennis 2–4, etc.) + proximity-aware via the **Haversine formula**        |
| 👑 **Auto-coordination**        | Random captain selection + auto-assigned closest compatible venue                                          |
| 🧠 **AI compatibility scoring** | Gemini reads everyone's bios and predicts group fit (0–100) — turns one-time matches into recurring groups |
| 💬 **Group chat**               | Native event chat per group                                                                                |
| 🗺️ **Maps**                     | Folium + OpenStreetMap with real Bucharest venues                                                          |
| 🔔 **Notifications**            | Sidebar badge + "action needed" tags for unconfirmed events                                                |
| 🌍 **Discover**                 | Map of all joinable events nearby                                                                          |

---

## Architecture

User clicks button in browser
↓
Streamlit re-runs app.py top-to-bottom
↓
Router checks st.session_state.user_id
↓
Picks the right page() function
↓
Page calls db.py helpers → SQLite reads/writes
↓
Page may call ai.py → Gemini API → JSON back
↓
Streamlit renders the new state

### Project Structure

showup2move/
├── app.py # Streamlit entry point — all UI pages and routing
├── db.py # SQLite schema, migrations, CRUD helpers, bcrypt auth
├── matching.py # Proximity-aware matching algorithm + auto-venue assignment
├── ai.py # Gemini integration — bio extraction + group compatibility
├── venues.py # Hardcoded Bucharest sports venues with lat/lng
├── seed.py # Generates 12 demo users with availability data
├── requirements.txt # Python dependencies
└── .streamlit/
└── secrets.toml # GEMINI_API_KEY (gitignored)

### Database Schema

Six tables in SQLite:

- `users` — credentials (bcrypt password_hash)
- `profiles` — bio, sports, skill_level, photo, lat/lng
- `availability` — user × sport × date × time_window
- `events` — created by matching, has captain and venue
- `event_members` — who's in each event, confirmation status
- `messages` — per-event chat history

---

## How Matching Works

For a given date + time window, the algorithm:

1. Pulls all available users grouped by sport
2. Checks per-sport group-size rules (Football: 10–14, Tennis: 2–4, Basketball: 6–10, etc.)
3. **Proximity sort:** computes the geographic centroid of candidates and sorts by Haversine distance
4. Takes the closest `max_size` users into a group; if remaining users meet `min_size`, forms another group
5. Randomly picks a captain
6. **Auto-assigns the closest compatible venue** to the group's centroid
7. Inserts `events` and `event_members` rows

The captain can override the venue via the dropdown if they prefer somewhere else.

---

## AI Features

Two distinct uses of Gemini, both with structured JSON outputs:

### 1. Bio → Sports Extraction

> Input: _"I love football and weekend tennis, played volleyball in college, intermediate level."_
>
> Output: `{"sports": ["Football", "Tennis", "Volleyball"], "skill_level": "intermediate"}`

### 2. Group Compatibility Scoring

> Input: List of members with bios, sports, skill levels
>
> Output: `{"score": 87, "reason": "All intermediate-to-advanced players with overlapping weekend availability", "best_pairs": ["alex_ro & maria_b"]}`

Both features include a **4-model fallback chain** (`gemini-flash-latest` → `gemini-2.0-flash` → `gemini-1.5-flash-8b` → `gemini-1.5-flash`) so if one hits quota, the next takes over automatically.

---

## Run Locally

```bash
# 1. Clone and enter
git clone https://github.com/DE-KHALED/summer-practice-hackathon-2026.git
cd summer-practice-hackathon-2026

# 2. Virtual environment
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Gemini API key
mkdir -p .streamlit
echo 'GEMINI_API_KEY = "your-key-here"' > .streamlit/secrets.toml

# 5. Seed demo data (12 users, varied availability)
python seed.py

# 6. Run
streamlit run app.py
```

Get a free Gemini API key at https://aistudio.google.com/apikey.

### Demo credentials

All seeded users use the password **`demo123`**. Try logging in as:

- `alex_ro`
- `maria_b`
- `vlad_t`
- _(or sign up with your own username + password)_

---

## Demo Flow

1. **Login** as `alex_ro` / `demo123`
2. **Profile** → click **✨ Auto-detect from bio** to see Gemini extract sports
3. **Show up today** → pick a sport for today/morning
4. **Sidebar → Run Matching Now** → today, morning
5. **My Events** → open your matched football game
6. **Compatibility score** loads at top — Gemini's group fit prediction
7. **Map** shows auto-assigned venue; captain can override
8. **Group chat** for coordination

---

## Tech Decisions & Tradeoffs

| Decision            | Why                              | Production swap                                |
| ------------------- | -------------------------------- | ---------------------------------------------- |
| Streamlit           | Solo build, fastest Python → web | React Native + FastAPI                         |
| SQLite              | Zero setup, single file          | Postgres (schema is portable)                  |
| Polling-based chat  | Simple, no websocket infra       | Supabase Realtime / Redis pubsub               |
| Hardcoded venues    | Fake-it-til-you-make-it          | Google Places API                              |
| Username + password | Real bcrypt, hackathon-scoped    | OAuth (Google, Apple)                          |
| Gemini free tier    | Free + fast                      | Provider-agnostic interface — 10 lines to swap |

---

## What's Next

- Real-time chat (Supabase Realtime)
- Calendar sync (Google Calendar API)
- Photo-based AI sport detection (already supported by Gemini Vision)
- OAuth login
- Push notifications
- Manual event creation flow
- Recurring group memory ("you played with these people last week — match again?")

---

## Built By

**Khaled** — solo, in roughly 6 hours.

Stack: Python · Streamlit · SQLite · Gemini · Folium · bcrypt
Hackathon: Summer Practice Hackathon 2026

---
