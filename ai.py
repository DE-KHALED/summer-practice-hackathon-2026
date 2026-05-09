import json
import streamlit as st

SPORTS_LIST = ["Football", "Basketball", "Tennis", "Volleyball",
               "Running", "Cycling", "Padel", "Swimming"]

# Try models in order — first one that doesn't 429 wins
MODEL_CANDIDATES = [
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
]


def _get_client():
    """Returns a configured Gemini client, or None if unavailable."""
    try:
        from google import genai
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            return None
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Gemini init error: {e}")
        return None


def _extract_json(text: str):
    """Strip code fences and parse JSON from model output."""
    text = text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def _generate(client, prompt: str):
    """Try each model until one works (handles per-model quota errors)."""
    last_err = None
    for model in MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            last_err = e
            err_str = str(e)
            # Only fall through on quota/rate-limit errors; raise on real bugs
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                continue
            raise
    # All models exhausted
    raise last_err if last_err else RuntimeError("No models available")


def extract_sports_from_bio(bio: str):
    """Returns dict {sports: [...], skill_level: '...'} or None on failure."""
    if not bio.strip():
        return None
    client = _get_client()
    if client is None:
        return None
    try:
        prompt = f"""Extract sports interests and skill level from this bio.
Bio: "{bio}"

Available sports: {", ".join(SPORTS_LIST)}
Skill levels: beginner, intermediate, advanced

Return ONLY valid JSON, no other text, no markdown:
{{"sports": ["Sport1", "Sport2"], "skill_level": "beginner"}}

Only include sports from the available list. Default skill to "beginner" if unclear."""

        text = _generate(client, prompt)
        data = _extract_json(text)
        data["sports"] = [s for s in data.get("sports", []) if s in SPORTS_LIST]
        if data.get("skill_level") not in ["beginner", "intermediate", "advanced"]:
            data["skill_level"] = "beginner"
        return data
    except Exception as e:
        st.error(f"AI extract error: {type(e).__name__}: {e}")
        return None


def compute_event_compatibility(members):
    """
    members: list of dicts with keys username, bio, sports, skill_level
    Returns: {"score": int, "reason": str, "best_pairs": [str, ...]} or None
    """
    if not members or len(members) < 2:
        return None
    client = _get_client()
    if client is None:
        return None
    try:
        member_text = "\n".join([
            f"- {m['username']}: skill={m['skill_level']}, sports={m['sports']}, bio=\"{m['bio'][:200]}\""
            for m in members
        ])
        prompt = f"""Rate the compatibility of this sports group from 0 to 100,
based on shared interests, similar skill levels, and bio vibes.

Group:
{member_text}

Return ONLY valid JSON, no markdown:
{{"score": 87, "reason": "one short sentence", "best_pairs": ["user1 & user2"]}}

Score 0-100. Pick 1-2 best pairs. Reason must be one short sentence."""

        text = _generate(client, prompt)
        data = _extract_json(text)
        score = int(data.get("score", 50))
        score = max(0, min(100, score))
        return {
            "score": score,
            "reason": data.get("reason", "Group looks reasonable."),
            "best_pairs": data.get("best_pairs", [])[:2],
        }
    except Exception as e:
        st.error(f"AI compatibility error: {type(e).__name__}: {e}")
        return None