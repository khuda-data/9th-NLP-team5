import os
import base64
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from graph import music_graph, regen_graph
from agents.instruments import ALL_INSTRUMENTS

app = FastAPI(title="Multi-Agent Music Generator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegenerateRequest(BaseModel):
    instruments: list[str]
    # 기존 state 재사용을 위한 컨텍스트
    mood_keywords: list[str]
    tempo: int
    scale: str
    color_profile: str
    chord_progression: list[str]
    song_structure: dict
    music_guide: dict
    existing_tracks: dict


@app.post("/generate")
async def generate_music(
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    max_retries: int = Form(2),
):
    """이미지/텍스트를 입력받아 전체 음악 시퀀스를 생성합니다."""
    if not image and not text:
        raise HTTPException(status_code=400, detail="image 또는 text 중 하나는 필수입니다.")

    image_b64: Optional[str] = None
    if image:
        raw = await image.read()
        image_b64 = base64.b64encode(raw).decode("utf-8")

    initial_state = {
        "image_base64": image_b64,
        "user_text": text,
        "target_instruments": None,
        "mood_keywords": [],
        "tempo": 120,
        "scale": "C Major",
        "color_profile": "",
        "chord_progression": [],
        "song_structure": {},
        "music_guide": {},
        "tracks": {},
        "critic_feedback": None,
        "quality_score": 0.0,
        "instrument_issues": {},
        "retry_count": 0,
        "max_retries": max_retries,
        "final_output": None,
    }

    result = await music_graph.ainvoke(initial_state)
    return result["final_output"]


@app.post("/regenerate")
async def regenerate_instruments(body: RegenerateRequest):
    """특정 악기만 선택적으로 재생성합니다."""
    invalid = [i for i in body.instruments if i not in ALL_INSTRUMENTS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"알 수 없는 악기: {invalid}")

    # mood/music 단계를 건너뛰고 악기 생성부터 시작
    initial_state = {
        "image_base64": None,
        "user_text": None,
        "target_instruments": body.instruments,
        "mood_keywords": body.mood_keywords,
        "tempo": body.tempo,
        "scale": body.scale,
        "color_profile": body.color_profile,
        "chord_progression": body.chord_progression,
        "song_structure": body.song_structure,
        "music_guide": body.music_guide,
        "tracks": body.existing_tracks,
        "critic_feedback": None,
        "quality_score": 0.0,
        "instrument_issues": {},
        "retry_count": 0,
        "max_retries": 1,
        "final_output": None,
    }

    result = await regen_graph.ainvoke(initial_state)
    return result["final_output"]


@app.get("/instruments")
def list_instruments():
    return {"instruments": ALL_INSTRUMENTS}


@app.get("/health")
def health():
    return {"status": "ok"}
