"use client";

interface NoteEvent {
  time: string;
  note: string;
  duration: string;
}

interface PianoRollProps {
  notes: NoteEvent[];
  color: string; // tailwind hex color for notes
}

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const SHARP_NOTES = new Set(["C#", "D#", "F#", "G#", "A#"]);

const DURATION_TO_BEATS: Record<string, number> = {
  "1n": 4, "2n": 2, "4n": 1, "8n": 0.5, "16n": 0.25,
  "2t": 4 / 3, "4t": 2 / 3, "8t": 1 / 3,
};

function noteToMidi(note: string): number {
  const match = note.match(/^([A-G]#?)(-?\d+)$/);
  if (!match) return 60;
  const [, name, octave] = match;
  return (parseInt(octave) + 1) * 12 + NOTE_NAMES.indexOf(name);
}

function midiToName(midi: number): string {
  const octave = Math.floor(midi / 12) - 1;
  const name = NOTE_NAMES[midi % 12];
  return `${name}${octave}`;
}

function timeToBeats(time: string): number {
  const parts = time.split(":").map(Number);
  const [m = 0, b = 0, s = 0] = parts;
  return m * 4 + b + s / 4;
}

function durationToBeats(dur: string): number {
  return DURATION_TO_BEATS[dur] ?? 1;
}

const ROW_H = 20;
const BEAT_W = 48;
const LABEL_W = 44;

export default function PianoRoll({ notes, color }: PianoRollProps) {
  if (!notes.length) return null;

  // 음계 범위 계산
  const midis = notes.map((n) => noteToMidi(n.note));
  const minMidi = Math.min(...midis) - 1;
  const maxMidi = Math.max(...midis) + 1;
  const pitchCount = maxMidi - minMidi + 1;

  // 전체 길이 계산
  const totalBeats = Math.max(
    ...notes.map((n) => timeToBeats(n.time) + durationToBeats(n.duration)),
    4
  );
  const totalBeatsCeil = Math.ceil(totalBeats / 4) * 4; // 마디 단위로 올림

  const svgW = LABEL_W + totalBeatsCeil * BEAT_W;
  const svgH = pitchCount * ROW_H;

  return (
    <div className="overflow-x-auto rounded-lg bg-black/40">
      <svg
        width={svgW}
        height={svgH}
        style={{ display: "block", minWidth: svgW }}
      >
        {/* 행 배경 (피치별) */}
        {Array.from({ length: pitchCount }, (_, i) => {
          const midi = maxMidi - i;
          const name = NOTE_NAMES[midi % 12];
          const isSharp = SHARP_NOTES.has(name);
          return (
            <rect
              key={`row-${midi}`}
              x={0}
              y={i * ROW_H}
              width={svgW}
              height={ROW_H}
              fill={isSharp ? "#1a1a1a" : "#111"}
            />
          );
        })}

        {/* 마디 구분선 */}
        {Array.from({ length: Math.ceil(totalBeatsCeil / 4) + 1 }, (_, bar) => (
          <line
            key={`bar-${bar}`}
            x1={LABEL_W + bar * 4 * BEAT_W}
            y1={0}
            x2={LABEL_W + bar * 4 * BEAT_W}
            y2={svgH}
            stroke="#444"
            strokeWidth={1}
          />
        ))}

        {/* 비트 구분선 */}
        {Array.from({ length: totalBeatsCeil }, (_, beat) => (
          beat % 4 !== 0 && (
            <line
              key={`beat-${beat}`}
              x1={LABEL_W + beat * BEAT_W}
              y1={0}
              x2={LABEL_W + beat * BEAT_W}
              y2={svgH}
              stroke="#2a2a2a"
              strokeWidth={1}
            />
          )
        ))}

        {/* 피치 라벨 */}
        {Array.from({ length: pitchCount }, (_, i) => {
          const midi = maxMidi - i;
          const label = midiToName(midi);
          const name = NOTE_NAMES[midi % 12];
          const isSharp = SHARP_NOTES.has(name);
          return (
            <g key={`label-${midi}`}>
              <rect x={0} y={i * ROW_H} width={LABEL_W} height={ROW_H} fill={isSharp ? "#222" : "#1a1a1a"} />
              <text
                x={LABEL_W - 6}
                y={i * ROW_H + ROW_H / 2 + 4}
                textAnchor="end"
                fontSize={10}
                fill={isSharp ? "#888" : "#bbb"}
                fontFamily="monospace"
              >
                {label}
              </text>
              {/* 라벨 구분선 */}
              <line x1={0} y1={i * ROW_H} x2={svgW} y2={i * ROW_H} stroke="#222" strokeWidth={1} />
            </g>
          );
        })}

        {/* 노트 블록 */}
        {notes.map((n, i) => {
          const midi = noteToMidi(n.note);
          const rowIdx = maxMidi - midi;
          const startBeat = timeToBeats(n.time);
          const durBeats = durationToBeats(n.duration);
          const x = LABEL_W + startBeat * BEAT_W;
          const y = rowIdx * ROW_H + 2;
          const w = Math.max(durBeats * BEAT_W - 2, 4);
          const h = ROW_H - 4;
          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={w}
                height={h}
                rx={3}
                fill={color}
                opacity={0.85}
              />
              {w > 20 && (
                <text
                  x={x + 4}
                  y={y + h / 2 + 4}
                  fontSize={9}
                  fill="white"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  {n.note}
                </text>
              )}
            </g>
          );
        })}

        {/* 마디 번호 */}
        {Array.from({ length: Math.ceil(totalBeatsCeil / 4) }, (_, bar) => (
          <text
            key={`barnum-${bar}`}
            x={LABEL_W + bar * 4 * BEAT_W + 3}
            y={10}
            fontSize={9}
            fill="#555"
            fontFamily="monospace"
          >
            {bar + 1}
          </text>
        ))}
      </svg>
    </div>
  );
}
