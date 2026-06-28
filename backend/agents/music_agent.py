from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langfuse import observe

from state import MusicState
from agents.schemas import MusicOutput
from rag.music_kb import query_music_knowledge

_llm = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=2048)
_structured_llm = _llm.with_structured_output(MusicOutput)

_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a professional music composer. "
        "Given mood analysis and relevant music theory, design a complete song structure.",
    ),
    (
        "human",
        """Mood keywords: {mood_keywords}
Scale: {scale}
Tempo: {tempo} BPM
Color profile: {color_profile}

Relevant music theory:
{rag_context}

Design chord_progression, song_structure (intro/main/outro with bars and description),
and music_guide with specific instructions for each instrument (bass, kick, pluck, brass, strings).""",
    ),
])

_chain = _prompt | _structured_llm


@observe(name="music_agent")
async def music_agent(state: MusicState) -> dict:
    rag_context = query_music_knowledge(
        scale=state["scale"],
        mood_keywords=state["mood_keywords"],
    )

    result: MusicOutput = await _chain.ainvoke({
        "mood_keywords": ", ".join(state["mood_keywords"]),
        "scale": state["scale"],
        "tempo": state["tempo"],
        "color_profile": state["color_profile"],
        "rag_context": rag_context,
    })

    return result.model_dump()
