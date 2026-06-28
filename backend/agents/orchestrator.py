from state import MusicState

QUALITY_THRESHOLD = 0.75


def orchestrator_router(state: MusicState) -> str:
    """Critic 결과를 보고 재시도 vs 완료 결정."""
    if state["quality_score"] >= QUALITY_THRESHOLD:
        return "finalize"
    if state["retry_count"] >= state["max_retries"]:
        return "finalize"
    return "retry"


async def increment_retry(state: MusicState) -> dict:
    """재시도 카운터 증가. 문제 있는 악기만 target으로 설정."""
    issues = state.get("instrument_issues", {})
    faulty = list(issues.keys()) if issues else None  # None = 전체 재생성
    return {
        "retry_count": state["retry_count"] + 1,
        "target_instruments": faulty,
        "tracks": {},  # 재생성 시 트랙 초기화
    }


async def finalize(state: MusicState) -> dict:
    """최종 출력 조합."""
    return {
        "final_output": {
            "mood": {
                "keywords": state["mood_keywords"],
                "tempo": state["tempo"],
                "scale": state["scale"],
            },
            "chord_progression": state["chord_progression"],
            "tracks": list(state["tracks"].values()),
            "quality_score": state["quality_score"],
        }
    }
