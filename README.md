# 🏃 ShowUp2Move

Hackathon submission — a smart sports-matching platform that turns "I want to play today" into a real organized game in 30 seconds.

## What it does

- **Profile** with AI bio analysis: paste a bio, Gemini extracts your sports + skill level automatically
- **ShowUpToday?** one-tap availability for any day/time window
- **Smart matching** respects sport-specific group sizes (Football 10–14, Tennis 2–4, etc.) and randomly assigns a captain
- **Event detail** with group chat, captain venue picker, interactive map, and AI-powered group compatibility scoring
- **Notifications** show pending events that need confirmation

## Stack

- Streamlit + Python + SQLite (single-file deploy)
- Gemini API for bio extraction and group compatibility
- streamlit-folium for maps
- Hardcoded venues around Bucharest

## Run locally

```bash
pip install -r requirements.txt
python seed.py
streamlit run app.py
```

Add your Gemini key to `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-key"
```

## Demo flow

1. Login as `alex_ro`
2. Profile → ✨ Auto-detect from bio
3. Show up today → pick day, click sport
4. Sidebar → Run matching now
5. My events → open match → see compatibility score, chat, map

## Built solo in ~5 hours.
