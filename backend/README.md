# Pic to Beat — Multi-Agent Music Generator (Backend)

이미지/텍스트 입력을 받아 분위기 분석 → 작곡 → 악기별 병렬 생성 → 품질 평가(critic) →
재시도 루프를 거쳐 **Tone.js 재생용 멀티트랙 시퀀스**를 만드는 FastAPI + LangGraph 백엔드.

```
[mood_agent] → [music_agent(RAG)] → ┌ bass ┐
                                     ├ kick ┤ (Send 병렬)
                                     ├ pluck┤ → [critic_agent] → score≥0.75 ? finalize : retry
                                     ├ brass┤
                                     └strings┘
```

## 디렉토리 구조

```
picto-beat/
├── main.py                # FastAPI 엔트리 (/generate, /regenerate, /instruments, /health)
├── graph.py               # LangGraph: full graph + regen graph
├── state.py               # MusicState (TypedDict, tracks reducer)
├── requirements.txt
├── .env.example
├── Dockerfile / docker-compose.yml / run.sh
├── agents/
│   ├── schemas.py         # Pydantic 출력 스키마
│   ├── mood_agent.py      # 이미지/텍스트 → 분위기·템포·스케일
│   ├── music_agent.py     # 분위기+RAG → 코드진행·구조·악기 가이드
│   ├── critic_agent.py    # 트랙 품질 채점
│   ├── orchestrator.py    # 라우팅·재시도·finalize
│   └── instruments/       # BaseInstrumentAgent + bass/kick/pluck/brass/strings
└── rag/
    └── music_kb.py        # ChromaDB 음악이론 지식베이스 (lazy seed)
```

## 실행 방법

### A. 로컬 (가장 빠름)

```bash
cp .env.example .env      # ANTHROPIC_API_KEY 채우기
./run.sh                  # venv 생성 + 설치 + uvicorn --reload
```

→ http://localhost:8000/docs (Swagger UI)

### B. Docker

```bash
cp .env.example .env      # 키 채우기
docker compose up --build
```

RAG 인덱스는 `chroma_data` 볼륨에 영속화됨.

## 환경변수 (.env)

| 변수 | 필수 | 설명 |
|------|------|------|
| `ANTHROPIC_API_KEY` | ✅ | 모든 에이전트가 사용 |
| `CHROMA_PERSIST_DIR` | | 기본 `./chroma_db` |
| `MAX_RETRIES` | | critic 재시도 상한(요청 폼으로도 전달 가능) |
| `LANGFUSE_*` | | 트레이싱(선택). 미설정 시 자동 비활성 |

## 엔드포인트

```bash
# 헬스체크
curl localhost:8000/health
# {"status":"ok"}

# 악기 목록
curl localhost:8000/instruments
# {"instruments":["bass","kick","pluck","brass","strings"]}

# 전체 생성 (이미지 또는 텍스트 중 하나 필수)
curl -X POST localhost:8000/generate \
  -F "text=비 오는 밤, 쓸쓸한 도시" \
  -F "max_retries=2"

# 이미지 입력
curl -X POST localhost:8000/generate \
  -F "image=@scene.jpg"

# 부분 재생성 (특정 악기만, mood/music 단계 스킵)
curl -X POST localhost:8000/regenerate \
  -H "Content-Type: application/json" \
  -d '{"instruments":["bass"], "mood_keywords":["dark"], "tempo":90,
       "scale":"A Minor", "color_profile":"", "chord_progression":["Am","F","C","G"],
       "song_structure":{}, "music_guide":{}, "existing_tracks":{}}'
```

`/generate`, `/regenerate` 는 실제 Anthropic API 호출이 일어나므로 유효한 키 필요.
`/health`, `/instruments` 는 키 없이 동작.

## 서버 구축 중 수정한 버그

1. **langfuse import (크래시)**: 원본은 v2 API(`langfuse.decorators`)였는데 설치 패키지가 v3+ 라
   import 자체가 실패 → `from langfuse import observe` 로 4개 파일 수정. 키 미설정 시 트레이싱 자동 비활성.
2. **악기명 대소문자 불일치 (retry 경로 크래시)**: critic LLM 이 `instrument_issues` 키를 `"Bass"` 처럼
   대문자로 주면 `INSTRUMENT_REGISTRY["Bass"]` 조회에서 `KeyError` → 재시도 시 500.
   → `critic_agent` 에서 issue 키를 소문자로 정규화 + `graph.run_instrument` 에서 소문자 조회로 방어.
   덤으로 critic 의 수정 힌트가 해당 악기에 정상 전달되도록 함(기존엔 키 불일치로 유실됨).
3. **`increment_retry` 의 `tracks: {}` (오해 소지)**: merge reducer 때문에 실제로는 초기화 안 됨(no-op).
   동작 자체는 의도대로(정상 트랙 보존 + 문제 악기만 덮어쓰기)라 줄만 제거하고 주석으로 명시.
4. **`MAX_RETRIES` env 미사용**: `.env` 에 있지만 `main.py` 가 안 읽었음 → `/generate` 의 기본값이
   `MAX_RETRIES` 환경변수를 따르도록 연결.

## 참고 / 알아둘 점

- 키 없이도 동작하는 엔드포인트(`/health`, `/instruments`)와 그래프 오케스트레이션(mood→music→악기병렬
  →critic→retry/finalize, regen)은 LLM 모킹 e2e 로 검증 완료(`test_e2e.py`).
- **ChromaDB 임베딩 모델**: `DefaultEmbeddingFunction` 이 첫 쿼리 때 MiniLM 모델을 1회 다운로드함
  (Docker 첫 `/generate` 호출이 약간 느릴 수 있음).
- **이미지 media_type**: `mood_agent.py` 가 `image/jpeg` 로 하드코딩돼 있어 PNG 등은 인식 불안정할 수 있음.
  필요하면 업로드 content-type 기반으로 동적 처리하도록 바꾸면 됨.
