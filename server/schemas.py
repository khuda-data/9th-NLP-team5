"""
schemas.py
프론트엔드 <-> 백엔드가 주고받는 데이터의 "정해진 모양".

여기 정의가 곧 프론트 담당자(React/TS)와의 약속이다.
프론트는 응답으로 받은 MusicState 의 tracks 를 Tone.js 로 그대로 재생하면 된다.
"""

from typing import Any, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------
# 1) 음 하나 (Tone.js 가 바로 재생할 수 있는 형태)
# ---------------------------------------------------------------
class Note(BaseModel):
    # Tone.js Transport 시간 표기 "bar:beat:sixteenth"  예: "0:0:0", "1:2:0"
    time: str
    # 음 높이. 단음 "C4", 화음 ["C4","E4","G4"], 타악기(킥 등)는 None
    note: Optional[Union[str, list[str]]] = None
    # 음 길이.  "4n"(4분), "8n"(8분), "2n"(2분) 등
    duration: str = "8n"
    # 세기 0.0 ~ 1.0
    velocity: float = 0.8


# ---------------------------------------------------------------
# 2) 트랙 하나 = 악기 하나 (Bass, Kick, Pluck, Brass, Strings ...)
# ---------------------------------------------------------------
class Track(BaseModel):
    instrument: str                 # "bass", "kick" ...
    synth: str                      # Tone.js 신스 종류 힌트 (프론트가 이걸로 악기 생성)
    notes: list[Note] = Field(default_factory=list)


# ---------------------------------------------------------------
# 3) 마스터(오케스트레이터)가 모든 에이전트에 강제하는 공통 제약
#    -> 이게 있어야 악기들이 서로 안 어긋난다 (기획서: 통일성 확보)
# ---------------------------------------------------------------
class Constraints(BaseModel):
    key: str = "C minor"
    bpm: int = 120
    time_signature: str = "4/4"
    chord_progression: list[str] = Field(default_factory=lambda: ["Cm", "Ab", "Eb", "Bb"])
    bars: int = 4                   # 곡 길이(마디 수)


# ---------------------------------------------------------------
# 4) Mood Agent 가 이미지/텍스트에서 뽑아내는 분위기 정보
# ---------------------------------------------------------------
class Mood(BaseModel):
    keywords: list[str] = Field(default_factory=list)   # ["calm", "nostalgic"]
    energy: float = 0.5             # 0(잔잔) ~ 1(격렬)
    description: str = ""


# ---------------------------------------------------------------
# 5) Critic Agent 의 평가 보고서
# ---------------------------------------------------------------
class CriticReport(BaseModel):
    score: float = 0.0              # 0 ~ 1 (높을수록 좋음)
    dissonance: float = 0.0         # 불협화도 (낮을수록 좋음)
    feedback: dict[str, str] = Field(default_factory=dict)   # {"bass": "너무 단조로움", ...}
    needs_revision: list[str] = Field(default_factory=list)  # 재생성이 필요한 트랙 이름들


# ---------------------------------------------------------------
# 6) 곡 전체 상태(State). 부분 갱신의 단위가 된다.
#    프론트는 이 객체를 들고 있다가 수정 요청 때 그대로 다시 보낸다.
# ---------------------------------------------------------------
class MusicState(BaseModel):
    constraints: Constraints = Field(default_factory=Constraints)
    mood: Mood = Field(default_factory=Mood)
    tracks: dict[str, Track] = Field(default_factory=dict)
    critic: Optional[CriticReport] = None


# ===============================================================
# 요청(Request) 모양
# ===============================================================
class GenerateRequest(BaseModel):
    # 이미지(base64) 또는 텍스트 프롬프트 중 하나로 시작
    image_base64: Optional[str] = None
    prompt: Optional[str] = None
    # 만들 악기들. 기획서의 악기별 에이전트.
    instruments: list[str] = Field(default_factory=lambda: ["bass", "kick", "pluck", "brass", "strings"])
    options: dict[str, Any] = Field(default_factory=dict)


class ReviseRequest(BaseModel):
    # 현재 곡 상태(프론트가 들고 있던 것)를 그대로 보냄 -> 누적 State
    state: MusicState
    # 다시 만들 트랙들만 지정 -> 그 트랙만 재실행 (부분 갱신)
    targets: list[str]
    # 선택: "베이스를 더 잔잔하게" 같은 사용자 지시
    instruction: Optional[str] = None


# ===============================================================
# 응답(Response) 모양
# ===============================================================
class GenerateResponse(BaseModel):
    ok: bool = True
    state: MusicState
    timing_ms: dict[str, float] = Field(default_factory=dict)  # 단계별 소요시간(평가지표용)
