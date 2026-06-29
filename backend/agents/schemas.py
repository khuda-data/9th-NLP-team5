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
