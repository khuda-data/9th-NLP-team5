# Pic to Beat — Multi-Agent Music Generator (Backend)

이미지/텍스트 입력을 받아 분위기 분석 → 작곡 → 악기별 병렬 생성 → 품질 평가 → 재시도 루프를 거쳐
**Tone.js 재생용 멀티트랙 시퀀스**를 반환하는 FastAPI + LangGraph 백엔드.

```
[mood_agent] → [music_agent(RAG)] → ┌ bass ┐
                                     ├ kick ┤ (병렬)
                                     ├ pluck┤ → [critic_agent] → score≥0.7 ? 완료 : retry
                                     ├ brass┤
                                     └strings┘
```

## 기술 스택

| 역할 | 라이브러리 |
|------|-----------|
| API 서버 | FastAPI + Uvicorn |
| 에이전트 오케스트레이션 | LangGraph |
| LLM | Anthropic Claude (mood/critic: Haiku, music/instruments: Sonnet) |
| LLM 체인 | LangChain-Anthropic |
| RAG 지식베이스 | ChromaDB |
| 트레이싱 | Langfuse 4.x (`@observe`) |

## 디렉토리 구조

```
backend/
├── main.py              # FastAPI 엔트리 (/generate, /regenerate, /instruments, /health)
├── graph.py             # LangGraph 그래프 정의
├── state.py             # MusicState (TypedDict + tracks reducer)
├── logger.py            # 공통 로거
├── requirements.txt
├── .env.example
├── run.bat              # Windows 로컬 실행 스크립트
├── agents/
│   ├── schemas.py       # Pydantic 출력 스키마
│   ├── mood_agent.py    # 이미지/텍스트 → 분위기·템포·스케일 (Haiku)
│   ├── music_agent.py   # 분위기+RAG → 코드진행·구조·악기 가이드 (Sonnet)
│   ├── critic_agent.py  # 트랙 품질 채점 0~1 (Haiku)
│   ├── orchestrator.py  # 라우팅·재시도·finalize
│   └── instruments/     # BaseInstrumentAgent + bass/kick/pluck/brass/strings (Sonnet)
└── rag/
    └── music_kb.py      # ChromaDB 음악이론 지식베이스
```

## 실행 방법

```bash
# .env 파일 준비
cp .env.example .env   # ANTHROPIC_API_KEY 입력

# Windows
run.bat

# 또는 직접
python -m uvicorn main:app --reload --port 8000
```

→ Swagger UI: http://localhost:8000/docs

## 환경변수 (.env)

| 변수 | 필수 | 설명 |
|------|------|------|
| `ANTHROPIC_API_KEY` | ✅ | 모든 LLM 호출에 사용 |
| `LANGFUSE_PUBLIC_KEY` | | Langfuse 트레이싱 (없으면 자동 비활성) |
| `LANGFUSE_SECRET_KEY` | | Langfuse 트레이싱 |
| `LANGFUSE_HOST` | | 기본값 `https://cloud.langfuse.com` |
| `CHROMA_PERSIST_DIR` | | 기본값 `./chroma_db` |
| `MAX_RETRIES` | | critic 재시도 상한 (기본값 2) |

## 주요 엔드포인트

```bash
# 헬스체크
GET  /health        → {"status":"ok"}

# 악기 목록
GET  /instruments   → {"instruments":["bass","kick","pluck","brass","strings"]}

# 음악 생성 (image 또는 text 중 하나 필수)
POST /generate
  -F "image=@scene.jpg"
  -F "text=비 오는 밤, 쓸쓸한 도시"
  -F "max_retries=2"

# 특정 악기만 재생성 (mood/music 단계 스킵)
POST /regenerate   (JSON body)
```

## 응답 구조

```json
{
  "scale": "C Major",
  "tempo": 90,
  "chord_progression": ["Cmaj7", "Am7", "F", "G"],
  "tracks": {
    "Bass":    {"notes": [{"time": "0:0:0", "note": "C2", "duration": "4n"}, ...]},
    "Kick":    {"notes": [...]},
    "Pluck":   {"notes": [...]},
    "Brass":   {"notes": [...]},
    "Strings": {"notes": [...]}
  }
}
```

`time` 은 Tone.js `"measure:beat:subdivision"` 포맷, `duration` 은 `4n` (4분음표) 등 Tone.js 표기.

## 알아둘 점

- ChromaDB `DefaultEmbeddingFunction` 은 첫 실행 시 MiniLM 모델을 1회 다운로드함 (약간 느릴 수 있음).
- `/health`, `/instruments` 는 API 키 없이 동작. `/generate`, `/regenerate` 는 유효한 키 필요.
- Langfuse 키 미설정 시 트레이싱 없이 정상 동작.
