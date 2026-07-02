from __future__ import annotations
from typing import Any, Optional, Annotated
from typing_extensions import TypedDict


def _merge_tracks(a: dict, b: dict) -> dict:
    return {**a, **b}


class MusicState(TypedDict):
    # --- 입력 ---
    image_base64: Optional[str]       # base64 인코딩된 이미지
    user_text: Optional[str]          # 사용자 텍스트 프롬프트
    target_instruments: Optional[list[str]]  # 부분 재생성 시 지정 (None = 전체)

    # --- Mood Agent 출력 ---
    mood_keywords: list[str]          # e.g. ["dark", "melancholic"]
    tempo: int                        # BPM
    scale: str                        # e.g. "A Minor"
    color_profile: str

    # --- Music Agent 출력 ---
    chord_progression: list[str]      # e.g. ["Am", "F", "C", "G"]
    song_structure: dict              # {intro, main, outro}
    music_guide: dict                 # 악기별 연주 힌트

    # --- Instrument Sub-Agents 출력 
    # 
    tracks: Annotated[dict[str, Any], _merge_tracks]

    # --- Critic Agent 출력 ---
    critic_feedback: Optional[str]
    quality_score: float              # 0.0 ~ 1.0
    instrument_issues: dict           # {instrument: issue_description}

    # --- 루프 제어 ---
    retry_count: int
    max_retries: int
    final_output: Optional[dict]
