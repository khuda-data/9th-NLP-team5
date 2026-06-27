"""
orchestrator.py
기획서의 Orchestrator Agent. 전체 흐름을 지휘한다.

흐름:
  1) Mood Agent 로 분위기 추출
  2) 공통 제약(key/bpm/코드) 확정  -> 모든 악기에 강제 (통일성)
  3) Performer 들을 "병렬"로 실행      -> asyncio.gather (기획서: 병렬 처리)
  4) Critic 으로 평가 -> 부족한 트랙만 다시 생성 (피드백 루프)
  5) 완성된 State 반환

부분 갱신(revise): 지정한 트랙만 다시 실행해서 State 를 갱신 -> 토큰/시간 절약.

on_event 콜백으로 각 단계 진행상황을 흘려보낼 수 있다(개발자 모드/SSE용).
"""

import asyncio
import time
from typing import Awaitable, Callable, Optional

import agents
from schemas import GenerateResponse, MusicState, Track

# 진행상황을 받을 콜백 타입 (단계이름, 상세정보)
EventCb = Optional[Callable[[str, dict], Awaitable[None]]]

MAX_CRITIC_LOOPS = 2   # Critic 재생성 반복 상한 (비용 폭주 방지)


async def _emit(cb: EventCb, stage: str, detail: dict):
    if cb:
        await cb(stage, detail)


async def generate(
    image_base64: str | None,
    prompt: str | None,
    instruments: list[str],
    on_event: EventCb = None,
) -> GenerateResponse:
    timing: dict[str, float] = {}

    # --- 1) Mood ---
    t0 = time.perf_counter()
    await _emit(on_event, "mood:start", {})
    mood = await agents.mood_agent(image_base64, prompt)
    constraints = agents.build_constraints(mood)
    timing["mood_ms"] = (time.perf_counter() - t0) * 1000
    await _emit(on_event, "mood:done", {"mood": mood.model_dump(), "constraints": constraints.model_dump()})

    # --- 2) Performer 들 병렬 실행 ---
    t0 = time.perf_counter()
    await _emit(on_event, "performers:start", {"instruments": instruments})
    results = await asyncio.gather(
        *[agents.performer_agent(inst, constraints, mood) for inst in instruments]
    )
    tracks: dict[str, Track] = {inst: trk for inst, trk in zip(instruments, results)}
    timing["performers_ms"] = (time.perf_counter() - t0) * 1000
    await _emit(on_event, "performers:done", {"tracks": list(tracks.keys())})

    # --- 3) Critic 평가 + 부족한 트랙만 재생성 (피드백 루프) ---
    t0 = time.perf_counter()
    critic = None
    for loop in range(MAX_CRITIC_LOOPS):
        await _emit(on_event, "critic:start", {"loop": loop})
        critic = await agents.critic_agent(tracks, constraints)
        await _emit(on_event, "critic:done", {"score": critic.score, "needs_revision": critic.needs_revision})
        if not critic.needs_revision:
            break
        # 문제 있는 트랙만 병렬 재생성
        await _emit(on_event, "revise:start", {"targets": critic.needs_revision})
        redone = await asyncio.gather(
            *[agents.performer_agent(inst, constraints, mood) for inst in critic.needs_revision]
        )
        for inst, trk in zip(critic.needs_revision, redone):
            tracks[inst] = trk
    timing["critic_ms"] = (time.perf_counter() - t0) * 1000

    state = MusicState(constraints=constraints, mood=mood, tracks=tracks, critic=critic)
    await _emit(on_event, "complete", {})
    return GenerateResponse(ok=True, state=state, timing_ms=timing)


async def revise(
    state: MusicState,
    targets: list[str],
    instruction: str | None = None,
    on_event: EventCb = None,
) -> GenerateResponse:
    """지정한 트랙만 다시 만든다 (누적 State 부분 갱신)."""
    timing: dict[str, float] = {}
    t0 = time.perf_counter()
    await _emit(on_event, "revise:start", {"targets": targets})

    # 대상 트랙만 병렬 재생성 — 나머지는 그대로 유지
    redone = await asyncio.gather(
        *[agents.performer_agent(inst, state.constraints, state.mood, instruction) for inst in targets]
    )
    for inst, trk in zip(targets, redone):
        state.tracks[inst] = trk

    # 재평가
    state.critic = await agents.critic_agent(state.tracks, state.constraints)
    timing["revise_ms"] = (time.perf_counter() - t0) * 1000
    await _emit(on_event, "complete", {})
    return GenerateResponse(ok=True, state=state, timing_ms=timing)
