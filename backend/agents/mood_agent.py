import re
import base64
import anthropic
from langfuse import observe, get_client

from state import MusicState
from agents.schemas import MoodOutput
from logger import get_logger

_client = anthropic.Anthropic()
_lf = get_client()
logger = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"


def _detect_media_type(image_b64: str) -> str:
    try:
        head = base64.b64decode(image_b64[:24], validate=False)
    except Exception:
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


_SYSTEM = """You are an expert Music Mood Analyst and Ethnomusicologist. 
Your sole objective is to convert a visual/textual theme into highly precise, production-ready musical metadata.

[CRITICAL SCHEMA RULES]
1. "mood_keywords": Must contain EXACTLY between 3 and 5 definitive mood/vibe keywords. Do NOT exceed 8 items under any circumstances.
2. "tempo": An integer strictly between 60 and 180 BPM based on the movement/energy of the input.
3. "scale": Specify the musical scale in "<Root_Note> <Scale_Type>" format.
   - Root_Note: C, C#, D, D#, E, F, F#, G, G#, A, A#, B
   - Scale_Type: To enforce musical diversity, choose dynamically from: [major, minor, dorian, phrygian, mixolydian, lydian, harmonic_minor]. Do NOT default to 'C major' unless explicitly relevant.
4. "color_profile": A brief description of the dominant visual or emotional color palette (e.g., "neon cyberpunk purple", "faded acoustic warm brown").

[OUTPUT FORMAT]
- Return ONLY the raw, minified JSON object.
- Absolutely NO conversational filler, NO markdown formatting (do NOT wrap in ```json), NO trailing text.
- Your output must be directly parseable by an application backend.

Example Output:
{{"mood_keywords":["retro","sophisticated","urban"],"tempo":112,"scale":"D dorian","color_profile":"neon purple"}}"""


def _parse_mood(text: str) -> MoodOutput:
    try:
        return MoodOutput.model_validate_json(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"Cannot extract JSON from response: {text[:200]}")
        return MoodOutput.model_validate_json(match.group())


@observe(name="mood_agent")
async def mood_agent(state: MusicState) -> dict:
    has_image = bool(state.get("image_base64"))
    has_text = bool(state.get("user_text"))
    logger.info("mood_agent start | image=%s text=%s", has_image, has_text)

    content: list[dict] = []
    if state.get("image_base64"):
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": _detect_media_type(state["image_base64"]),
                "data": state["image_base64"],
            },
        })

    text = state.get("user_text") or ""
    content.append({
        "type": "text",
        "text": f"Analyze this input for musical mood.\n{text}" if text else "Analyze this image for musical mood.",
    })

    response = _client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )

    _lf.update_current_generation(
        model=_MODEL,
        usage_details={
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        },
    )

    result = _parse_mood(response.content[0].text)

    logger.info(
        "mood_agent done | keywords=%s tempo=%d scale=%s | tokens in=%d out=%d",
        result.mood_keywords, result.tempo, result.scale,
        response.usage.input_tokens, response.usage.output_tokens,
    )
    return result.model_dump()
