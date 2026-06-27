# Pic to Beat — Orchestrator 서버 (BE)

이미지/텍스트 → 멀티에이전트 협업 → Tone.js로 재생 가능한 음악(JSON)을 만들어 주는 백엔드.
기획서의 에이전트 구조(Orchestrator → Mood / Music·Performers / Critic)를 그대로 골격으로 구현했다.

**지금 상태:** 실제 LLM 없이도 "규칙 기반 더미"로 실제 소리나는 음악이 생성된다 → 연결·재생·UI를 먼저 완성하고, AI는 나중에 끼우면 된다.

```
프론트(React/Tone.js)
      │  POST /api/generate
      ▼
 Orchestrator ──┬─ Mood Agent        (이미지/텍스트 → 분위기·key·BPM·코드)
                ├─ Performer Agents   (Bass/Kick/Pluck/Brass/Strings ... 병렬 생성)
                └─ Critic Agent       (평가 → 부족한 트랙만 재생성)
      │
      ▼  state(JSON) = 모든 트랙의 Tone.js 음표
프론트가 Tone.js로 재생 / 트랙별 수정
```

---

## 1. 실행 (로컬)

```bash
pip install -r requirements.txt
python main.py          # 또는: uvicorn main:app --reload
```

- 확인: `http://localhost:8000/api/health` → `{"status":"ok"}`
- 자동 테스트 화면: `http://localhost:8000/docs`
- **소리까지 테스트:** `frontend-example.html` 을 브라우저로 열고 → ① 생성 → ▶ 재생
  (에이전트 진행상황이 개발자 모드 로그에 흐르고, 트랙별 "↻" 버튼으로 부분 갱신도 됨)

---

## 2. 파일 구조 (어디를 채우면 되는지)

| 파일 | 역할 | 네가 만질 일 |
|------|------|--------------|
| `schemas.py` | 프론트와 주고받는 데이터 모양(State, 음표) | 거의 없음 |
| `agents.py` | **에이전트들 + LLM 호출 자리** | ⭐ 여기를 채움 |
| `orchestrator.py` | 병렬 실행·Critic 루프·부분 갱신 흐름 | 거의 없음 |
| `main.py` | HTTP 엔드포인트 | 거의 없음 |
| `frontend-example.html` | 재생/테스트용 | 참고용 |

---

## 3. AI(LLM) 끼우기

핵심은 `agents.py` 의 **`call_llm()` 한 곳**. 여기에 Claude(또는 로컬모델) 호출을 채우면
Mood / Performer / Critic 전부가 LLM에 연결된다.

```python
async def call_llm(prompt, image_base64=None, model="claude"):
    from anthropic import AsyncAnthropic
    import os
    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = await client.messages.create(
        model="claude-sonnet-4-6", max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text
```

그 다음:
1. 각 에이전트의 `prompt` 와 응답 파서(`_parse_mood` / `_parse_track` / `_parse_critic`)를 채운다.
2. 환경변수 `USE_LLM=1` 로 켠다 → 더미 대신 진짜 LLM 동작.
3. 로컬 경량 모델을 쓸 땐 `call_llm` 의 `model` 분기에서 다른 호출을 추가하면 된다.

API 키는 코드에 직접 쓰지 말고 환경변수(`.env` 또는 배포 플랫폼 설정)에 둘 것.

---

## 4. 엔드포인트 (프론트 담당자에게 전달)

| 주소 | 용도 | 보냄 | 받음 |
|------|------|------|------|
| `POST /api/generate` | 곡 전체 생성 | `{prompt 또는 image_base64, instruments}` | `{state, timing_ms}` |
| `POST /api/revise` | 트랙만 부분 갱신 | `{state, targets:[...]}` | 갱신된 `{state}` |
| `POST /api/generate/stream` | 개발자 모드(실시간 진행) | 위와 동일 | SSE 이벤트 스트림 |
| `GET /api/health` | 상태 확인 | — | `{status}` |

`state.tracks` 의 각 음표는 Tone.js `Part` 에 그대로 넣어 재생할 수 있는 형태
(`{time, note, duration, velocity}`). 호출/재생 예시는 `frontend-example.html` 참고.

---

## 5. 배포 (서버리스 대신 일반 서버를 추천하는 이유)

이 프로젝트는 **로컬 모델 + 멀티에이전트 병렬 + 긴 처리시간 + 상태 유지 + 스트리밍**이라
서버리스(Vercel 등)의 stateless·타임아웃 제약과 잘 안 맞는다. 대신:

- **Railway / Render**: git 연결하면 자동 배포(서버리스만큼 간단)이면서, 상시 서버라
  로컬 모델·긴 처리·스트리밍·State 유지가 모두 된다. → **가장 추천**
- 직접 서버(VM)에 `uvicorn` + 프로세스 관리자(예: systemd, pm2)로 올려도 됨.

배포 시 환경변수(`ANTHROPIC_API_KEY`, `USE_LLM=1`)를 플랫폼 설정에 넣는다.
```
```
