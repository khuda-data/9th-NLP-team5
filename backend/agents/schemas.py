from pydantic import BaseModel, Field
from typing import Literal


class MoodOutput(BaseModel):
    mood_keywords: list[str] = Field(min_length=1)
    tempo: int = Field(ge=60, le=180)
    scale: str
    color_profile: str


class NoteEvent(BaseModel):
    time: str       # Tone.js format: "measure:beat:subdivision"
    note: str = Field(..., pattern=r"^[A-G]#?[0-7]$")
    duration: str   # e.g. "4n", "8n", "2n"


class TrackOutput(BaseModel):
    instrument: str
    notes: list[NoteEvent] = Field(min_length=1)


class MusicOutput(BaseModel):
    chord_progression: list[str] = Field(min_length=2)
    song_structure: dict = Field(default_factory=dict)   # {intro, main, outro}
    music_guide: dict = Field(default_factory=dict)       # {bass, kick, pluck, brass, strings}



# Pydantic이 이 필드 자체를 타입 레벨에서 검증해줘요.
DefectCategory = Literal["harmony", "rhythm", "range", "integrity"]
DefectSeverity = Literal["minor", "major"]


class DefectItem(BaseModel):
    category: DefectCategory = Field(
        description="어느 카테고리의 결함인지 (harmony/rhythm/range/integrity)"
    )
    severity: DefectSeverity = Field(
        description="심각도. minor=경미, major=심각"
    )
    instrument: str = Field(
        description="문제가 발생한 악기명 "
    )
    description: str = Field(
        description="구체적으로 무엇이 문제인지 서술 (예: '5마디 Bass가 B0로 옥타브 범위 이탈')"
    )


class CriticOutput(BaseModel):
    # 트랜스 포머가 이후 토큰을 만들 때 앞서 쓴 내용을 다시 참고하는 self-attention 구조→ 그래서 defects를 먼저 선언
    defects: list[DefectItem] = Field(
        default_factory=list,
        description="1단계에서 발견한 모든 결함 목록. 결함이 전혀 없으면 빈 리스트.",
    )

    quality_score: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "2단계 점수 매핑 규칙을 defects 리스트에 기계적으로 적용한 결과. "
            "major 결함 0개, minor 0~1개 → 0.85~1.0 / "
            "minor 결함 2개 이상, major 없음 → 0.6~0.85 / "
            "major 결함 1개 → 0.3~0.59 / "
            "major 결함 2개 이상 → 0.0~0.29"
        ),
    )

    feedback: str = Field(
        description="defects 리스트를 종합한 사람이 읽을 요약. 결함이 없어도 '결함 없음' 등으로 명시할 것."
    )

    instrument_issues: dict = Field(
        default_factory=dict,
        description="문제 있는 악기만.",
    )


# --- API 응답 모델 (Swagger /docs 스키마/예시용) ---
class MoodSummary(BaseModel):
    keywords: list[str]
    tempo: int
    scale: str


class GenerateResponse(BaseModel):
    """POST /generate, /regenerate 의 성공 응답 구조."""
    mood: MoodSummary
    chord_progression: list[str]
    tracks: list[TrackOutput]
    quality_score: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "mood": {
                    "keywords": ["melancholic", "lonely", "nocturnal"],
                    "tempo": 72,
                    "scale": "D minor",
                },
                "chord_progression": ["Dm", "Bb", "F", "C", "Dm", "Gm", "A7", "Dm"],
                "tracks": [
                    {
                        "instrument": "Bass",
                        "notes": [
                            {"time": "0:0:0", "note": "D2", "duration": "4n"},
                            {"time": "0:2:0", "note": "A2", "duration": "8n"},
                        ],
                    }
                ],
                "quality_score": 0.82,
            }
        }
    }


class ErrorResponse(BaseModel):
    """에러 응답 구조 (FastAPI HTTPException 기본 형식)."""
    detail: str

