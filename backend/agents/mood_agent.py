import re
import json
import base64
import anthropic
from langfuse import observe

from state import MusicState
from agents.schemas import MoodOutput

_client = anthropic.Anthropic()


def _detect_media_type(image_b64: str) -> str:
    """Detect real image type from base64 magic bytes (avoids hardcoded-jpeg bug)."""
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
    return "image/jpeg"  # fallback when unknown

_SYSTEM = """You are a music mood analyst. Analyze the given image and/or text and extract musical characteristics.
Return ONLY valid JSON with this exact structure:
{
  "mood_keywords": ["keyword1", "keyword2", "keyword3"],
  "tempo": <integer BPM 60-180>,
  "scale": "<root> <mode>",
  "color_profile": "<brief color description>"
}"""


def _parse_mood(text: str) -> MoodOutput:
    try:
        return MoodOutput.model_validate_json(text)
    except Exception:
        # extract JSON if it is embedded in surrounding text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"Cannot extract JSON from response: {text[:200]}")
        return MoodOutput.model_validate_json(match.group())


@observe(name="mood_agent")
async def mood_agent(state: MusicState) -> dict:
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
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )

    result = _parse_mood(response.content[0].text)
    return result.model_dump()
