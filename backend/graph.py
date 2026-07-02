from langgraph.graph import StateGraph, END
from langgraph.constants import Send

from state import MusicState
from agents.mood_agent import mood_agent
from agents.music_agent import music_agent
from agents.critic_agent import critic_agent
from agents.orchestrator import orchestrator_router, increment_retry, finalize
from agents.instruments import INSTRUMENT_REGISTRY, ALL_INSTRUMENTS

# 악기 노드: 
async def run_instrument(state: dict) -> dict:
    instrument_name: str = state["instrument_name"].lower() 
    agent = INSTRUMENT_REGISTRY[instrument_name]() # 팩토리 패턴 호출 - 생성자 호출 
    track = await agent.generate(state)
    return {"tracks": {instrument_name: track}}


# 악기 병렬 라우터 Send
def route_to_instruments(state: MusicState) -> list[Send]:
    targets = state.get("target_instruments") or ALL_INSTRUMENTS
    return [
        Send("run_instrument", {**state, "instrument_name": inst})
        for inst in targets
    ]


def _add_instrument_subgraph(g: StateGraph) -> None:
    g.add_node("run_instrument", run_instrument)
    g.add_node("critic_agent", critic_agent)
    g.add_node("increment_retry", increment_retry)
    g.add_node("finalize", finalize)

    g.add_edge("run_instrument", "critic_agent")
    g.add_conditional_edges(
        "critic_agent",
        orchestrator_router,
        {"finalize": "finalize", "retry": "increment_retry"},
    )
    g.add_conditional_edges("increment_retry", route_to_instruments, ["run_instrument"])
    g.add_edge("finalize", END)


def build_full_graph() -> StateGraph:
    #MusicState 를 기반으로 하는 StateGraph 생성
    g = StateGraph(MusicState)

    g.add_node("mood_agent", mood_agent)
    g.add_node("music_agent", music_agent)

    _add_instrument_subgraph(g)

    g.set_entry_point("mood_agent")
    g.add_edge("mood_agent", "music_agent")
    g.add_conditional_edges("music_agent", route_to_instruments, ["run_instrument"])
    return g.compile()


def build_regen_graph() -> StateGraph:
    #부분 재생성 mood/music 스킵하고 악기 생성부터 시작.
    g = StateGraph(MusicState)
    _add_instrument_subgraph(g)
    # 악기 병렬 실행이 진입점
    g.add_conditional_edges("__start__", route_to_instruments, ["run_instrument"])
    return g.compile()


# 싱글턴 컴파일 그래프
music_graph = build_full_graph()
regen_graph = build_regen_graph()
