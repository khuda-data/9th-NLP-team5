# 프로젝트 명세서: 멀티 에이전트 기반 음악 생성 시스템

## 1. 시스템 목적 및 핵심 메커니즘

- **목적**: 이미지/텍스트 입력을 파싱하여 `Tone.js`에서 재생 가능한 악기별 멜로디 시퀀스(JSON)를 협업 생성
- **핵심 특징**:
  - 단일 호출이 아닌 '평가-수정-재생성'의 피드백 루프 구현 (Critic-Generator 패턴)
  - 사용자가 특정 트랙만 선택 재생성 가능 (`/regenerate` — 전체 재생성 방지, 지연 시간 단축)
  - Pydantic v2로 모든 LLM 출력을 구조화 검증 (JSON 파싱 실패 방지)
  - Langfuse로 전체 파이프라인 LLM 호출 트레이싱 및 비용 모니터링

---

## 2. 기술 스택

| 분류                    | 기술                                                          |
| ----------------------- | ------------------------------------------------------------- |
| **Framework**           | FastAPI + Uvicorn (비동기 API)                                |
| **Agent Orchestration** | LangGraph (StateGraph, Send API, Conditional Edges)           |
| **LLM Framework**       | LangChain LCEL (`prompt \| llm \| structured_output`)         |
| **Main LLM**            | Claude 3.5 Sonnet — 멀티모달 (이미지+텍스트 동시 입력)        |
| **Output Validation**   | Pydantic v2 (`model_validate_json`, `with_structured_output`) |
| **Observability**       | Langfuse (LLM 트레이싱, 토큰 비용, 지연 모니터링)             |
| **Vector DB**           | ChromaDB (음악 이론 RAG)                                      |

---

## 3. 에이전트 구조 및 역할 정의

### Orchestrator (그래프 레벨 라우터)

- Critic의 `quality_score`를 기준으로 재시도 vs 완료 분기
- `quality_score >= 0.75` → finalize (최종 반환)
- `quality_score < 0.75 && retry_count < max` → 문제 악기만 타겟하여 재생성
- 구현: LangGraph `add_conditional_edges` + `orchestrator_router` 라우터 함수

### Mood Agent

- **입력**: 이미지(base64), 사용자 텍스트
- **처리**: Anthropic SDK 직접 호출 (Claude Vision 멀티모달)
- **출력 (Pydantic)**: `MoodOutput` — `mood_keywords`, `tempo`, `scale`, `color_profile`
- **트레이싱**: `@observe(name="mood_agent")` → Langfuse에 입출력 자동 기록

### Music Agent

- **입력**: `MoodOutput` + ChromaDB RAG 검색 결과
- **처리**: LangChain LCEL 체인
  ```
  ChatPromptTemplate | ChatAnthropic.with_structured_output(MusicOutput)
  ```
- **출력 (Pydantic)**: `MusicOutput` — `chord_progression`, `song_structure`, `music_guide`
- **트레이싱**: `@observe(name="music_agent")`

### Instrument Sub-Agents (병렬 실행)

- **종류**: Bass, Kick, Pluck, Brass, Strings
- **처리**: LangGraph `Send` API로 동시 실행 → `tracks`에 자동 병합 (Annotated reducer)
- **재시도 시**: Critic의 `instrument_issues`를 프롬프트에 주입하여 문제 수정 요청
- **출력 (Pydantic)**: `TrackOutput` — Tone.js 호환 JSON
  ```json
  {
    "instrument": "Bass",
    "notes": [
      { "time": "0:0:0", "note": "A2", "duration": "4n" },
      { "time": "0:1:0", "note": "E2", "duration": "4n" }
    ]
  }
  ```

### Critic Agent

- **입력**: 전체 `tracks` + 음악 컨텍스트 (scale, tempo, chord)
- **처리**: LangChain LCEL 체인
  ```
  ChatPromptTemplate | ChatAnthropic.with_structured_output(CriticOutput)
  ```
- **출력 (Pydantic)**: `CriticOutput` — `quality_score (0-1)`, `feedback`, `instrument_issues`

---

## 4. 그래프 구조

### 전체 생성 (`/generate`)

```
입력 (이미지/텍스트)
  → mood_agent
  → music_agent  (RAG 조회 포함)
  → [Bass, Kick, Pluck, Brass, Strings] 병렬 실행   ← LangGraph Send API
  → critic_agent
  → quality_score >= 0.75? ──Yes──→ finalize → 반환
          │ No
          └─→ 문제 악기만 재생성 → critic_agent → ... (최대 max_retries)
```

### 부분 재생성 (`/regenerate`)

```
사용자 지정 악기 (예: ["kick"])
  → [Kick만 재생성]   ← mood/music 단계 스킵 (별도 regen_graph)
  → critic_agent
  → finalize → 반환
```

---

## 5. API 엔드포인트

| Method | Path           | 설명                           |
| ------ | -------------- | ------------------------------ |
| `POST` | `/generate`    | 이미지/텍스트 → 전체 음악 생성 |
| `POST` | `/regenerate`  | 특정 악기만 선택 재생성        |
| `GET`  | `/instruments` | 지원 악기 목록 반환            |
| `GET`  | `/health`      | 헬스체크                       |

### `/generate` 요청 (multipart/form-data)

| 필드          | 타입              | 설명                    |
| ------------- | ----------------- | ----------------------- |
| `image`       | File (optional)   | 분위기 분석용 이미지    |
| `text`        | string (optional) | 사용자 텍스트 프롬프트  |
| `max_retries` | int (default: 2)  | Critic 재시도 최대 횟수 |

### `/regenerate` 요청 (JSON)

```json
{
  "instruments": ["kick"],
  "mood_keywords": ["dark", "melancholic"],
  "tempo": 85,
  "scale": "A Minor",
  "color_profile": "deep blues",
  "chord_progression": ["Am", "F", "C", "G"],
  "song_structure": { "intro": {}, "main": {}, "outro": {} },
  "music_guide": { "kick": "four-on-the-floor pattern" },
  "existing_tracks": { "bass": {}, "pluck": {} }
}
```

---

## 6. Pydantic 스키마 (`agents/schemas.py`)

```python
MoodOutput    → mood_keywords, tempo (60-180 BPM), scale, color_profile
MusicOutput   → chord_progression, song_structure, music_guide
TrackOutput   → instrument, notes: list[NoteEvent]
NoteEvent     → time ("0:0:0"), note ("A2"), duration ("4n")
CriticOutput  → quality_score (0.0-1.0), feedback, instrument_issues
```

---

## 7. 프로젝트 구조

```
backend/
├── main.py                        # FastAPI 앱 (엔드포인트)
├── state.py                       # LangGraph MusicState 정의
├── graph.py                       # 그래프 조립 (full_graph / regen_graph)
├── requirements.txt
├── .env.example
├── agents/
│   ├── schemas.py                 # Pydantic 출력 스키마 (전 에이전트 공용)
│   ├── mood_agent.py              # Anthropic SDK + Pydantic + Langfuse
│   ├── music_agent.py             # LangChain LCEL + Pydantic + Langfuse
│   ├── critic_agent.py            # LangChain LCEL + Pydantic + Langfuse
│   ├── orchestrator.py            # 재시도 라우팅 로직
│   └── instruments/
│       ├── base_instrument.py     # 공통 생성 로직 + Pydantic + Langfuse
│       ├── bass.py
│       ├── kick.py
│       ├── pluck.py
│       ├── brass.py
│       └── strings.py
└── rag/
    └── music_kb.py                # ChromaDB + 음악 이론 시드 데이터
```

---

## 8. 실행 방법

```bash
cd backend
cp .env.example .env
# .env에 ANTHROPIC_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY 입력

pip install -r requirements.txt
uvicorn main:app --reload
```

Langfuse 대시보드 (`https://cloud.langfuse.com`)에서 `/generate` 호출마다
에이전트별 토큰 사용량, 지연시간, 입출력을 실시간 확인 가능.
