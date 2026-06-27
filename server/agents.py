"""
agents.py
기획서의 에이전트들이 여기 모여 있다.

  Mood Agent      : 이미지/텍스트 -> 분위기, key, bpm, 코드 진행
  Performer Agent : 악기 하나의 멜로디/패턴 생성 (Bass, Kick, Pluck, Brass, Strings...)
  Critic Agent    : 생성된 곡을 평가하고 다시 만들 트랙을 지정

[팀원이 할 일]
  1) 맨 아래 call_llm() 함수에 실제 LLM 호출(Claude / 로컬모델)을 채운다.
  2) 각 에이전트의 prompt 부분을 다듬는다.
  3) 환경변수 USE_LLM=1 로 켜면 더미 대신 진짜 LLM 이 동작한다.

지금(USE_LLM 꺼짐)은 "규칙 기반 더미"가 돌아가서, AI 없이도
실제로 소리가 나는 음악이 생성된다 -> 연결/재생 테스트 가능.
"""

import asyncio
import os

from schemas import Constraints, CriticReport, Mood, Note, Track

USE_LLM = os.environ.get("USE_LLM") == "1"   # 1 이면 실제 LLM, 아니면 더미


# ===============================================================
#  음악 헬퍼 (더미가 그럴듯한 음을 만들기 위한 최소한의 음악 지식)
# ===============================================================
# 코드 -> 구성음(옥타브 없는 음 이름)
_CHORD_TONES = {
    "Cm": ["C", "Eb", "G"], "Ab": ["Ab", "C", "Eb"],
    "Eb": ["Eb", "G", "Bb"], "Bb": ["Bb", "D", "F"],
    "Gm": ["G", "Bb", "D"], "Fm": ["F", "Ab", "C"],
}


def _chord_tones(chord: str) -> list[str]:
    return _CHORD_TONES.get(chord, ["C", "Eb", "G"])


# ===============================================================
#  Mood Agent
# ===============================================================
async def mood_agent(image_base64: str | None, prompt: str | None) -> Mood:
    """이미지/텍스트에서 분위기를 추출한다."""
    if USE_LLM:
        # 👉 팀원: 이미지(vision) + 텍스트를 LLM에 넣고, 분위기 JSON을 받아 파싱
        _prompt = (
            "다음 입력의 분위기를 분석해서 keywords, energy(0~1), description 을 "
            "JSON으로만 답하라.\n입력: " + (prompt or "(이미지 참조)")
        )
        raw = await call_llm(_prompt, image_base64=image_base64)
        return _parse_mood(raw)

    # --- 더미 ---
    text = (prompt or "").lower()
    energy = 0.8 if any(w in text for w in ["energetic", "신나", "fast", "활기"]) else 0.4
    return Mood(
        keywords=["calm", "warm"] if energy < 0.5 else ["bright", "driving"],
        energy=energy,
        description=prompt or "이미지에서 추출한 분위기(더미)",
    )


def build_constraints(mood: Mood) -> Constraints:
    """Mood 를 바탕으로 마스터가 강제할 공통 제약을 확정한다."""
    if USE_LLM:
        # 실제로는 mood 기반으로 LLM/규칙이 key·bpm·코드진행을 정할 수 있음
        pass
    bpm = 90 + int(mood.energy * 60)            # 잔잔 90 ~ 격렬 150
    return Constraints(key="C minor", bpm=bpm, chord_progression=["Cm", "Ab", "Eb", "Bb"], bars=4)


# ===============================================================
#  Performer Agent (악기 하나)  -- 이게 병렬로 여러 개 동시에 돈다
# ===============================================================
async def performer_agent(instrument: str, constraints: Constraints, mood: Mood,
                          instruction: str | None = None) -> Track:
    """악기 하나의 트랙(음표들)을 생성한다."""
    if USE_LLM:
        # 👉 팀원: 악기 역할 + 공통제약(키/BPM/코드) + 분위기를 LLM에 주고
        #         Tone.js 음표 배열을 JSON으로 받아 파싱
        _prompt = (
            f"악기 '{instrument}' 의 {constraints.bars}마디 패턴을 만들어라. "
            f"키 {constraints.key}, BPM {constraints.bpm}, "
            f"코드진행 {constraints.chord_progression}. 분위기 {mood.keywords}. "
            f"추가지시: {instruction or '없음'}. "
            "Tone.js 음표 배열(JSON)로만 답하라."
        )
        raw = await call_llm(_prompt)
        return _parse_track(instrument, raw)

    # --- 더미: 실제로 소리나는 패턴 생성 ---
    # (LLM 호출 시간을 흉내내는 지연 — 실제 LLM 붙이면 자연히 사라짐.
    #  이게 있어야 "병렬이 순차보다 빠르다"는 걸 눈으로 확인 가능)
    await asyncio.sleep(0.4)
    return _dummy_track(instrument, constraints)


# ===============================================================
#  Critic Agent
# ===============================================================
async def critic_agent(tracks: dict[str, Track], constraints: Constraints) -> CriticReport:
    """곡을 평가하고, 다시 만들 트랙을 지정한다."""
    if USE_LLM:
        # 👉 팀원: 트랙들 + 음악이론(RAG)을 LLM에 주고 평가/불협화도/피드백 받기
        _prompt = "다음 트랙들의 협화도와 무드 적합성을 평가하라. ..."
        raw = await call_llm(_prompt)
        return _parse_critic(raw)

    # --- 더미: 간단 평가 (빈 트랙이 있으면 재생성 대상으로) ---
    await asyncio.sleep(0.2)
    needs = [name for name, t in tracks.items() if len(t.notes) == 0]
    return CriticReport(
        score=0.85 if not needs else 0.5,
        dissonance=0.15,
        feedback={n: "음표가 비어 있어 재생성 필요" for n in needs},
        needs_revision=needs,
    )


# ===============================================================
#  더미 트랙 생성기 (USE_LLM 꺼졌을 때 사용)
# ===============================================================
def _dummy_track(instrument: str, c: Constraints) -> Track:
    notes: list[Note] = []
    inst = instrument.lower()

    for bar in range(c.bars):
        chord = c.chord_progression[bar % len(c.chord_progression)]
        tones = _chord_tones(chord)

        if inst == "kick":
            # 매 박마다 킥 (음정 없음)
            for beat in range(4):
                notes.append(Note(time=f"{bar}:{beat}:0", note=None, duration="8n", velocity=0.9))
        elif inst == "bass":
            # 코드 근음을 낮게, 박자마다
            root = tones[0]
            for beat in range(4):
                notes.append(Note(time=f"{bar}:{beat}:0", note=f"{root}2", duration="4n", velocity=0.8))
        elif inst == "pluck":
            # 코드 구성음 아르페지오 (8분음표 8개)
            for i in range(8):
                t = tones[i % len(tones)]
                notes.append(Note(time=f"{bar}:{i // 2}:{(i % 2) * 2}", note=f"{t}4", duration="8n", velocity=0.6))
        elif inst == "brass":
            # 코드 화음을 길게 (마디 시작)
            notes.append(Note(time=f"{bar}:0:0", note=[f"{t}4" for t in tones], duration="1n", velocity=0.5))
        else:  # strings 등 패드류
            notes.append(Note(time=f"{bar}:0:0", note=[f"{t}3" for t in tones], duration="1n", velocity=0.4))

    synth_map = {
        "kick": "Tone.MembraneSynth", "bass": "Tone.MonoSynth",
        "pluck": "Tone.PluckSynth", "brass": "Tone.Synth", "strings": "Tone.PolySynth",
    }
    return Track(instrument=instrument, synth=synth_map.get(inst, "Tone.Synth"), notes=notes)


# ===============================================================
#  실제 LLM 호출 자리  (팀원이 채우는 핵심 한 곳)
# ===============================================================
async def call_llm(prompt: str, image_base64: str | None = None, model: str = "claude") -> str:
    """
    모든 에이전트가 이 함수를 통해 LLM을 부른다.
    여기 한 곳만 채우면 Mood/Performer/Critic 전부가 LLM에 연결된다.

    예시) Claude API (async):
        import os
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    """
    raise NotImplementedError("call_llm 을 구현하세요 (USE_LLM=1 일 때 호출됨)")


# --- LLM 응답 파서 자리 (실제 LLM 붙일 때 구현) ---
def _parse_mood(raw: str) -> Mood: ...
def _parse_track(instrument: str, raw: str) -> Track: ...
def _parse_critic(raw: str) -> CriticReport: ...
