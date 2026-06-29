from pydantic import BaseModel, Field


class MoodOutput(BaseModel):
    mood_keywords: list[str] = Field(min_length=1)
    tempo: int = Field(ge=60, le=180)
    scale: str
    color_profile: str


class NoteEvent(BaseModel):
    time: str       # Tone.js format: "measure:beat:subdivision"
    note: str       # e.g. "A2", "C4"
    duration: str   # e.g. "4n", "8n", "2n"


class TrackOutput(BaseModel):
    instrument: str
    notes: list[NoteEvent] = Field(min_length=1)


class MusicOutput(BaseModel):
    chord_progression: list[str] = Field(min_length=2)
    song_structure: dict = Field(default_factory=dict)   # {intro, main, outro}
    music_guide: dict = Field(default_factory=dict)       # {bass, kick, pluck, brass, strings}


class CriticOutput(BaseModel):
    quality_score: float = Field(ge=0.0, le=1.0)
    feedback: str = ""
    instrument_issues: dict = Field(default_factory=dict)


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
