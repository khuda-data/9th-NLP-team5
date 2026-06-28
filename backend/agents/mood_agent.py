import re
import json
import anthropic
from langfuse.decorators import observe

from state import MusicState
from agents.schemas import MoodOutput

_client = anthropic.Anthropic()

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
        # JSON이 다른 텍스트에 묻혀 있을 경우 추출
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
                "media_type": "image/jpeg",
                "data": state["image_base64"],
            },
        })

    text = state.get("user_text") or ""
    content.append({
        "type": "text",
        "text": f"Analyze this input for musical mood.\n{text}" if text else "Analyze this image for musical mood.",
    })

    response = _client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=512,
        system=_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )

    result = _parse_mood(response.content[0].text)
    return result.model_dump()
