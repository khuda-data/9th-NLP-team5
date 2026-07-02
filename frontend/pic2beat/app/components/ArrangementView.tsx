"use client";

import { useRef, useCallback } from "react";

interface NoteEvent {
  time: string;
  note: string;
  duration: string;
}

interface TrackOutput {
  instrument: string;
  notes: NoteEvent[];
}

interface ArrangementViewProps {
  tracks: TrackOutput[];
  currentBeat: number;
  onSeek: (beat: number) => void;
}

const DURATION_TO_BEATS: Record<string, number> = {
  "1n": 4, "2n": 2, "4n": 1, "8n": 0.5, "16n": 0.25,
  "2t": 4 / 3, "4t": 2 / 3, "8t": 1 / 3,
};

const TRACK_COLORS: Record<string, { block: string; row: string; label: string }> = {
  bass:    { block: "#3b82f6", row: "#0f172a", label: "#93c5fd" },
  kick:    { block: "#ef4444", row: "#1a0a0a", label: "#fca5a5" },
  pluck:   { block: "#22c55e", row: "#0a1a0a", label: "#86efac" },
  brass:   { block: "#eab308", row: "#1a1500", label: "#fde047" },
  strings: { block: "#a855f7", row: "#12001a", label: "#d8b4fe" },
};

const TRACK_ICONS: Record<string, string> = {
  bass: "🎸", kick: "🥁", pluck: "🎹", brass: "🎺", strings: "🎻",
};

function timeToBeats(time: string): number {
  const [m = 0, b = 0, s = 0] = time.split(":").map(Number);
  return m * 4 + b + s / 4;
}

function durationToBeats(dur: string): number {
  return DURATION_TO_BEATS[dur] ?? 1;
}

const ROW_H = 40;
const BEAT_W = 20;
const LABEL_W = 72;
const HEADER_H = 24;

export default function ArrangementView({ tracks, currentBeat, onSeek }: ArrangementViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const isDragging = useRef(false);

  if (!tracks.length) return null;

  const totalBeats = Math.max(
    ...tracks.flatMap((t) =>
      t.notes.map((n) => timeToBeats(n.time) + durationToBeats(n.duration))
    ),
    8
  );
  const totalBars = Math.ceil(totalBeats / 4);
  const totalBeatsCeil = totalBars * 4;

  const svgW = LABEL_W + totalBeatsCeil * BEAT_W;
  const svgH = HEADER_H + tracks.length * ROW_H;

  const beatFromMouseX = useCallback((clientX: number): number => {
    const svg = svgRef.current;
    if (!svg) return 0;
    const rect = svg.getBoundingClientRect();
    const x = clientX - rect.left - LABEL_W;
    return Math.max(0, Math.min(x / BEAT_W, totalBeatsCeil));
  }, [totalBeatsCeil]);

  const handleMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true;
    onSeek(beatFromMouseX(e.clientX));
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current) return;
    onSeek(beatFromMouseX(e.clientX));
  };

  const handleMouseUp = () => {
    isDragging.current = false;
  };

  const playheadX = LABEL_W + currentBeat * BEAT_W;

  return (
    <div className="overflow-x-auto rounded-xl bg-[#0a0a0a] border border-gray-800">
      <svg
        ref={svgRef}
        width={svgW}
        height={svgH}
        style={{ display: "block", minWidth: svgW, cursor: "crosshair" }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* 헤더 배경 */}
        <rect x={0} y={0} width={svgW} height={HEADER_H} fill="#111" />
        <rect x={0} y={0} width={LABEL_W} height={svgH} fill="#0d0d0d" />

        {/* 마디 번호 + 세로선 */}
        {Array.from({ length: totalBars + 1 }, (_, bar) => {
          const x = LABEL_W + bar * 4 * BEAT_W;
          return (
            <g key={`bar-${bar}`}>
              <line x1={x} y1={0} x2={x} y2={svgH} stroke="#2a2a2a" strokeWidth={1} />
              {bar < totalBars && (
                <text x={x + 4} y={HEADER_H - 6} fontSize={10} fill="#555" fontFamily="monospace">
                  {bar + 1}
                </text>
              )}
            </g>
          );
        })}

        {/* 비트 세로선 */}
        {Array.from({ length: totalBeatsCeil }, (_, beat) =>
          beat % 4 !== 0 ? (
            <line
              key={`beat-${beat}`}
              x1={LABEL_W + beat * BEAT_W}
              y1={HEADER_H}
              x2={LABEL_W + beat * BEAT_W}
              y2={svgH}
              stroke="#1a1a1a"
              strokeWidth={1}
            />
          ) : null
        )}

        {/* 트랙 행 */}
        {tracks.map((track, ti) => {
          const name = track.instrument.toLowerCase();
          const colors = TRACK_COLORS[name] ?? { block: "#a855f7", row: "#111", label: "#d8b4fe" };
          const icon = TRACK_ICONS[name] ?? "🎵";
          const y = HEADER_H + ti * ROW_H;

          return (
            <g key={name}>
              <rect x={LABEL_W} y={y} width={svgW - LABEL_W} height={ROW_H} fill={colors.row} />
              <line x1={0} y1={y + ROW_H} x2={svgW} y2={y + ROW_H} stroke="#1f1f1f" strokeWidth={1} />
              <text x={8} y={y + ROW_H / 2 - 4} fontSize={10} fill={colors.label} fontFamily="sans-serif" fontWeight="bold">
                {icon} {name}
              </text>
              <text x={8} y={y + ROW_H / 2 + 9} fontSize={9} fill="#444" fontFamily="monospace">
                {track.notes.length} notes
              </text>

              {track.notes.map((n, ni) => {
                const startBeat = timeToBeats(n.time);
                const durBeats = durationToBeats(n.duration);
                const x = LABEL_W + startBeat * BEAT_W;
                const w = Math.max(durBeats * BEAT_W - 1, 2);
                return (
                  <g key={ni}>
                    <rect x={x} y={y + 4} width={w} height={ROW_H - 8} rx={2} fill={colors.block} opacity={0.8} />
                    <rect x={x} y={y + 4} width={w} height={3} rx={2} fill="white" opacity={0.25} />
                    {w > 18 && (
                      <text x={x + 3} y={y + ROW_H / 2 + 4} fontSize={8} fill="white" fontFamily="monospace" opacity={0.9}>
                        {n.note}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* 라벨 구분선 */}
        <line x1={LABEL_W} y1={0} x2={LABEL_W} y2={svgH} stroke="#333" strokeWidth={1} />
        <line x1={0} y1={HEADER_H} x2={svgW} y2={HEADER_H} stroke="#333" strokeWidth={1} />

        {/* 플레이헤드 */}
        {playheadX >= LABEL_W && (
          <g style={{ pointerEvents: "none" }}>
            {/* 헤더 삼각형 핸들 */}
            <polygon
              points={`${playheadX - 5},0 ${playheadX + 5},0 ${playheadX},${HEADER_H}`}
              fill="#ffffff"
              opacity={0.9}
            />
            {/* 세로선 */}
            <line
              x1={playheadX}
              y1={HEADER_H}
              x2={playheadX}
              y2={svgH}
              stroke="white"
              strokeWidth={1.5}
              opacity={0.8}
            />
          </g>
        )}
      </svg>
    </div>
  );
}
