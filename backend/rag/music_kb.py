import os
import chromadb
from chromadb.utils import embedding_functions

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
]


def _seed_if_empty() -> None:
    if _collection.count() == 0:
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
    return "\n".join(f"- {doc}" for doc in docs)
