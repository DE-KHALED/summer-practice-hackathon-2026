import json
import streamlit as st
from google import genai

# Configuration
SPORTS_LIST = ["Football", "Basketball", "Tennis", "Volleyball",
               "Running", "Cycling", "Padel", "Swimming"]

# Ordered by most likely to have free quota / stability
MODEL_CANDIDATES = [
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
]

def _get_client():
    """Initializes the Gemini client using Streamlit secrets."""
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def _extract_json(text: str):
    """Cleans and parses JSON from AI string output."""
    clean_text = text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

def _generate_with_retry(client, prompt: str):
    """Loops through model candidates to find one with available quota."""
    last_err = None
    for model in MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text
        except Exception as e:
            last_err = e
            # If it's not a quota issue (429), stop and report the real bug
            if "429" not in str(e) and "RESOURCE_EXHAUSTED" not in str(e):
                break
            continue
    raise last_err or RuntimeError("All models exhausted or unavailable.")

@st.cache_data(show_spinner="AI is analyzing the bio...")
def extract_sports_from_bio(bio: str):
    """Analyzes a user bio to determine sports and skill level."""
    if not bio.strip():
        return None
    
    client = _get_client()
    if not client:
        st.error("Gemini API key not configured.")
        return None

    prompt = f"""Extract sports interests and skill level from this bio.
    Bio: "{bio}"
    Available sports: {", ".join(SPORTS_LIST)}
    Skill levels: beginner, intermediate, advanced

    Return ONLY valid JSON:
    {{"sports": ["Sport1"], "skill_level": "beginner"}}
    """

    try:
        text = _generate_with_retry(client, prompt)
        data = _extract_json(text)
        
        # Validation & Cleanup
        detected_sports = [s for s in data.get("sports", []) if s in SPORTS_LIST]
        skill = data.get("skill_level", "beginner").lower()
        if skill not in ["beginner", "intermediate", "advanced"]:
            skill = "beginner"
            
        return {"sports": detected_sports, "skill_level": skill}
    except Exception as e:
        st.warning(f"AI Extraction unavailable: {e}")
        return {"sports": [], "skill_level": "beginner"}

@st.cache_data(show_spinner="Calculating group chemistry...")
def compute_event_compatibility(members):
    """Calculates a compatibility score for a group of users."""
    if not members or len(members) < 2:
        return None

    client = _get_client()
    if not client:
        return None

    member_summary = "\n".join([
        f"- {m['username']}: {m['skill_level']}, {m['sports']}" for m in members
    ])

    prompt = f"""Rate the compatibility (0-100) for this sports group:
    {member_summary}

    Return ONLY valid JSON:
    {{"score": 85, "reason": "Short explanation.", "best_pairs": ["user1 & user2"]}}
    """

    try:
        text = _generate_with_retry(client, prompt)
        data = _extract_json(text)
        return {
            "score": max(0, min(100, int(data.get("score", 50)))),
            "reason": data.get("reason", "Good match."),
            "best_pairs": data.get("best_pairs", [])[:2]
        }
    except Exception:
        return {"score": 50, "reason": "Could not calculate score.", "best_pairs": []}