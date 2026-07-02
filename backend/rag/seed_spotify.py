import csv
import os
import random
from collections import defaultdict

import chromadb
from chromadb.utils import embedding_functions

CSV_PATH = os.path.join(os.path.dirname(__file__), "spotify_data.csv")
PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "music_knowledge"
TARGET_PER_GENRE = 20   # 장르당 최대 곡 수 
MIN_POPULARITY = 60    
KEEP_GENRES = {
    "pop", "dance", "hip-hop", "rock", "alt-rock", "indie-pop",
    "jazz", "electronic", "edm", "house", "soul", "funk",
    "blues", "country", "k-pop", "r-n-b", "disco", "groove",
    "chill", "ambient", "trip-hop", "dubstep", "techno",
    "trance", "deep-house", "electro", "club", "punk-rock",
    "hard-rock", "singer-songwriter", "folk", "new-age",
}

# key 번호  음이름
KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def key_to_scale(key: int, mode: int) -> str:
    name = KEY_NAMES[key % 12]
    return f"{name} {'major' if mode == 1 else 'minor'}"

def derive_mood(row: dict) -> str:
    tags = []
    v = float(row["valence"])
    e = float(row["energy"])
    d = float(row["danceability"])
    a = float(row["acousticness"])
    t = float(row["tempo"])

    if v > 0.7:
        tags += ["bright", "happy", "uplifting"]
    elif v < 0.3:
        tags += ["dark", "sad", "melancholic"]
    else:
        tags.append("neutral")

    if e > 0.8:
        tags += ["energetic", "intense"]
    elif e < 0.3:
        tags += ["calm", "relaxed"]


    if d > 0.75:
        tags.append("danceable")
    if a > 0.6:
        tags.append("acoustic")
    if t > 130:
        tags.append("fast")
    elif t < 80:
        tags.append("slow")

    return ", ".join(tags)


def row_to_text(row: dict) -> str:
    key = int(float(row["key"]))
    mode = int(float(row["mode"]))
    scale = key_to_scale(key, mode)
    tempo = round(float(row["tempo"]))
    mood = derive_mood(row)
    energy = round(float(row["energy"]), 2)
    valence = round(float(row["valence"]), 2)
    dance = round(float(row["danceability"]), 2)

    return (
        f"Genre: {row['genre']}, Tempo: {tempo} BPM, Key: {scale}, "
        f"Energy: {energy}, Valence: {valence}, Danceability: {dance}, "
        f"Mood: {mood}."
    )


def main():
    print("CSV 읽는 중")
    by_genre: dict[str, list[dict]] = defaultdict(list)

    with open(CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            genre = row["genre"].strip().lower()
            if genre not in KEEP_GENRES:
                continue
            try:
                pop = int(row["popularity"])
            except ValueError:
                continue
            if pop < MIN_POPULARITY:
                continue
            by_genre[genre].append(row)

    print(f"필터 후 장르 {len(by_genre)}개")

    # 장르별 균등 샘플링
    selected: list[dict] = []
    for genre, rows in sorted(by_genre.items()):
        sample = random.sample(rows, min(TARGET_PER_GENRE, len(rows)))
        selected.extend(sample)
        print(f"  {genre:25s}: {len(sample)}곡")

    random.shuffle(selected)
    print(f"\n총 {len(selected)}곡 선택됨")

    # ChromaDB 적재
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    ef = embedding_functions.DefaultEmbeddingFunction()
    col = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)

    client.delete_collection(name=COLLECTION_NAME)
    col = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)
    print(" music_kb 삭제")

    ids, docs, metas = [], [], []
    for i, row in enumerate(selected):
        ids.append(f"spotify_{i}_{row['track_id']}")
        docs.append(row_to_text(row))
        metas.append({
            "track_name": row["track_name"],
            "artist_name": row["artist_name"],
            "genre": row["genre"],
            "scale_type": "major" if int(float(row["mode"])) == 1 else "minor",
            "tempo": str(round(float(row["tempo"]))),
        })

    batch = 100
    for start in range(0, len(ids), batch):
        col.add(
            ids=ids[start:start+batch],
            documents=docs[start:start+batch],
            metadatas=metas[start:start+batch],
        )
        print(f"  적재 {min(start+batch, len(ids))}/{len(ids)}...")

    print(f"\nChromaDB 총 문서 수: {col.count()}")
    print("완료!")

 # 테스트
    print("\n[테스트 쿼리] G major bright energetic:")
    results = col.query(query_texts=["G major bright energetic"], n_results=3)
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        print(f"  → {meta['artist_name']} - {meta['track_name']} | {doc[:120]}")

if __name__ == "__main__":
    main()
