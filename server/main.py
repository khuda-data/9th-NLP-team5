"""
main.py
FastAPI 서버 진입점. 프론트(React/Tone.js)가 호출하는 입구.

엔드포인트:
  GET  /api/health           서버 살아있나
  POST /api/generate         이미지/텍스트 -> 곡 전체 생성
  POST /api/revise           특정 트랙만 다시 생성 (부분 갱신)
  POST /api/generate/stream  생성하면서 각 에이전트 진행상황을 실시간 전송 (개발자 모드)

실행(로컬):  uvicorn main:app --reload
"""

import asyncio
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import orchestrator
from schemas import GenerateRequest, GenerateResponse, ReviseRequest

app = FastAPI(title="Pic to Beat — Orchestrator Server")

# 프론트(React, 다른 포트/도메인)에서 호출 가능하게 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 배포 시엔 프론트 주소만 넣기
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------
# 곡 전체 생성
# ---------------------------------------------------------------
@app.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    try:
        return await orchestrator.generate(
            image_base64=req.image_base64,
            prompt=req.prompt,
            instruments=req.instruments,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------
# 부분 갱신 — 지정한 트랙만 다시
# ---------------------------------------------------------------
@app.post("/api/revise", response_model=GenerateResponse)
async def revise(req: ReviseRequest):
    try:
        return await orchestrator.revise(
            state=req.state,
            targets=req.targets,
            instruction=req.instruction,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------
# 개발자 모드: 생성 과정을 실시간 스트리밍 (Server-Sent Events)
# 프론트에서 fetch + ReadableStream 또는 EventSource 로 받는다.
# 각 에이전트가 "언제 무엇을 하는지" 화면에 흘려보낼 수 있다.
# ---------------------------------------------------------------
@app.post("/api/generate/stream")
async def generate_stream(req: GenerateRequest):
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(stage: str, detail: dict):
        await queue.put({"stage": stage, "detail": detail})

    async def run():
        try:
            res = await orchestrator.generate(
                image_base64=req.image_base64,
                prompt=req.prompt,
                instruments=req.instruments,
                on_event=on_event,
            )
            # 마지막에 완성된 결과를 함께 흘려보냄
            await queue.put({"stage": "result", "detail": res.model_dump()})
        except Exception as e:
            await queue.put({"stage": "error", "detail": {"message": str(e)}})
        finally:
            await queue.put(None)  # 끝 신호

    async def event_generator():
        task = asyncio.create_task(run())
        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        await task

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
