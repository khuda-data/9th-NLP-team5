import json
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langfuse import observe
from langfuse.langchain import CallbackHandler

from state import MusicState
from agents.schemas import CriticOutput
from logger import get_logger

logger = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

_llm = ChatAnthropic(model=_MODEL, max_tokens=512, temperature=0.1)
_structured_llm = _llm.with_structured_output(CriticOutput)

_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 AI 음악 생성 시스템의 음악 평론가입니다.\n"
        "예술에는 정답이 없으므로, '기술적 결함'만 검사합니다.\n\n"

        " [1단계: 결함 나열 - 반드시 먼저 수행]\n"
        "아래 4개 카테고리 각각에 대해 결함이 있는지 확인하고, "
        "있다면 defects 리스트에 category/severity/instrument/description을 "
        "모두 채워서 추가하세요. 결함이 하나도 없으면 defects를 빈 리스트로 두세요.\n"
        "1. harmony (화성 이탈): Scale/Chord와 불협화음인 노트가 있는가\n"
        "2. rhythm (리듬 문제): 템포/박자 포맷 오류\n"
        "3. range (음역대 위반): 악기별 적정 음역 초과\n"
        "4. integrity (데이터 무결성): 빈 note 값, 파싱 불가능한 값 등 기술적 결함\n\n"

 
        " [2단계: 점수 매핑 - defects 리스트를 보고 아래 구간에서만 고를 것]\n"
        "- major 0개, minor 0~1개 → 0.85~1.0\n"
        "- minor 2개 이상, major 0개 → 0.6~0.84\n"
        "- major 1개 → 0.3~0.59\n"
        "- major 2개 이상 → 0.0~0.29\n\n"

        " [출력 시 주의]\n"
        "- quality_score는 반드시 defects 리스트의 내용과 논리적으로 일치해야 합니다 "
        "(예: defects가 비어있는데 quality_score가 0.5 미만이면 안 됩니다).\n"
        "- feedback에는 defects 내용을 사람이 읽기 쉽게 요약하세요.\n"
        "- instrument_issues에는 문제 있는 악기만 소문자로 기록하세요."
    ),
    (
        "human",
        """Scale: {scale}
Tempo: {tempo} BPM
Chord progression: {chords}
Previous feedback: {prev_feedback}

Generated tracks:
{tracks_json}

1단계(defects)부터 채운 뒤, 그 결과에 따라 2단계(quality_score)를 결정하세요.""",
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

    result: CriticOutput = await _chain.ainvoke(
        {
            "scale": state["scale"],
            "tempo": state["tempo"],
            "chords": ", ".join(state["chord_progression"]),
            "prev_feedback": state.get("critic_feedback") or "None",
            "tracks_json": json.dumps(state.get("tracks", {}), indent=2),
        },
        config={"callbacks": [CallbackHandler()]},
    )

    issues = {str(k).lower(): v for k, v in (result.instrument_issues or {}).items()}

    has_major = any(d.severity == "major" for d in result.defects)
    has_defects = len(result.defects) > 0
    if not has_defects and result.quality_score < 0.85:
        logger.warning(
            "critic_agent 모순 감지 | defects=0인데 score=%.2f (규칙상 0.85 이상이어야 함)",
            result.quality_score,
        )
    elif has_major and result.quality_score >= 0.6:
        logger.warning(
            "critic_agent 모순 감지 | major 결함 있는데 score=%.2f (규칙상 0.6 미만이어야 함)",
            result.quality_score,
        )

    logger.info(
        "critic_agent done | score=%.2f defects=%d issues=%s feedback=%s",
        result.quality_score,
        len(result.defects),
        list(issues.keys()) or "none",
        (result.feedback or "")[:80],
    )

    return {
        "quality_score": result.quality_score,
        "critic_feedback": result.feedback,
        "instrument_issues": issues,
    }