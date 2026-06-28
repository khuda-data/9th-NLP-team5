import re
import json
import anthropic
from abc import ABC, abstractmethod
from langfuse import observe

from agents.schemas import TrackOutput

_client = anthropic.Anthropic()

_SYSTEM_TEMPLATE = """You are a {instrument} composer for an electronic music system.
Generate a {instrument} sequence for Tone.js playback.
Return ONLY valid JSON with this exact structure:
{{
  "instrument": "{instrument}",
  "notes": [
    {{"time": "0:0:0", "note": "<note>", "duration": "<duration>"}},
    ...
  ]
}}
Time format: "measure:beat:subdivision" (e.g. "0:0:0", "0:2:0", "1:0:0")
Duration format: Tone.js notation ("4n"=quarter, "8n"=eighth, "2n"=half, "1n"=whole)
Generate notes to fill the full structure (intro + main + outro)."""


def _parse_track(text: str) -> TrackOutput:
    try:
        return TrackOutput.model_validate_json(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"Cannot extract track JSON: {text[:200]}")
        return TrackOutput.model_validate_json(match.group())


class BaseInstrumentAgent(ABC):
    @property
    @abstractmethod
    def instrument_name(self) -> str:
        ...

    @property
    def valid_note_range(self) -> tuple[str, str]:
        return ("C1", "C7")

    @observe()
    async def generate(self, state: dict) -> dict:
        system = _SYSTEM_TEMPLATE.format(instrument=self.instrument_name)

        guide = state.get("music_guide", {}).get(self.instrument_name.lower(), "")
        critic_issue = state.get("instrument_issues", {}).get(self.instrument_name.lower(), "")

        prompt = f"""Scale: {state['scale']}
Tempo: {state['tempo']} BPM
Chord progression: {state['chord_progression']}
Song structure: {json.dumps(state['song_structure'])}
Instrument guide: {guide}
Note range: {self.valid_note_range[0]} to {self.valid_note_range[1]}

IMPORTANT: Output at most 32 notes total. Keep the JSON compact and ensure it is complete and valid (close every bracket)."""

        if critic_issue:
            prompt += f"\n\nPrevious issue to fix: {critic_issue}"

        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        result = _parse_track(response.content[0].text)
        return result.model_dump()
