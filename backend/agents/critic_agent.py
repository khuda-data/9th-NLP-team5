import json
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langfuse import observe

from state import MusicState
from agents.schemas import CriticOutput
from logger import get_logger

logger = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_llm = ChatAnthropic(model=_MODEL, max_tokens=512)
_structured_llm = _llm.with_structured_output(CriticOutput)

_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 AI 음악 생성 시스템의 합리적이고 관대한 음악 평론가입니다.\n"
        "예술에는 정답이 없으므로, 주관적인 멜로디의 아름다움보다는 '최소한의 기술적 결함'만 검사합니다.\n\n"

        " [채점 방식 - 감점제 적용]\n"
        "기본 점수 1.0점에서 시작하여 아래 결격 사유가 있을 때만 각 0.1 ~ 0.15점씩 감점하세요.\n"
        "1. 심각한 화성학적 이탈 (지정된 Scale/Chord와 완전히 불협화음을 이루는 노트가 3개 이상인 경우)\n"
        "2. 리듬 붕괴 (템포에 맞지 않거나 Tone.js가 인식할 수 없는 박자 포맷인 경우)\n"
        "3. 음역대 위반 (Bass가 지나치게 고음을 치거나 Strings가 너무 저음을 치는 경우)\n\n"

        " [주의 사항]\n"
        "- 문제가 있는 악기나 잘 어울리지 않는 악기는 정확히 'instrument_issues'에 소문자로 기록하세요."
    ),
    (
        "human",
        """Scale: {scale}
Tempo: {tempo} BPM
Chord progression: {chords}
Previous feedback: {prev_feedback}

Generated tracks:
{tracks_json}

Score 0.0-1.0. List instrument_issues only for instruments that have problems.""",
    ),
])

_chain = _prompt | _structured_llm


@observe(name="critic_agent")
async def critic_agent(state: MusicState) -> dict:
    retry = state.get("retry_count", 0)
    logger.info(
        "critic_agent start | retry=%d scale=%s tempo=%d tracks=%s",
        retry, state["scale"], state["tempo"],
        list(state.get("tracks", {}).keys()),
    )

    result: CriticOutput = await _chain.ainvoke({
        "scale": state["scale"],
        "tempo": state["tempo"],
        "chords": ", ".join(state["chord_progression"]),
        "prev_feedback": state.get("critic_feedback") or "None",
        "tracks_json": json.dumps(state.get("tracks", {}), indent=2),
    })

    issues = {str(k).lower(): v for k, v in (result.instrument_issues or {}).items()}

    logger.info(
        "critic_agent done | score=%.2f issues=%s feedback=%s",
        result.quality_score,
        list(issues.keys()) or "none",
        (result.feedback or "")[:80],
    )

    return {
        "quality_score": result.quality_score,
        "critic_feedback": result.feedback,
        "instrument_issues": issues,
    }
