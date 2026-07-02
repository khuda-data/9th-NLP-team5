from state import MusicState

QUALITY_THRESHOLD = 0.8


def orchestrator_router(state: MusicState) -> str:
    if state["quality_score"] >= QUALITY_THRESHOLD:
        return "finalize"
    if state["retry_count"] >= state["max_retries"]:
        return "finalize"
    return "retry"


async def increment_retry(state: MusicState) -> dict:
    issues = state.get("instrument_issues", {})
    faulty = list(issues.keys()) if issues else None  # None = 전체 재생성
    return {
        "retry_count": state["retry_count"] + 1,
        "target_instruments": faulty,
        # NOTE: tracks 는 merge reducer 라 여기서 {} 를 줘도 초기화되지 않음(의도된 동작).
        #       문제 악기만 target 으로 재생성되어 기존 정상 트랙 위에 덮어쓰기 merge 됨.
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
