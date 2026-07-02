"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import PianoRoll from "./PianoRoll";
import ArrangementView from "./ArrangementView";

interface NoteEvent {
  time: string;
  note: string;
  duration: string;
}

interface TrackOutput {
  instrument: string;
  notes: NoteEvent[];
}

interface MusicPlayerProps {
  tracks: TrackOutput[];
  tempo: number;
}

// 악기별 Tone.js 신디사이저 설정
const SYNTH_CONFIG: Record<string, object> = {
  bass: {
    oscillator: { type: "triangle" },
    envelope: { attack: 0.05, decay: 0.3, sustain: 0.4, release: 0.8 },
    volume: -6,
  },
  kick: {
    oscillator: { type: "sine" },
    envelope: { attack: 0.001, decay: 0.2, sustain: 0, release: 0.1 },
    volume: -3,
  },
  pluck: {
    oscillator: { type: "triangle" },
    envelope: { attack: 0.001, decay: 0.3, sustain: 0.1, release: 0.5 },
    volume: -8,
  },
  brass: {
    oscillator: { type: "sawtooth" },
    envelope: { attack: 0.05, decay: 0.1, sustain: 0.6, release: 0.4 },
    volume: -10,
  },
  strings: {
    oscillator: { type: "sine" },
    envelope: { attack: 0.2, decay: 0.1, sustain: 0.8, release: 1.0 },
    volume: -10,
  },
};

const TRACK_COLORS: Record<string, string> = {
  bass: "bg-blue-900/50 border-blue-700",
  kick: "bg-red-900/50 border-red-700",
  pluck: "bg-green-900/50 border-green-700",
  brass: "bg-yellow-900/50 border-yellow-700",
  strings: "bg-pink-900/50 border-pink-700",
};

const ROLL_COLORS: Record<string, string> = {
  bass: "#3b82f6",
  kick: "#ef4444",
  pluck: "#22c55e",
  brass: "#eab308",
  strings: "#ec4899",
};

const TRACK_ICONS: Record<string, string> = {
  bass: "🎸",
  kick: "🥁",
  pluck: "🎹",
  brass: "🎺",
  strings: "🎻",
};

const DURATION_LABEL: Record<string, string> = {
  "1n": "온음표", "2n": "2분음표", "4n": "4분음표",
  "8n": "8분음표", "16n": "16분음표", "2t": "3연음2분", "4t": "3연음4분",
};

export default function MusicPlayer({ tracks, tempo }: MusicPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [mutedTracks, setMutedTracks] = useState<Set<string>>(new Set());
  const [expandedTrack, setExpandedTrack] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [currentBeat, setCurrentBeat] = useState(0);
  const toneRef = useRef<typeof import("tone") | null>(null);
  const partsRef = useRef<unknown[]>([]);
  const synthsRef = useRef<Record<string, unknown>>({});
  const rafRef = useRef<number | null>(null);

  // Tone.js는 브라우저 전용이라 동적으로 로드
  useEffect(() => {
    import("tone").then((Tone) => {
      toneRef.current = Tone;
      setReady(true);
    });
    return () => {
      stopAll();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stopRaf = () => {
    if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = null; }
  };

  const startRaf = useCallback(() => {
    const Tone = toneRef.current;
    if (!Tone) return;
    const tick = () => {
      const pos = Tone.getTransport().position as string;
      const [m = 0, b = 0, s = 0] = pos.split(":").map(Number);
      setCurrentBeat(m * 4 + b + s / 4);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, []);

  const stopAll = () => {
    const Tone = toneRef.current;
    if (!Tone) return;
    stopRaf();
    (partsRef.current as { dispose: () => void }[]).forEach((p) => p.dispose());
    partsRef.current = [];
    Object.values(synthsRef.current as Record<string, { dispose: () => void }>).forEach((s) => s.dispose());
    synthsRef.current = {};
    Tone.getTransport().stop();
    Tone.getTransport().cancel();
  };

  const handleSeek = useCallback((beat: number) => {
    const Tone = toneRef.current;
    if (!Tone) return;
    const bar = Math.floor(beat / 4);
    const quarter = Math.floor(beat % 4);
    const sixteenth = Math.round((beat % 1) * 4);
    Tone.getTransport().position = `${bar}:${quarter}:${sixteenth}`;
    setCurrentBeat(beat);
  }, []);

  const handlePlay = async () => {
    const Tone = toneRef.current;
    if (!Tone) return;

    await Tone.start();
    stopAll();

    Tone.getTransport().bpm.value = tempo;

    const newSynths: Record<string, unknown> = {};
    const newParts: unknown[] = [];

    for (const track of tracks) {
      const name = track.instrument.toLowerCase();
      if (mutedTracks.has(name)) continue;

      const config = SYNTH_CONFIG[name] ?? SYNTH_CONFIG.pluck;
      const synth = new Tone.Synth(config as ConstructorParameters<typeof Tone.Synth>[0]).toDestination();
      newSynths[name] = synth;

      const part = new Tone.Part(
        (time: number, event: NoteEvent) => {
          (synth as { triggerAttackRelease: (note: string, duration: string, time: number) => void })
            .triggerAttackRelease(event.note, event.duration, time);
        },
        track.notes.map((n) => ({ time: n.time, note: n.note, duration: n.duration }))
      );
      part.start(0);
      newParts.push(part);
    }

    synthsRef.current = newSynths;
    partsRef.current = newParts;

    Tone.getTransport().start();
    setIsPlaying(true);
    startRaf();
  };

  const handleStop = () => {
    stopAll();
    setIsPlaying(false);
  };

  const toggleMute = (name: string) => {
    setMutedTracks((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
    // 재생 중이면 중단 (뮤트 반영을 위해 재시작 필요)
    if (isPlaying) handleStop();
  };

  return (
    <div className="flex flex-col gap-4">
      {/* DAW 배치도 */}
      <ArrangementView tracks={tracks} currentBeat={currentBeat} onSeek={handleSeek} />

      {/* 재생 컨트롤 */}
      <div className="flex items-center gap-3">
        {!isPlaying ? (
          <button
            onClick={handlePlay}
            disabled={!ready}
            className="flex-1 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition text-sm flex items-center justify-center gap-2"
          >
            ▶ 재생
          </button>
        ) : (
          <button
            onClick={handleStop}
            className="flex-1 bg-gray-700 hover:bg-gray-600 text-white font-semibold py-3 rounded-xl transition text-sm flex items-center justify-center gap-2"
          >
            ■ 정지
          </button>
        )}
        <div className="bg-[#111] rounded-xl px-4 py-3 text-center min-w-[80px]">
          <p className="text-xs text-gray-500">BPM</p>
          <p className="text-base font-bold">{tempo}</p>
        </div>
      </div>

      {/* 트랙 목록 */}
      <div className="flex flex-col gap-2">
        <p className="text-xs text-gray-500">트랙 (클릭하면 음계 확인)</p>
        {tracks.map((track) => {
          const name = track.instrument.toLowerCase();
          const muted = mutedTracks.has(name);
          const expanded = expandedTrack === name;
          const colorClass = TRACK_COLORS[name] ?? "bg-gray-800 border-gray-600";
          const icon = TRACK_ICONS[name] ?? "🎵";
          return (
            <div key={name} className={`rounded-xl border transition ${colorClass} ${muted ? "opacity-40" : "opacity-100"}`}>
              {/* 트랙 헤더 */}
              <div className="flex items-center px-4 py-2.5 gap-2">
                {/* 음계 펼치기 버튼 (트랙명 클릭) */}
                <button
                  onClick={() => setExpandedTrack(expanded ? null : name)}
                  className="flex-1 flex items-center gap-2 text-sm capitalize text-left"
                >
                  <span>{icon}</span>
                  <span>{name}</span>
                  <span className="text-xs text-gray-400">{track.notes.length}개 노트</span>
                  <span className="ml-auto text-gray-500 text-xs">{expanded ? "▲" : "▼"}</span>
                </button>
                {/* 뮤트 버튼 */}
                <button
                  onClick={() => toggleMute(name)}
                  className={`text-xs px-2 py-1 rounded-lg border transition ml-2 ${muted ? "border-gray-500 text-gray-500" : "border-gray-600 text-gray-300 hover:border-red-500 hover:text-red-400"}`}
                >
                  {muted ? "음소거" : "🔊"}
                </button>
              </div>

              {/* 피아노롤 (펼쳤을 때) */}
              {expanded && (
                <div className="px-3 pb-3">
                  <PianoRoll
                    notes={track.notes}
                    color={ROLL_COLORS[name] ?? "#a855f7"}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {isPlaying && (
        <p className="text-xs text-center text-purple-400 animate-pulse">♪ 재생 중...</p>
      )}
    </div>
  );
}
