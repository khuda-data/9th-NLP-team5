import os
import uuid
import time
import base64
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from graph import music_graph, regen_graph
from agents.instruments import ALL_INSTRUMENTS
from logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Multi-Agent Music Generator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())[:8]
    logger.info("REQUEST  [%s] %s %s", req_id, request.method, request.url.path)
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - t0
    logger.info(
        "RESPONSE [%s] status=%d elapsed=%.2fs",
        req_id, response.status_code, elapsed,
    )
    return response


class RegenerateRequest(BaseModel):
    instruments: list[str]
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
    max_retries: int = Form(int(os.getenv("MAX_RETRIES", "2"))),
):
    """이미지/텍스트를 입력받아 전체 음악 시퀀스를 생성합니다."""
    if not image and not text:
        raise HTTPException(status_code=400, detail="image 또는 text 중 하나는 필수입니다.")

    image_b64: Optional[str] = None
    if image:
        raw = await image.read()
        image_b64 = base64.b64encode(raw).decode("utf-8")
        logger.info("generate | image_size=%d bytes max_retries=%d", len(raw), max_retries)
    else:
        logger.info("generate | text_prompt='%s' max_retries=%d", (text or "")[:80], max_retries)

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

    t0 = time.perf_counter()
    result = await music_graph.ainvoke(initial_state)
    elapsed = time.perf_counter() - t0

    score = result.get("final_output", {}).get("quality_score", 0.0)
    logger.info("generate complete | score=%.2f elapsed=%.2fs", score, elapsed)

    return result["final_output"]


@app.post("/regenerate")
async def regenerate_instruments(body: RegenerateRequest):
    """특정 악기만 선택적으로 재생성합니다."""
    invalid = [i for i in body.instruments if i not in ALL_INSTRUMENTS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"알 수 없는 악기: {invalid}")

    logger.info("regenerate | instruments=%s", body.instruments)

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

    t0 = time.perf_counter()
    result = await regen_graph.ainvoke(initial_state)
    elapsed = time.perf_counter() - t0

    score = result.get("final_output", {}).get("quality_score", 0.0)
    logger.info("regenerate complete | instruments=%s score=%.2f elapsed=%.2fs", body.instruments, score, elapsed)

    return result["final_output"]


@app.get("/instruments")
def list_instruments():
    return {"instruments": ALL_INSTRUMENTS}


@app.get("/health")
def health():
    return {"status": "ok"}
