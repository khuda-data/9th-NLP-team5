"""
LLM 레이어를 가짜로 갈아끼우고 graph 오케스트레이션을 end-to-end로 검증.
실제 Anthropic 호출 없이 mood→music→악기병렬→critic→retry/finalize 와 regen 그래프를 돌린다.
"""
import os, json, asyncio, sys
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-dummy")
os.environ.setdefault("CHROMA_PERSIST_DIR", "/tmp/chroma_e2e")

import agents.mood_agent as mood_mod
import agents.music_agent as music_mod
import agents.critic_agent as critic_mod
import agents.instruments.base_instrument as base_mod
from agents.schemas import MoodOutput, MusicOutput, CriticOutput

# ---- 가짜 anthropic 클라이언트 (mood_agent / base_instrument 용) ----
class _Msg:
    def __init__(self, text): self.content = [type("B", (), {"text": text})()]

class _FakeMessages:
    def __init__(self, payload_fn): self._fn = payload_fn
    def create(self, **kw): return _Msg(self._fn(kw))

class FakeAnthropic:
    def __init__(self, payload_fn): self.messages = _FakeMessages(payload_fn)

def _mood_payload(kw):
    return json.dumps({
        "mood_keywords": ["dark", "melancholic"],
        "tempo": 90, "scale": "A Minor", "color_profile": "deep blue",
    })

def _track_payload(kw):
    # system 프롬프트에서 악기 이름 추출
    syss = kw.get("system", "")
    return json.dumps({
        "instrument": "X",
        "notes": [{"time": "0:0:0", "note": "A2", "duration": "4n"}],
    })

mood_mod._client = FakeAnthropic(_mood_payload)
base_mod._client = FakeAnthropic(_track_payload)

# ---- 가짜 structured chain (music_agent / critic_agent 용) ----
class FakeChain:
    def __init__(self, fn): self._fn = fn
    async def ainvoke(self, inputs): return self._fn(inputs)

music_mod._chain = FakeChain(lambda i: MusicOutput(
    chord_progression=["Am", "F", "C", "G"],
    song_structure={"intro": "4 bars", "main": "8 bars", "outro": "4 bars"},
    music_guide={"bass": "root notes", "kick": "four-on-floor",
                 "pluck": "arp", "brass": "stabs", "strings": "pads"},
))
# RAG (chroma) 도 스텁 처리 — 임베딩 모델 다운로드 회피
music_mod.query_music_knowledge = lambda scale, mood_keywords, n_results=4: "- (stub theory)"

# critic 은 시나리오별로 갈아끼움
def set_critic(fn): critic_mod._chain = FakeChain(fn)

# graph 는 위 패치 이후에 import (그래프가 노드 함수를 참조하므로 함수 내부에서 모듈 글로벌을 봄)
from graph import music_graph, regen_graph
from state import MusicState


def base_state(**over):
    s = dict(image_base64=None, user_text="비 오는 밤", target_instruments=None,
             mood_keywords=[], tempo=120, scale="C Major", color_profile="",
             chord_progression=[], song_structure={}, music_guide={}, tracks={},
             critic_feedback=None, quality_score=0.0, instrument_issues={},
             retry_count=0, max_retries=2, final_output=None)
    s.update(over); return s


async def scenario_happy():
    set_critic(lambda i: CriticOutput(quality_score=0.9, feedback="good", instrument_issues={}))
    out = await music_graph.ainvoke(base_state())
    fo = out["final_output"]
    assert fo is not None
    assert len(fo["tracks"]) == 5, fo["tracks"]
    assert fo["quality_score"] == 0.9
    return f"OK  tracks={len(fo['tracks'])} score={fo['quality_score']}"


async def scenario_retry_lowercase():
    calls = {"n": 0}
    def crit(i):
        calls["n"] += 1
        if calls["n"] == 1:
            return CriticOutput(quality_score=0.5, feedback="bass weak", instrument_issues={"bass": "too sparse"})
        return CriticOutput(quality_score=0.85, feedback="fixed", instrument_issues={})
    set_critic(crit)
    out = await music_graph.ainvoke(base_state())
    fo = out["final_output"]
    assert fo["quality_score"] == 0.85
    return f"OK  critic_calls={calls['n']} final_score={fo['quality_score']} tracks={len(fo['tracks'])}"


async def scenario_retry_capitalized():
    def crit(i):
        return CriticOutput(quality_score=0.5, feedback="Bass weak",
                            instrument_issues={"Bass": "too sparse"})
    set_critic(crit)
    out = await music_graph.ainvoke(base_state(max_retries=1))
    return f"OK  final_score={out['final_output']['quality_score']}"


async def scenario_regen():
    set_critic(lambda i: CriticOutput(quality_score=0.9, feedback="good", instrument_issues={}))
    st = base_state(target_instruments=["bass", "kick"], mood_keywords=["dark"],
                    tempo=90, scale="A Minor", chord_progression=["Am", "F", "C", "G"],
                    song_structure={"main": "8 bars"},
                    music_guide={"bass": "root", "kick": "4floor"},
                    tracks={"pluck": {"instrument": "Pluck", "notes": []}})
    out = await regen_graph.ainvoke(st)
    fo = out["final_output"]
    return f"OK  regen tracks={len(fo['tracks'])} keys_via_count"


async def main():
    scenarios = [
        ("1. happy path (즉시 finalize)", scenario_happy),
        ("2. retry (소문자 issue 키)", scenario_retry_lowercase),
        ("3. retry (대문자 issue 키)", scenario_retry_capitalized),
        ("4. regen graph", scenario_regen),
    ]
    for name, fn in scenarios:
        try:
            res = await fn()
            print(f"[PASS] {name}: {res}")
        except Exception as e:
            print(f"[FAIL] {name}: {type(e).__name__}: {e}")

asyncio.run(main())
