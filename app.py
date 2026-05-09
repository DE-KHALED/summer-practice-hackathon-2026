import streamlit as st
from pathlib import Path
import db
from datetime import date as dt_date, timedelta
st.set_page_config(page_title="ShowUp2Move", page_icon="🏃", layout="centered")
db.init_db()

st.markdown(
    "<h1 style='margin-bottom:0;'>🏃 ShowUp2Move</h1>"
    "<p style='color:#888;margin-top:0;font-size:0.95em;'>Spontaneous sports. Just show up.</p>",
    unsafe_allow_html=True,
)

SPORTS = ["Football", "Basketball", "Tennis", "Volleyball", "Running", "Cycling", "Padel", "Swimming"]
SKILLS = ["beginner", "intermediate", "advanced"]

def _fmt_dt(date_str, time_window=None):
    d = dt_date.fromisoformat(date_str)
    s = d.strftime("%a %d %b")
    return f"{s} · {time_window}" if time_window else s

# --- session ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None

# --- login screen ---
def login_screen():
    mode = st.radio("", ["Log in", "Sign up"], horizontal=True, label_visibility="collapsed")
    st.caption("💡 Demo users (alex_ro, etc.) all use password: **demo123**")
    st.divider()

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if mode == "Sign up":
        confirm = st.text_input("Confirm password", type="password")
        if st.button("Sign up", use_container_width=True, type="primary"):
            if not username.strip():
                st.error("Username is required.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            elif password != confirm:
                st.error("Passwords don't match.")
            else:
                uid = db.create_user(username.strip(), password)
                if uid:
                    st.session_state.user_id = uid
                    st.session_state.username = username.strip()
                    st.rerun()
                else:
                    st.error("Username taken — try another.")
    else:
        if st.button("Log in", use_container_width=True, type="primary"):
            u = db.verify_login(username, password)
            if u:
                st.session_state.user_id = u["id"]
                st.session_state.username = u["username"]
                st.rerun()
            else:
                st.error("Invalid username or password.")
from datetime import date as dt_date, timedelta


# --- profile page ---
def profile_page():
    st.header("Your profile")
    p = db.get_profile(st.session_state.user_id)

    bio = st.text_area("Tell us about yourself",
                       value=p["bio"],
                       placeholder="e.g. I love football and weekend tennis. Played volleyball in college.",
                       height=100,
                       key="bio_input")

    # AI extraction
    col_ai1, col_ai2 = st.columns([1, 2])
    if col_ai1.button("✨ Auto-detect from bio", use_container_width=True):
        if not bio.strip():
            st.warning("Write a bio first!")
        else:
            with st.spinner("Claude is reading your bio..."):
                from ai import extract_sports_from_bio
                result = extract_sports_from_bio(bio)
                if result:
                    st.session_state.ai_sports = result["sports"]
                    st.session_state.ai_skill = result["skill_level"]
                    st.success(f"Detected: {', '.join(result['sports'])} · {result['skill_level']}")
                else:
                    st.error("AI unavailable — fill manually.")

    current_sports = st.session_state.get("ai_sports") or [s for s in p["sports"].split(",") if s]
    sports = st.multiselect("Sports you play", SPORTS, default=current_sports)

    default_skill = st.session_state.get("ai_skill") or (p["skill_level"] if p["skill_level"] in SKILLS else "beginner")
    skill = st.select_slider("Skill level", SKILLS, value=default_skill)

    photo = st.file_uploader("Profile photo (optional)", type=["png", "jpg", "jpeg"])
    photo_path = None
    if photo:
        Path("uploads").mkdir(exist_ok=True)
        photo_path = f"uploads/{st.session_state.user_id}_{photo.name}"
        with open(photo_path, "wb") as f:
            f.write(photo.read())

    if p["photo_path"]:
        st.image(p["photo_path"], width=120)

    if st.button("💾 Save profile", type="primary"):
        db.update_profile(st.session_state.user_id, bio, ",".join(sports), skill, photo_path)
        st.session_state.pop("ai_sports", None)
        st.session_state.pop("ai_skill", None)
        st.toast("✅ Profile saved!")
        st.rerun()


def showup_page():
    st.header("🏃 Show up today?")
    st.caption("Tell us when you're free. We'll match you with people who want to play.")

    p = db.get_profile(st.session_state.user_id)
    user_sports = [s for s in p["sports"].split(",") if s]

    if not user_sports:
        st.warning("Add some sports to your profile first!")
        return

    # date picker — today and next 6 days
    today = dt_date.today()
    date_options = [(today + timedelta(days=i)) for i in range(7)]
    date_labels = [d.strftime("%a %d %b") for d in date_options]
    date_idx = st.radio("When?", range(7),
                        format_func=lambda i: date_labels[i],
                        horizontal=True)
    selected_date = date_options[date_idx].isoformat()

    time_window = st.radio("Time of day",
                           ["morning", "afternoon", "evening"],
                           horizontal=True,
                           format_func=lambda x: {
                               "morning": "🌅 Morning",
                               "afternoon": "☀️ Afternoon",
                               "evening": "🌆 Evening"
                           }[x])

    st.divider()
    st.subheader("Which sports are you up for?")

    cols = st.columns(min(len(user_sports), 3))
    for i, sport in enumerate(user_sports):
        with cols[i % len(cols)]:
            if st.button(f"✅ {sport}", key=f"yes_{sport}", use_container_width=True):
                db.add_availability(st.session_state.user_id, sport, selected_date, time_window)
                st.toast(f"You're in for {sport} on {date_labels[date_idx]} {time_window}!", icon="🎉")

    # show current availability
    st.divider()
    st.subheader("Your upcoming availability")
    avail = db.get_user_availability(st.session_state.user_id)
    if not avail:
        st.info("🗓️ Pick a sport above to get started.")
    else:
        for a in sorted(avail, key=lambda x: (x["date"], x["time_window"])):
            d = dt_date.fromisoformat(a["date"])
            st.write(f"• **{a['sport']}** — {d.strftime('%a %d %b')} ({a['time_window']})")


# --- my events page ---
def my_events_page():
    st.header("🗓️ My Events")
    events = db.get_user_events(st.session_state.user_id)

    if not events:
        st.info("👀 No matches yet! Head to **Show up today** to set your availability and get matched.")
        return

    today = dt_date.today().isoformat()
    upcoming = [e for e in events if e["date"] >= today]
    past = [e for e in events if e["date"] < today]
    pending_ids = db.get_user_pending_event_ids(st.session_state.user_id)

    def render_event_card(e, action_needed=False):
        members = db.get_event_members_detail(e["id"])
        captain = next((m for m in members if m["user_id"] == e["captain_id"]), None)
        captain_name = captain["username"] if captain else "Unknown"

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                if action_needed:
                    st.warning("🔔 Action needed")
                st.subheader(f"{e['sport']} — {_fmt_dt(e['date'], e['time_window'])}")
                st.caption(f"👑 Captain: {captain_name}")
                member_names = [
                    m["username"] + (" 👑" if m["user_id"] == e["captain_id"] else "")
                    for m in members
                ]
                st.write("Players: " + ", ".join(member_names))
                if e["venue_id"]:
                    from venues import VENUES
                    venue = next((v for v in VENUES if v["id"] == e["venue_id"]), None)
                    if venue:
                        st.write(f"📍 {venue['name']}")
            with col2:
                my_status = next((m for m in members if m["user_id"] == st.session_state.user_id), None)
                if my_status:
                    if my_status["confirmed"]:
                        st.success("✅ Confirmed")
                    else:
                        if st.button("✅ Confirm", key=f"confirm_{e['id']}", use_container_width=True):
                            db.update_event_member_confirmation(e["id"], st.session_state.user_id, 1)
                            st.toast("👍 You're confirmed!")
                            st.rerun()
                        if st.button("❌ Decline", key=f"decline_{e['id']}", use_container_width=True):
                            db.update_event_member_confirmation(e["id"], st.session_state.user_id, 0)
                            st.toast("Got it, marked as declined.")
                            st.rerun()
                if st.button("👁️ Open", key=f"view_{e['id']}", use_container_width=True, type="primary"):
                    st.session_state.selected_event_id = e["id"]
                    st.session_state.page = "event_detail"
                    st.rerun()

    if upcoming:
        st.subheader("Upcoming")
        for e in sorted(upcoming, key=lambda x: (x["id"] not in pending_ids, x["date"], x["time_window"])):
            render_event_card(e, action_needed=e["id"] in pending_ids)

    if past:
        st.subheader("Past")
        for e in sorted(past, key=lambda x: (x["date"], x["time_window"]), reverse=True):
            render_event_card(e)


# --- event detail page ---
def event_detail_page():
    event_id = st.session_state.get("selected_event_id")
    if not event_id:
        st.error("No event selected.")
        return

    e = db.get_event(event_id)
    if not e:
        st.error("Event not found.")
        return

    members = db.get_event_members_detail(event_id)
    captain = next((m for m in members if m["user_id"] == e["captain_id"]), None)
    captain_name = captain["username"] if captain else "Unknown"
    is_captain = e["captain_id"] == st.session_state.user_id

    if st.button("← Back to My Events"):
        st.session_state.page = "my_events"
        st.rerun()

    st.header(f"{e['sport']} — {_fmt_dt(e['date'], e['time_window'])}")
    st.caption(f"👑 Captain: {captain_name} · Status: {e['status']}")
    st.caption("📍 Matched by proximity")

    # member list
    st.subheader("Members")
    cols = st.columns(min(len(members), 4))
    for i, m in enumerate(members):
        confirmed_icon = "✅" if m["confirmed"] else "⏳"
        if m["user_id"] == e["captain_id"]:
            cols[i % len(cols)].markdown(f"{confirmed_icon} 👑 **{m['username']}** · Captain")
        else:
            cols[i % len(cols)].write(f"{confirmed_icon} {m['username']}")

    # venue display
    from venues import VENUES
    if e["venue_id"]:
        venue = next((v for v in VENUES if v["id"] == e["venue_id"]), None)
        if venue:
            st.divider()
            st.subheader("📍 Venue")
            st.write(f"**{venue['name']}**")
            st.caption(f"{venue['address']} · {venue['price_per_hour']} RON/hr")
            try:
                import folium
                from streamlit_folium import st_folium
                m_map = folium.Map(location=[venue["lat"], venue["lng"]], zoom_start=15)
                folium.Marker(
                    [venue["lat"], venue["lng"]], popup=venue["name"],
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m_map)
                st_folium(m_map, width=680, height=280)
            except Exception:
                st.write(f"Map unavailable — lat: {venue['lat']}, lng: {venue['lng']}")

    # captain: pick venue
    if is_captain:
        st.divider()
        st.subheader("🏟️ Pick Venue (Captain only)")
        sport_venues = [v for v in VENUES if e["sport"] in v["sport_types"]]
        if sport_venues:
            venue_labels = [f"{v['name']} ({v['price_per_hour']} RON/hr)" for v in sport_venues]
            selected_label = st.selectbox("Choose venue", venue_labels, key="venue_pick")
            selected_venue = sport_venues[venue_labels.index(selected_label)]
            if st.button("📌 Set venue", type="primary"):
                db.update_event_venue(event_id, selected_venue["id"])
                st.toast("📍 Venue set!")
                st.rerun()
        else:
            st.info("No hardcoded venues for this sport — add one to venues.py.")

    # group compatibility
    st.divider()
    compat_key = f"compat_{event_id}"
    col_title, col_btn = st.columns([5, 1])
    col_title.subheader("✨ Group Compatibility")
    if col_btn.button("🔄 Recompute", key=f"recompute_{event_id}"):
        st.session_state.pop(compat_key, None)
        st.rerun()

    if compat_key not in st.session_state:
        member_profiles = db.get_event_members_profiles(event_id)
        with st.spinner("Reading bios..."):
            from ai import compute_event_compatibility
            st.session_state[compat_key] = compute_event_compatibility(member_profiles)

    compat = st.session_state[compat_key]
    if compat is None:
        st.info("AI compatibility unavailable.")
    else:
        score = compat["score"]
        color = "green" if score > 75 else ("orange" if score >= 50 else "red")
        st.markdown(f"<h2 style='color:{color}'>{score}/100</h2>", unsafe_allow_html=True)
        st.write(compat["reason"])
        if compat.get("best_pairs"):
            st.caption("Best matches: " + ", ".join(compat["best_pairs"]))

    # suggested teams (Football with >= 6 members)
    if e["sport"] == "Football" and len(members) >= 6:
        st.divider()
        st.subheader("⚖️ Suggested teams")
        _SKILL_PTS   = {"advanced": 3, "intermediate": 2, "beginner": 1}
        _SKILL_BADGE = {"advanced": "🟢 advanced", "intermediate": "🟡 intermediate", "beginner": "🔴 beginner"}
        _profiles = db.get_event_members_profiles(event_id)
        _sorted  = sorted(_profiles, key=lambda m: _SKILL_PTS.get(m["skill_level"], 1), reverse=True)
        team_a, team_b = [], []
        for _i, _m in enumerate(_sorted):
            (team_a if _i % 4 in (0, 3) else team_b).append(_m)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Team A**")
            for _m in team_a:
                st.write(f"{_m['username']} · {_SKILL_BADGE.get(_m['skill_level'], _m['skill_level'])}")
        with col_b:
            st.markdown("**Team B**")
            for _m in team_b:
                st.write(f"{_m['username']} · {_SKILL_BADGE.get(_m['skill_level'], _m['skill_level'])}")
        with st.expander("Why?"):
            st.write("Teams balanced by skill level using snake draft.")

    # group chat
    st.divider()
    st.subheader("💬 Group Chat")
    messages = db.get_event_messages(event_id)
    if not messages:
        st.caption("💬 No messages yet — be the first to say hi!")
    for msg in messages:
        with st.chat_message("user"):
            st.markdown(f"**{msg['username']}**: {msg['content']}")
            st.caption(msg["created_at"])

    chat_input = st.chat_input("Say something to the group…")
    if chat_input:
        db.add_message(event_id, st.session_state.user_id, chat_input)
        st.rerun()


# --- discover page ---
def discover_page():
    st.header("🗺️ Discover Events")
    st.caption("Upcoming matches you can join.")

    events = db.get_discoverable_events(st.session_state.user_id)

    if not events:
        st.info("🏆 No open events right now — check back after the next matching run!")
        return

    from matching import SPORT_SIZES

    try:
        import folium
        from streamlit_folium import st_folium
        fmap = folium.Map(location=[44.4268, 26.1025], zoom_start=12)
        for e in events:
            lat = e.get("venue_lat") or 44.4268
            lng = e.get("venue_lng") or 26.1025
            tip = (f"{e['sport']} · {_fmt_dt(e['date'], e['time_window'])} "
                   f"· {e['member_count']} players · 👑 {e['captain_username']}")
            folium.Marker(
                [lat, lng],
                tooltip=tip,
                icon=folium.Icon(color="blue", icon="flag"),
            ).add_to(fmap)
        st_folium(fmap, width=700, height=400)
    except Exception:
        st.info("Map unavailable.")

    st.divider()
    for e in events:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"{e['sport']} — {_fmt_dt(e['date'], e['time_window'])}")
                st.caption(f"👑 {e['captain_username']} · {e['member_count']} players")
            with col2:
                _, max_size = SPORT_SIZES.get(e["sport"], (2, 8))
                if st.button("➕ Request to join", key=f"join_{e['id']}",
                             use_container_width=True, type="primary"):
                    if e["member_count"] >= max_size:
                        st.toast("Event is full!")
                    else:
                        db.add_event_member(e["id"], st.session_state.user_id)
                        st.toast("🎉 You're in! Check My Events.")
                        st.rerun()


# --- main router ---
if not st.session_state.user_id:
    login_screen()
else:
    if "page" not in st.session_state:
        st.session_state.page = "showup"

    with st.sidebar:
        st.title("🏃 ShowUp2Move")
        st.caption(f"👤 {st.session_state.username}")
        st.divider()

        if st.button("🏃 Show Up Today", use_container_width=True):
            st.session_state.page = "showup"
            st.rerun()
        if st.button("🗺️ Discover", use_container_width=True):
            st.session_state.page = "discover"
            st.rerun()
        if st.button("👤 My Profile", use_container_width=True):
            st.session_state.page = "profile"
            st.rerun()
        _pending = db.count_pending_for_user(st.session_state.user_id)
        _events_label = f"🗓️ My Events ({_pending})" if _pending > 0 else "🗓️ My Events"
        if st.button(_events_label, use_container_width=True):
            st.session_state.page = "my_events"
            st.rerun()

        st.divider()
        st.caption("⚡ Admin / Demo")
        admin_date = st.date_input("Match date", value=dt_date.today(), key="admin_date")
        admin_window = st.selectbox("Time window", ["morning", "afternoon", "evening"], key="admin_window")
        if st.button("▶ Run Matching Now", use_container_width=True, type="primary"):
            from matching import run_matching
            with st.spinner("Finding matches..."):
                event_ids = run_matching(admin_date.isoformat(), admin_window)
            if event_ids:
                st.toast(f"🎯 Created {len(event_ids)} event(s)!")
            else:
                st.warning("No matches — not enough players for any sport.")

        st.divider()
        if st.button("🚪 Log out", use_container_width=True):
            for k in ["user_id", "username", "page", "selected_event_id", "ai_sports", "ai_skill"]:
                st.session_state.pop(k, None)
            st.rerun()

    page = st.session_state.get("page", "showup")
    if page == "showup":
        showup_page()
    elif page == "discover":
        discover_page()
    elif page == "profile":
        profile_page()
    elif page == "my_events":
        my_events_page()
    elif page == "event_detail":
        event_detail_page()
    else:
        showup_page()