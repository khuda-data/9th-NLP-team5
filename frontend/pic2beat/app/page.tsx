"use client";

import { useState, useRef, useCallback } from "react";
import MusicPlayer from "./components/MusicPlayer";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface NoteEvent {
  time: string;
  note: string;
  duration: string;
}

interface TrackOutput {
  instrument: string;
  notes: NoteEvent[];
}

interface GenerateResult {
  mood: {
    keywords: string[];
    tempo: number;
    scale: string;
  };
  chord_progression: string[];
  tracks: TrackOutput[];
  quality_score: number;
}

export default function Home() {
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) {
      setError("이미지 파일만 업로드할 수 있어요.");
      return;
    }
    setImage(file);
    setPreview(URL.createObjectURL(file));
    setError(null);
    setResult(null);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleSubmit = async () => {
    if (!image && !text.trim()) {
      setError("이미지 또는 텍스트 중 하나는 필요해요.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const form = new FormData();
      if (image) form.append("image", image);
      if (text.trim()) form.append("text", text.trim());

      const res = await fetch(`${API_BASE}/generate`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? `서버 오류 (${res.status})`);
      }

      const data: GenerateResult = await res.json();
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "알 수 없는 오류가 발생했어요.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setImage(null);
    setPreview(null);
    setText("");
    setResult(null);
    setError(null);
  };

  return (
    <main className="min-h-screen bg-[#0d0d0d] text-white flex flex-col items-center px-4 py-12">
      {/* 헤더 */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold tracking-tight mb-2">🎵 Pic to Beat</h1>
        <p className="text-gray-400 text-sm">이미지를 올리면 AI가 음악을 만들어드려요</p>
      </div>

      <div className="w-full max-w-xl flex flex-col gap-5">
        {/* 이미지 업로드 영역 */}
        <div
          className={`relative rounded-2xl border-2 border-dashed transition-colors cursor-pointer
            ${dragOver ? "border-purple-400 bg-purple-950/30" : "border-gray-600 hover:border-gray-400"}
            ${preview ? "border-solid border-gray-600" : ""}
          `}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => !preview && fileInputRef.current?.click()}
        >
          {preview ? (
            <div className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={preview}
                alt="업로드된 이미지"
                className="w-full rounded-2xl object-cover max-h-72"
              />
              <button
                onClick={(e) => { e.stopPropagation(); handleReset(); }}
                className="absolute top-2 right-2 bg-black/60 hover:bg-black/80 text-white text-xs px-2 py-1 rounded-lg transition"
              >
                ✕ 제거
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-14 gap-3 text-gray-500">
              <span className="text-4xl">🖼️</span>
              <p className="text-sm">이미지를 드래그하거나 클릭해서 업로드</p>
              <p className="text-xs text-gray-600">JPG, PNG, WEBP, GIF 지원</p>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />
        </div>

        {/* 텍스트 입력 */}
        <div className="flex flex-col gap-1">
          <label className="text-xs text-gray-400">텍스트로 분위기 추가 (선택)</label>
          <textarea
            className="bg-[#1a1a1a] border border-gray-700 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 resize-none focus:outline-none focus:border-purple-500 transition"
            rows={2}
            placeholder="예: 비 오는 밤, 조용하고 감성적인 분위기"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>

        {/* 에러 메시지 */}
        {error && (
          <p className="text-red-400 text-sm text-center">{error}</p>
        )}

        {/* 생성 버튼 */}
        <button
          onClick={handleSubmit}
          disabled={loading || (!image && !text.trim())}
          className="bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition text-sm"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin inline-block">⏳</span> 음악 생성 중...
            </span>
          ) : (
            "✨ 음악 생성하기"
          )}
        </button>

        {/* 결과 */}
        {result && (
          <div className="bg-[#1a1a1a] border border-gray-700 rounded-2xl p-5 flex flex-col gap-4">
            <h2 className="text-base font-semibold text-purple-300">생성 결과</h2>

            {/* 무드 키워드 */}
            <div>
              <p className="text-xs text-gray-500 mb-1">무드</p>
              <div className="flex flex-wrap gap-2">
                {result.mood.keywords.map((kw) => (
                  <span key={kw} className="bg-purple-900/50 text-purple-200 text-xs px-3 py-1 rounded-full">
                    {kw}
                  </span>
                ))}
              </div>
            </div>

            {/* 음악 정보 */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#111] rounded-xl p-3">
                <p className="text-xs text-gray-500">BPM</p>
                <p className="text-lg font-bold">{result.mood.tempo}</p>
              </div>
              <div className="bg-[#111] rounded-xl p-3">
                <p className="text-xs text-gray-500">스케일</p>
                <p className="text-lg font-bold">{result.mood.scale}</p>
              </div>
            </div>

            {/* 코드 진행 */}
            <div>
              <p className="text-xs text-gray-500 mb-1">코드 진행</p>
              <div className="flex gap-2 flex-wrap">
                {result.chord_progression.map((chord, i) => (
                  <span key={i} className="bg-[#111] border border-gray-700 text-white text-sm px-3 py-1 rounded-lg font-mono">
                    {chord}
                  </span>
                ))}
              </div>
            </div>

            {/* 음악 플레이어 */}
            <div className="border-t border-gray-700 pt-4">
              <MusicPlayer tracks={result.tracks} tempo={result.mood.tempo} />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
