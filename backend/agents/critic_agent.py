import json
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langfuse.decorators import observe

from state import MusicState
from agents.schemas import CriticOutput

_llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", max_tokens=512)
_structured_llm = _llm.with_structured_output(CriticOutput)

_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a music quality critic for an AI music generation system. "
        "Evaluate generated tracks for: musical coherence with the scale and chords, "
        "rhythmic consistency with tempo, Tone.js format validity (time/note/duration), "
        "and instrument-appropriate note ranges.",
    ),
    (
        "human",
        """Scale: {scale}
Tempo: {tempo} BPM
Chord progression: {chords}
Previous feedback: {prev_feedback}

Generated tracks:
{tracks_json}

Score 0.0–1.0. List instrument_issues only for instruments that have problems.""",
    ),
])

_chain = _prompt | _structured_llm


@observe(name="critic_agent")
async def critic_agent(state: MusicState) -> dict:
    result: CriticOutput = await _chain.ainvoke({
        "scale": state["scale"],
        "tempo": state["tempo"],
        "chords": ", ".join(state["chord_progression"]),
        "prev_feedback": state.get("critic_feedback") or "None",
        "tracks_json": json.dumps(state.get("tracks", {}), indent=2),
    })

    return {
        "quality_score": result.quality_score,
        "critic_feedback": result.feedback,
        "instrument_issues": result.instrument_issues,
    }
