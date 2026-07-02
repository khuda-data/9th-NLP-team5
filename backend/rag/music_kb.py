import os
import chromadb
from chromadb.utils import embedding_functions
from logger import get_logger

logger = get_logger(__name__)
_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

_client = chromadb.PersistentClient(path=_PERSIST_DIR)
_ef = embedding_functions.DefaultEmbeddingFunction()
_collection = _client.get_or_create_collection(
    name="music_knowledge",
    embedding_function=_ef,
)

# 초기 음악 지식 데이터 (최초 1회 로드)
_SEED_DOCS = [
    {
        "id": "minor_mood",
        "text": "Minor scales convey sadness, tension, mystery. Natural Minor (Aeolian) works well for dark, melancholic pieces. Common progressions: i-VI-III-VII (Am-F-C-G), i-iv-V (Am-Dm-E).",
        "metadata": {"scale_type": "minor", "mood": "dark,sad,tense"},
    },
    {
        "id": "major_mood",
        "text": "Major scales convey happiness, brightness, resolution. Common progressions: I-IV-V-I (C-F-G-C), I-V-vi-IV (C-G-Am-F). Works for uplifting, joyful music.",
        "metadata": {"scale_type": "major", "mood": "happy,bright,uplifting"},
    },
    {
        "id": "bass_patterns",
        "text": "Bass patterns: root note on beat 1, fifth on beat 3 for steady groove. Walking bass moves stepwise through chord tones. Syncopated bass lands on off-beats for rhythmic tension.",
        "metadata": {"instrument": "bass"},
    },
    {
        "id": "kick_patterns",
        "text": "Kick drum patterns: four-on-the-floor (beats 1,2,3,4) for dance music. Two and four (snare-like) for rock. Off-beat for syncopation. Combine with hi-hats for groove.",
        "metadata": {"instrument": "kick"},
    },
    {
        "id": "chord_voice_leading",
        "text": "Voice leading: move chord tones by smallest interval. Common-tone sustained across chords creates smoothness. Contrary motion between bass and melody adds interest.",
        "metadata": {"topic": "voice_leading"},
    },
    {
        "id": "dorian_mode",
        "text": "Dorian mode: minor scale with raised 6th. Used in jazz, funk, and modal music. Creates a sophisticated minor sound. Progressions: i-IV (Dm-G in D Dorian).",
        "metadata": {"scale_type": "dorian", "mood": "sophisticated,jazzy"},
    },
    {
        "id": "strings_orchestration",
        "text": "Strings provide harmonic pad and melodic lines. Sustained whole notes for pads, eighth notes for movement. Layer violins (high), violas (mid), cellos (low) for richness.",
        "metadata": {"instrument": "strings"},
    },
    {
        "id": "brass_patterns",
        "text": "Brass: punchy staccato rhythms for energy, legato lines for grandeur. Typical brass hits on beat 2 and 4 (backbeat). Fanfare patterns ascend stepwise. Avoid rapid passages.",
        "metadata": {"instrument": "brass"},
    },
   # --- 1. 시티팝 / 신스웨이브 / retro (4개) ---
    {
        "id": "synthwave_80s",
        "text": "Synthwave and 80s Retro Electro rely on driving, continuous 8th-note basslines (bassline pumping with sidechain effect). Common progression: i - bVII - bVI - bVII (Am - G - F - G). Tempo ranges between 100-120 BPM. High use of analog synthesizer pads.",
        "metadata": {"scale_type": "minor", "mood": "retro,futuristic,cyberpunk,synthwave"},
    },
    {
        "id": "shibuya_kei_pop",
        "text": "Shibuya-kei and sophisticated J-Pop use rapidly changing jazz modulations. Progression: ii7 - V7 - Imaj7 - VI7 (Dm7 - G7 - Cmaj7 - A7) followed by minor iv7 (Fm7). Bass features highly active walking patterns with frequent syncopation.",
        "metadata": {"scale_type": "major", "mood": "bright,cute,sophisticated,shibuya"},
    },
    {
        "id": "disco_funky_guitar",
        "text": "Nu-Disco utilizes 16th-note muted guitar scratching patterns on top of a steady four-on-the-floor kick. Progression: i7 - iv7 - bVII7 - IIImaj7 (Am7 - Dm7 - G7 - Cmaj7). Strings provide short, staccato stabs on the upper register during chorus.",
        "metadata": {"scale_type": "minor", "mood": "groovy,energetic,disco,retro"},
    },
    {
        "id": "dream_pop_shoegaze",
        "text": "Dream Pop and Shoegaze maximize lush, washed-out texture using suspended chords (Csus2, Fmaj7#11). Progressions revolve around static Root-Fourth loops: I - IV (C - F). Pluck and guitars must use heavy reverb and delay to blur individual note boundaries.",
        "metadata": {"scale_type": "major", "mood": "dreamy,ethereal,nostalgic,spacey"},
    },

    # --- 2. 힙합 / 알앤비 / Lo-Fi (4개) ---
    {
        "id": "trap_dark_hiphop",
        "text": "Dark Trap uses minor secondary harmonics and chromatic half-step movements. Progression: i - bII (Am - Bb) for extreme tension. The kick drum acts as an 808 sub-bass with long slides, while hi-hats execute rapid 32nd-note triplets.",
        "metadata": {"scale_type": "minor", "mood": "dark,aggressive,tense,trap,hiphop"},
    },
    {
        "id": "rnb_neo_soul_ballad",
        "text": "R&B and Contemporary Soul rely heavily on 9th, 11th, and 13th extensions. Progression: Imaj9 - vi9 - ii11 - V7alt (Cmaj9 - Am9 - Dm11 - G7b9). Pluck sounds should emulate soft rhodes electric pianos with a slow vibrato effect.",
        "metadata": {"scale_type": "major", "mood": "warm,romantic,smooth,rnb"},
    },
    {
        "id": "jazz_hop_chill",
        "text": "Jazz Hop integrates vinyl crackle textures with complex jazz turnarounds. Progression: iii7 - VI7 - ii7 - V7 (Em7 - A7 - Dm7 - G7). Tempo is strictly slow (75-80 BPM). Bass acts loosely, dragging slightly behind the beat for a 'laid-back' swing feel.",
        "metadata": {"scale_type": "major", "mood": "calm,relaxed,jazzy,lofi"},
    },
    {
        "id": "pbrnb_ambient",
        "text": "Alternative R&B (PBR&B) uses minimalist, filtered tracks. Progression: i7 - v7 (Am7 - Em7) looped endlessly. Drums omit the snare on beat 2, placing a filtered rimshot only on beat 4. Strings play very low, sustained drone notes for an ominous baseline.",
        "metadata": {"scale_type": "minor", "mood": "mysterious,sad,lonely,ambient"},
    },

    # --- 3. 재즈 / 보사노바 / 어쿠스틱 (4개) ---
    {
        "id": "bossanova_brazilian",
        "text": "Bossa Nova features a highly distinctive syncopated nylon guitar pattern combined with a jazz progression: Imaj7 - VI7alt - ii7 - V7 (Cmaj7 - A7b9 - Dm7 - G7). Bass plays strictly on beats 1 and 3 (root and fifth) mimicking a relaxed surdo drum.",
        "metadata": {"scale_type": "major", "mood": "calm,warm,breeze,bossanova"},
    },
    {
        "id": "gipsy_jazz_swing",
        "text": "Gypsy Jazz and Swing utilize driving acoustic rhythm guitars playing quarter-note chop chords (la pompe). Progression: i - iv - V7 (Am - Dm - E7). Pluck elements mimic fast chromatic gypsy guitar licks using staccato acoustic articulations.",
        "metadata": {"scale_type": "minor", "mood": "playful,bouncy,vintage,swing"},
    },
    {
        "id": "acoustic_folk_indie",
        "text": "Acoustic Folk relies on simple triadic open chords with rolling fingerpicking patterns. Progression: I - V - vi - IV (C - G - Am - F). Pluck mimics acoustic guitar plucking. Strings provide minimal, warm cello support in the low-mid frequency range.",
        "metadata": {"scale_type": "major", "mood": "innocent,peaceful,sad,folk"},
    },
    {
        "id": "modal_jazz_impressionism",
        "text": "Modal Jazz avoids traditional functional harmony, focusing on quartal harmony (chords stacked in fourths). Perfect for ambiguous, intellectual atmosphere. Dorian or Mixolydian modes work best. Bass explores free, non-repetitive melodic shapes.",
        "metadata": {"scale_type": "dorian", "mood": "sophisticated,mysterious,jazzy"},
    },

    # --- 4. 댄스 / 일렉트로닉 / 팝 (4개) ---
    {
        "id": "tropical_house_edm",
        "text": "Tropical House uses clean marimba or kalimba pluck patterns playing upbeat syncopated riffs. Progression: vi - IV - I - V (Am - F - C - G). Tempo is upbeat (110-115 BPM). Kick drum plays a solid four-on-the-floor with a bright acoustic snap.",
        "metadata": {"scale_type": "major", "mood": "happy,bright,refreshing,tropical"},
    },
    {
        "id": "future_bass_pop",
        "text": "Future Bass relies on huge, detonating synthesizer pads with fast volume lfo modulation (wobble chords). Progression: IVmaj7 - V - iii7 - vi (Fmaj7 - G - Em7 - Am). Snare lands hard on beat 3. Brass elements layer on accents to punch through.",
        "metadata": {"scale_type": "major", "mood": "energetic,emotional,futuristic,futurebass"},
    },
    {
        "id": "future_funk_anime",
        "text": "Future Funk samples vintage records, speeding them up to 125-130 BPM. Progression: ii7 - V7 - III7 - vi7 (Dm7 - G7 - E7 - Am7). Bass executes high-velocity slap patterns (continuous 16th notes), and brass sections fill every structural pause.",
        "metadata": {"scale_type": "major", "mood": "bouncy,cheerful,high-energy,funk"},
    },
    {
        "id": "cyberpunk_industrial",
        "text": "Industrial Electronic uses heavily distorted synth basslines playing jagged, aggressive driving ostinatos on 16th notes. Progression stays static on a single dark note (e.g., D minor drone). Kick drum is metallic and loud, hitting on every beat.",
        "metadata": {"scale_type": "minor", "mood": "dark,aggressive,industrial,cyberpunk"},
    },

    # --- 5. 시네마틱 / 에픽 / 메디테이션 (4개) ---
    {
        "id": "epic_orchestral_battle",
        "text": "Epic Cinematic Battle tracks use dark minor mode progressions: i - bVI - bVII - i (Am - F - G - Am). Kick drum acts as heavy orchestral Taiko stabs on beats 1 and 3. Strings play fast, driving 16th-note staccato ostinatos throughout the track.",
        "metadata": {"scale_type": "minor", "mood": "epic,grand,aggressive,cinematic"},
    },
    {
        "id": "ambient_meditation",
        "text": "Ambient Meditation tracks completely omit rhythmic elements like kick and bass riffs. Progression floats slowly between I and IV (Cmaj7 to Fmaj7) every 4 bars. Strings play ultra-long, soft pads with fading attack and decay times for a floating feel.",
        "metadata": {"scale_type": "major", "mood": "calm,peaceful,relaxed,ambient"},
    },
    {
        "id": "dark_fantasy_gothic",
        "text": "Gothic Dark Fantasy uses the Harmonic Minor scale paired with classical pipe organ structures. Progression: i - iv - V7 - i (Am - Dm - E7 - Am). Brass plays slow, menacing low-register minor triads. Pluck elements mimic a delicate, spooky harpsichord.",
        "metadata": {"scale_type": "minor", "mood": "mysterious,dark,gothic,fantasy"},
    },
    {
        "id": "hopeful_cinematic_climax",
        "text": "Hopeful Cinematic resolutions utilize ascending major progressions that resolve upward: bVI - bVII - I (F - G - C). Strings begin as soft pizzicato (plucked strings) in verse, transitioning into massive legato ensemble sweeps during the climax.",
        "metadata": {"scale_type": "major", "mood": "bright,emotional,grand,hopeful"},
    }
]


def _seed_if_empty() -> None:
    # Spotify 데이터로 교체 후 기본 시드 비활성화
    if _collection.count() == 0 and _SEED_DOCS:
        _collection.add(
            ids=[d["id"] for d in _SEED_DOCS],
            documents=[d["text"] for d in _SEED_DOCS],
            metadatas=[d["metadata"] for d in _SEED_DOCS],
        )


def query_music_knowledge(scale: str, mood_keywords: list[str], n_results: int = 4) -> str:
    _seed_if_empty()
    query = f"{scale} {' '.join(mood_keywords)}"
    results = _collection.query(query_texts=[query], n_results=n_results)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    logger.info(
        "RAG 검색 query='%s' | %d개 매칭",
        query, len(docs),
    )
    for doc, meta in zip(docs, metas):
        logger.info(
            "  → %s - %s | %s",
            meta.get("artist_name", "?"), meta.get("track_name", "?"), doc,
        )
    return "\n".join(f"- {doc}" for doc in docs)
