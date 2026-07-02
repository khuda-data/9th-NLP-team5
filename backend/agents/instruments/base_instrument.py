import re
import json
import random
import anthropic
from abc import ABC, abstractmethod
from langfuse import observe, get_client

from agents.schemas import TrackOutput
from logger import get_logger

_client = anthropic.AsyncAnthropic()
_lf = get_client()
logger = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

_GROOVE_HINTS: dict[str, list[str]] = {
    "bass": [
        "Walk between chord roots using chromatic passing tones. Add syncopated 16th-note fills at bar ends. Rest on beat 3 every other bar.",
        "Offbeat feel: rest on beat 1, punch on the 'and' of 1, root on beat 2. Create forward momentum with 8th-note runs.",
        "Mix sustained half-note roots with punchy 8th-note riffs on the backbeat. End phrases with a quick descending run.",
        "Reggae-style: land on the 'and' of beat 2 and 4, skip the downbeats. Use ghost notes between main hits.",
    ],
    "kick": [
        "Avoid plain beats-1-and-3. Use: beat 1, 'and' of 2, beat 3.5. Add a ghost kick on the 'and' of 4.",
        "Half-time feel in intro (beats 1 and 3 only), switch to syncopated 16th-note accents in main section.",
        "Four-on-the-floor in main but drop the beat-3 kick every 4 bars for tension. Re-enter on beat 1 with emphasis.",
        "Polyrhythmic: accent every 3rd 8th note within the 4/4 bar. Creates a 3-against-4 feel.",
    ],
    "pluck": [
        "Arpeggiate chords upward, then add a descending chromatic run at the end of each 2-bar phrase.",
        "Staccato chord stabs on upbeats ('and' positions only). Leave silence between every hit — space is musical.",
        "Combine sustained chord hits (2n) with single-note melodic fills (8n). Vary rhythm: some 8th, some 16th.",
        "Play an ascending arpeggio on beat 1, then a syncopated single note on the 'and' of 3. Repeat with variation.",
    ],
    "brass": [
        "Short, punchy staccato stabs on upbeats only. Leave 2-bar rests between phrases for dramatic impact.",
        "Call-and-response: 1-bar melodic phrase (3-4 notes), then 1 full bar of silence. Build to fuller hits in outro.",
        "Sforzando accent on beat 2 or the 'and' of 3 — land notes where the listener doesn't expect them.",
        "Long swell into the main section (whole note crescendo), then switch to short 8th-note punches on the backbeat.",
    ],
    "strings": [
        "Sustain whole-note chord tones for 2 bars, then play a 4-note chromatic countermelody line in bar 3.",
        "Tremolo effect: rapid 16th-note repetitions on one pitch for tension, then resolve to a long held chord.",
        "Pizzicato feel: short 8th-note chord hits on beat 1 and 3, contrasted with one long sustained phrase per section.",
        "Sparse single sustained notes in the intro, build to full chord swells in main, fade back in outro.",
    ],
}

_SYSTEM_TEMPLATE = """You are a {instrument} composer for an electronic music production.
Generate a MUSICAL, NON-MECHANICAL, EXPRESSIVE {instrument} sequence for Tone.js.

CRITICAL rules for a human, organic feel:
- Use SILENCE intentionally — not every beat needs a note. Rests are musical.
- MIX note durations: combine 1n, 2n, 4n, 8n, 16n in the same track.
- Add SYNCOPATION: place some notes on the 'and' of beats (subdivision 2), not only on downbeats.
- AVOID repeating the same bar pattern more than twice in a row.
- Each section (intro / main / outro) should have a distinct feel or density.

Return ONLY a single line of compact JSON (NO newlines, NO indentation, NO spaces after colons/commas):
{{"instrument":"{instrument}","notes":[{{"time":"measure:beat:subdivision","note":"<pitch>","duration":"<duration>"}},...]}}
Time format: "measure:beat:subdivision"  (e.g. "0:0:0"=bar0 beat0, "0:1:2"=bar0 beat1 sub2)
Duration: Tone.js notation  (1n=whole, 2n=half, 4n=quarter, 8n=eighth, 16n=sixteenth)"""


def _parse_track(text: str) -> TrackOutput:
    try:
        return TrackOutput.model_validate_json(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"Cannot extract track JSON: {text[:200]}")
        raw = match.group()
        try:
            return TrackOutput.model_validate_json(raw)
        except Exception:
            # JSON truncated mid-array: find last complete note object and close the structure
            last_complete = raw.rfind("},")
            if last_complete == -1:
                last_complete = raw.rfind("}")
            if last_complete > 0:
                trimmed = raw[: last_complete + 1] + "]}"
                try:
                    return TrackOutput.model_validate_json(trimmed)
                except Exception:
                    pass
            raise ValueError(f"Cannot parse track JSON (truncated?): {text[:300]}")


# 추상 클래스 정의: BaseInstrumentAgent
class BaseInstrumentAgent(ABC):
    @property
    @abstractmethod
    def instrument_name(self) -> str: ...

    @property
    def valid_note_range(self) -> tuple[str, str]:
        return ("C1", "C7")

    @observe(name="generate")
    async def generate(self, state: dict) -> dict:
        instrument = self.instrument_name
        system = _SYSTEM_TEMPLATE.format(instrument=instrument)

        guide = state.get("music_guide", {}).get(instrument.lower(), "")
        critic_issue = state.get("instrument_issues", {}).get(instrument.lower(), "")
        retry = state.get("retry_count", 0)

        hints = _GROOVE_HINTS.get(instrument.lower(), [])
        groove_hint = random.choice(hints) if hints else ""

        logger.info(
            "generate start | instrument=%s retry=%d groove='%s'",
            instrument, retry, groove_hint[:60],
        )

        prompt = f"""Scale: {state['scale']}
Tempo: {state['tempo']} BPM
Chord progression: {state['chord_progression']}
Song structure: {json.dumps(state['song_structure'])}
Instrument guide: {guide}
Note range: {self.valid_note_range[0]} to {self.valid_note_range[1]}
Groove style: {groove_hint}

Generate 20-25 notes maximum. Use varied durations and include rests (gaps between notes).
Output compact single-line JSON only — no newlines, no indentation."""

        if critic_issue:
            prompt += f"\n\nPrevious issue to fix: {critic_issue}"

        response = await _client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        _lf.update_current_generation(
            name=f"generate:{instrument.lower()}",
            model=_MODEL,
            usage_details={
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            },
        )

        result = _parse_track(response.content[0].text)

        logger.info(
            "generate done | instrument=%s notes=%d tokens in=%d out=%d",
            instrument, len(result.notes),
            response.usage.input_tokens, response.usage.output_tokens,
        )

        return result.model_dump()
