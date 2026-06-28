"""
라이브 스모크 테스트 (로컬 전용).
실제 Anthropic 호출까지 포함해 /generate 전체 경로를 검증한다.

사용법:
  1) .env 에 ANTHROPIC_API_KEY 채우기 (절대 코드/채팅에 하드코딩 X)
  2) 서버 실행:   ./run.sh         (또는 docker compose up --build)
  3) 다른 터미널:  python smoke_live.py  [--text "..."] [--image path.jpg] [--url http://localhost:8000]

키는 이 스크립트가 직접 읽지 않는다. 서버 프로세스(.env)만 키를 갖는다.
"""
import argparse, json, sys, urllib.request, urllib.error


def post_generate(base, text=None, image=None, max_retries=2):
    url = base.rstrip("/") + "/generate"
    boundary = "----pictobeatsmoke"
    parts = []

    def field(name, value):
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(f"{value}\r\n".encode())

    if text:
        field("text", text)
    field("max_retries", str(max_retries))
    if image:
        with open(image, "rb") as f:
            data = f.read()
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            f'Content-Disposition: form-data; name="image"; filename="{image}"\r\n'.encode()
        )
        parts.append(b"Content-Type: image/jpeg\r\n\r\n")
        parts.append(data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode())


def validate(out):
    checks = []
    def ck(name, cond): checks.append((name, bool(cond)))

    ck("final_output 존재", isinstance(out, dict))
    ck("mood.keywords 있음", out.get("mood", {}).get("keywords"))
    ck("tempo 정수", isinstance(out.get("mood", {}).get("tempo"), int))
    ck("chord_progression 2+", len(out.get("chord_progression", [])) >= 2)
    tracks = out.get("tracks", [])
    ck("tracks 1+", len(tracks) >= 1)
    # 각 트랙 노트의 Tone.js 형식 대략 검증
    note_ok = True
    for t in tracks:
        for n in t.get("notes", []):
            if not (n.get("time", "").count(":") == 2 and n.get("note") and n.get("duration")):
                note_ok = False
    ck("노트 Tone.js 형식(measure:beat:sub)", tracks and note_ok)
    ck("quality_score 범위", 0.0 <= out.get("quality_score", -1) <= 1.0)
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--text", default="비 오는 밤, 쓸쓸한 도시의 네온사인")
    ap.add_argument("--image", default=None)
    ap.add_argument("--max-retries", type=int, default=2)
    args = ap.parse_args()

    # 헬스 먼저
    try:
        with urllib.request.urlopen(args.url.rstrip("/") + "/health", timeout=10) as r:
            assert json.loads(r.read())["status"] == "ok"
        print(f"[*] 서버 살아있음: {args.url}")
    except Exception as e:
        print(f"[X] 서버에 못 붙음 ({args.url}). 먼저 ./run.sh 로 서버 띄워. ({e})")
        sys.exit(1)

    print(f"[*] /generate 호출... (text={args.text!r}, image={args.image})")
    try:
        out = post_generate(args.url, args.text, args.image, args.max_retries)
    except urllib.error.HTTPError as e:
        print(f"[X] HTTP {e.code}: {e.read().decode()[:500]}")
        sys.exit(1)

    print("\n--- 응답 요약 ---")
    print("mood:", out.get("mood"))
    print("chords:", out.get("chord_progression"))
    print("tracks:", [t.get("instrument") for t in out.get("tracks", [])])
    print("score:", out.get("quality_score"))

    print("\n--- 검증 ---")
    ok_all = True
    for name, ok in validate(out):
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        ok_all = ok_all and ok
    print("\n결과:", "전체 통과 ✅" if ok_all else "일부 실패 ❌")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
