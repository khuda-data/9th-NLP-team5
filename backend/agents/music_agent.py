from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langfuse import observe
from langfuse.langchain import CallbackHandler

from state import MusicState
from agents.schemas import MusicOutput
from rag.music_kb import query_music_knowledge
from logger import get_logger
import cache

logger = get_logger(__name__)

_MODEL = "claude-sonnet-4-6"
_llm = ChatAnthropic(model=_MODEL, max_tokens=2048)
_structured_llm = _llm.with_structured_output(MusicOutput)

_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a professional music composer. "
        "Given mood analysis and relevant music theory, design a complete song structure. "
        "Be creative and avoid generic, predictable progressions — vary the structure between sections.",
    ),
    (
        "human",
        """Mood keywords: {mood_keywords}
Scale: {scale}
Tempo: {tempo} BPM
Color profile: {color_profile}

Relevant music theory:
{rag_context}

Design chord_progression (4-6 chords MAX), song_structure (intro/main/outro, TOTAL 12-16 bars only),
and music_guide with specific, VARIED instructions for each instrument (bass, kick, pluck, brass, strings).
Each instrument guide must describe distinct rhythmic patterns, articulations, and dynamics — not generic advice.
Keep total song length to 12-16 bars so playback is roughly 30-50 seconds.""",
    ),
])

_chain = _prompt | _structured_llm


@observe(name="music_agent")
async def music_agent(state: MusicState) -> dict:
    scale = state["scale"]
    mood_keywords = state["mood_keywords"]

    logger.info(
        "music_agent start | scale=%s tempo=%d keywords=%s",
        scale, state["tempo"], mood_keywords,
    )

    cache_key = cache.make_music_key(scale, mood_keywords)
    cached = cache.get(cache_key)
    if cached:
        logger.info("⭐music_agent cache HIT | key=%s", cache_key)
        return cached

    rag_context = query_music_knowledge(scale=scale, mood_keywords=mood_keywords)

    result: MusicOutput = await _chain.ainvoke(
        {
            "mood_keywords": ", ".join(mood_keywords),
            "scale": scale,
            "tempo": state["tempo"],
            "color_profile": state["color_profile"],
            "rag_context": rag_context,
        },
        config={"callbacks": [CallbackHandler()]},
    )

    output = result.model_dump()
    cache.set(cache_key, output)

    logger.info(
        "music_agent done | chords=%s structure_keys=%s (cached)",
        result.chord_progression,
        list(result.song_structure.keys()),
    )
    return output
