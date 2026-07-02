"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import MusicPlayer from "../components/MusicPlayer";
import ArrangementView from "../components/ArrangementView";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface NoteEvent { time: string; note: string; duration: string; }
interface TrackOutput { instrument: string; notes: NoteEvent[]; }
interface GenerateResult {
  mood: { keywords: string[]; tempo: number; scale: string; };
  chord_progression: string[];
  tracks: TrackOutput[];
  quality_score: number;
}

const ALL_INSTRUMENTS = ["bass", "kick", "pluck", "brass", "strings"];

const TRACK_ICONS: Record<string, string> = {
  bass: "🎸", kick: "🥁", pluck: "🎹", brass: "🎺", strings: "🎻",
};

const TRACK_COLORS: Record<string, string> = {
  bass: "border-blue-700 bg-blue-900/30",
  kick: "border-red-700 bg-red-900/30",
  pluck: "border-green-700 bg-green-900/30",
  brass: "border-yellow-700 bg-yellow-900/30",
  strings: "border-pink-700 bg-pink-900/30",
};

export default function EditPage() {
  const router = useRouter();
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [hint, setHint] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentBeat, setCurrentBeat] = useState(0);

  useEffect(() => {
    const raw = localStorage.getItem("pic2beat_result");
    if (!raw) { router.push("/"); return; }
    setResult(JSON.parse(raw));
  }, [router]);

  const toggleInstrument = (name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const handleRegenerate = async () => {
    if (!result || selected.size === 0) return;
    setLoading(true);
    setError(null);

    // tracks 배열 → dict 변환
    const existingTracks: Record<string, TrackOutput> = {};
    result.tracks.forEach((t) => {
      existingTracks[t.instrument.toLowerCase()] = t;
    });

    const body = {
      instruments: Array.from(selected),
      mood_keywords: result.mood.keywords,
      tempo: result.mood.tempo,
      scale: result.mood.scale,
      color_profile: hint.trim() || "",   // 힌트를 color_profile에 추가
      chord_progression: result.chord_progression,
      song_structure: {},
      music_guide: hint.trim()
        ? Object.fromEntries(Array.from(selected).map((inst) => [inst, hint.trim()]))
        : {},
      existing_tracks: existingTracks,
    };

    try {
      const res = await fetch(`${API_BASE}/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? `서버 오류 (${res.status})`);
      }

      const data: GenerateResult = await res.json();
      setResult(data);
      localStorage.setItem("pic2beat_result", JSON.stringify(data));
      setSelected(new Set());
      setHint("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "알 수 없는 오류가 발생했어요.");
    } finally {
      setLoading(false);
    }
  };

  if (!result) return (
    <main className="min-h-screen bg-[#0d0d0d] text-white flex items-center justify-center">
      <p className="text-gray-400">불러오는 중...</p>
    </main>
  );

  const existingInstruments = new Set(result.tracks.map((t) => t.instrument.toLowerCase()));

  return (
    <main className="min-h-screen bg-[#0d0d0d] text-white flex flex-col items-center px-4 py-10">
      {/* 헤더 */}
      <div className="w-full max-w-2xl flex items-center gap-3 mb-8">
        <button
          onClick={() => router.push("/")}
          className="text-gray-400 hover:text-white text-sm transition"
        >
          ← 홈
        </button>
        <h1 className="text-2xl font-bold">✏️ 편집</h1>
      </div>

      <div className="w-full max-w-2xl flex flex-col gap-6">

        {/* 현재 곡 정보 */}
        <div className="bg-[#1a1a1a] border border-gray-700 rounded-2xl p-4 flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-gray-300">현재 곡</h2>
          <div className="flex flex-wrap gap-2">
            {result.mood.keywords.map((kw) => (
              <span key={kw} className="bg-purple-900/50 text-purple-200 text-xs px-3 py-1 rounded-full">{kw}</span>
            ))}
          </div>
          <div className="flex gap-3 text-sm">
            <span className="text-gray-500">BPM <span className="text-white font-bold">{result.mood.tempo}</span></span>
            <span className="text-gray-500">스케일 <span className="text-white font-bold">{result.mood.scale}</span></span>
          </div>
          <div className="flex gap-2 flex-wrap">
            {result.chord_progression.map((c, i) => (
              <span key={i} className="bg-[#111] border border-gray-700 text-xs px-2 py-1 rounded font-mono">{c}</span>
            ))}
          </div>
        </div>

        {/* 전체 배치 뷰 */}
        <ArrangementView tracks={result.tracks} currentBeat={currentBeat} onSeek={setCurrentBeat} />

        {/* 악기 선택 */}
        <div className="bg-[#1a1a1a] border border-gray-700 rounded-2xl p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-300">재생성할 악기 선택</h2>
            <div className="flex gap-2">
              <button
                onClick={() => setSelected(new Set(ALL_INSTRUMENTS.filter(i => existingInstruments.has(i))))}
                className="text-xs text-purple-400 hover:text-purple-300 transition"
              >
                전체 선택
              </button>
              <span className="text-gray-600">|</span>
              <button
                onClick={() => setSelected(new Set())}
                className="text-xs text-gray-400 hover:text-gray-300 transition"
              >
                전체 해제
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            {ALL_INSTRUMENTS.map((inst) => {
              const exists = existingInstruments.has(inst);
              const checked = selected.has(inst);
              const colorClass = TRACK_COLORS[inst] ?? "border-gray-700 bg-gray-800/30";
              return (
                <label
                  key={inst}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition
                    ${exists ? colorClass : "border-gray-800 bg-gray-900/20 opacity-40 cursor-not-allowed"}
                    ${checked ? "ring-1 ring-purple-500" : ""}
                  `}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={!exists}
                    onChange={() => exists && toggleInstrument(inst)}
                    className="accent-purple-500 w-4 h-4"
                  />
                  <span className="text-lg">{TRACK_ICONS[inst]}</span>
                  <span className="text-sm capitalize flex-1">{inst}</span>
                  {exists
                    ? <span className="text-xs text-gray-500">{result.tracks.find(t => t.instrument.toLowerCase() === inst)?.notes.length}개 노트</span>
                    : <span className="text-xs text-gray-600">없음</span>
                  }
                </label>
              );
            })}
          </div>
        </div>

        {/* 힌트 입력 */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-semibold text-gray-300">
            작곡 힌트 <span className="text-gray-600 font-normal">(선택 — 선택한 악기에 반영)</span>
          </label>
          <textarea
            className="bg-[#1a1a1a] border border-gray-700 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 resize-none focus:outline-none focus:border-purple-500 transition"
            rows={3}
            placeholder="예: 더 낮고 묵직하게, 8분음표 위주로, 어두운 분위기로"
            value={hint}
            onChange={(e) => setHint(e.target.value)}
          />
        </div>

        {/* 에러 */}
        {error && <p className="text-red-400 text-sm text-center">{error}</p>}

        {/* 재생성 버튼 */}
        <button
          onClick={handleRegenerate}
          disabled={loading || selected.size === 0}
          className="bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition text-sm"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin inline-block">⏳</span>
              {Array.from(selected).join(", ")} 재생성 중...
            </span>
          ) : selected.size > 0
            ? `🎵 ${Array.from(selected).join(", ")} 재생성`
            : "악기를 선택해주세요"
          }
        </button>

        {/* 플레이어 */}
        <div className="bg-[#1a1a1a] border border-gray-700 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">플레이어</h2>
          <MusicPlayer tracks={result.tracks} tempo={result.mood.tempo} />
        </div>
      </div>
    </main>
  );
}
