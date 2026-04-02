"""
ISSAI Turkish Speech Corpus → Whisper Error Pairs
--------------------------------------------------
1. HuggingFace'ten ISSAI_TSC_218.tar.gz indir
2. Ses dosyalarını faster-whisper ile işle
3. Whisper çıktısı vs. ground truth → pair oluştur
4. issai_pairs.jsonl olarak kaydet (train_runpod.py formatı)

Çalıştır (tekli):
  python process_issai.py

Paralel (3 shard):
  SHARD_INDEX=0 SHARD_TOTAL=3 python process_issai.py &
  SHARD_INDEX=1 SHARD_TOTAL=3 python process_issai.py &
  SHARD_INDEX=2 SHARD_TOTAL=3 python process_issai.py &

  # Bitince merge:
  cat /workspace/issai_pairs_*.jsonl > /workspace/issai_pairs_all.jsonl

Çıktı:
  /workspace/issai_pairs.jsonl        — tekli mod
  /workspace/issai_pairs_0.jsonl etc  — shard modu
"""

import os
import json
import tarfile
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Shard config (env var ile override edilebilir)
# ---------------------------------------------------------------------------
SHARD_INDEX = int(os.environ.get("SHARD_INDEX", "0"))
SHARD_TOTAL = int(os.environ.get("SHARD_TOTAL", "1"))

if SHARD_TOTAL > 1:
    OUTPUT_FILE = f"/workspace/issai_pairs_{SHARD_INDEX}.jsonl"
else:
    OUTPUT_FILE  = "/workspace/issai_pairs.jsonl"

DOWNLOAD_DIR = "/root/issai_raw"       # container disk (120GB) — workspace 20GB quota aşılır!
EXTRACT_DIR  = "/root/issai_extracted" # container disk (120GB)
WHISPER_MODEL = "large-v3"   # RTX 4090 kaldırır
BATCH_SIZE   = 16            # GPU paralel işlem
HF_TOKEN     = os.environ.get("HF_TOKEN", "")

print(f"Shard: {SHARD_INDEX}/{SHARD_TOTAL} → {OUTPUT_FILE}")

# ---------------------------------------------------------------------------
# 1. İndir
# ---------------------------------------------------------------------------
def download_dataset():
    tar_path = f"{DOWNLOAD_DIR}/ISSAI_TSC_218.tar.gz"
    if Path(tar_path).exists():
        print(f"Already downloaded: {tar_path}")
        return tar_path

    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    print("Downloading ISSAI_TSC_218.tar.gz (~21GB)...")

    import urllib.request
    url = "https://huggingface.co/datasets/issai/Turkish_Speech_Corpus/resolve/main/ISSAI_TSC_218.tar.gz"
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        with open(tar_path, "wb") as f:
            while True:
                chunk = response.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {downloaded/1e9:.1f}GB / {total/1e9:.1f}GB ({pct:.1f}%)", end="", flush=True)
    print(f"\nDownloaded: {tar_path}")
    return tar_path

# ---------------------------------------------------------------------------
# 2. Extract
# ---------------------------------------------------------------------------
def extract_dataset(tar_path):
    if Path(EXTRACT_DIR).exists() and any(Path(EXTRACT_DIR).iterdir()):
        print(f"Already extracted: {EXTRACT_DIR}")
        return

    Path(EXTRACT_DIR).mkdir(parents=True, exist_ok=True)
    print(f"Extracting {tar_path}...")
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(EXTRACT_DIR)
    print(f"Extracted to {EXTRACT_DIR}")

# ---------------------------------------------------------------------------
# 3. Ses + transkript dosyalarını bul
# ---------------------------------------------------------------------------
def find_pairs():
    """
    ISSAI formatı: ses dosyası + yanında .txt veya metadata dosyası.
    Yapıyı keşfederek eşleştir.
    """
    extract_path = Path(EXTRACT_DIR)

    # Tüm ses dosyalarını bul
    audio_files = []
    for ext in ["*.wav", "*.flac", "*.mp3"]:
        audio_files.extend(extract_path.rglob(ext))

    # Deterministik sıralama (shardlar aynı listeyi böler)
    audio_files = sorted(audio_files)
    print(f"Found {len(audio_files)} audio files total")

    # Shard slice
    if SHARD_TOTAL > 1:
        shard_files = audio_files[SHARD_INDEX::SHARD_TOTAL]
        print(f"  Shard {SHARD_INDEX}/{SHARD_TOTAL}: {len(shard_files)} dosya")
        audio_files = shard_files

    pairs = []
    missing = 0

    for audio_path in audio_files:
        # Transkripti bul: aynı isimde .txt, veya üst dizinde transcript.txt/metadata
        transcript = None

        # 1. Aynı stem ile .txt
        txt_path = audio_path.with_suffix(".txt")
        if txt_path.exists():
            transcript = txt_path.read_text(encoding="utf-8").strip()

        # 2. Üst dizinde transcripts.txt (tsv/csv formatı)
        if transcript is None:
            for meta_name in ["transcripts.txt", "metadata.csv", "transcripts.tsv"]:
                meta_path = audio_path.parent / meta_name
                if meta_path.exists():
                    # stem → transkript eşleştir
                    for line in meta_path.read_text(encoding="utf-8").splitlines():
                        parts = re.split(r"[\t,|]", line, maxsplit=1)
                        if len(parts) == 2 and audio_path.stem in parts[0]:
                            transcript = parts[1].strip()
                            break

        if transcript:
            pairs.append((str(audio_path), transcript))
        else:
            missing += 1

    print(f"Paired: {len(pairs)}, missing transcript: {missing}")
    return pairs

# ---------------------------------------------------------------------------
# 4. Ses + transkript dosyalarını bul
# ---------------------------------------------------------------------------
SAVE_EVERY  = 1000   # her N dosyada bir diske yaz

# ---------------------------------------------------------------------------
# 5. Pair oluştur + kaydet (incremental)
# ---------------------------------------------------------------------------
_FILLERS = {'ee', 'aa', 'hmm', 'hm', 'ıı', 'mm', 'ah', 'eh', 'uh', 'um'}

def _clean_ground_truth(text: str) -> str:
    """Ground truth'u normalize et: filler temizle, büyük harf, nokta ekle."""
    words = text.strip().split()
    cleaned = [w for w in words if w.lower().rstrip('.,!?') not in _FILLERS]
    if not cleaned:
        return text.strip()
    result = ' '.join(cleaned)
    result = result[0].upper() + result[1:] if result else result
    if result and result[-1] not in '.!?…':
        result += '.'
    return result

def build_and_append_pairs(results, f):
    """results listesini {"input", "output", "category"} formatına çevir, dosyaya append et."""
    count = 0
    for r in results:
        whisper = r["whisper"]
        truth   = _clean_ground_truth(r["ground_truth"])
        if whisper.lower().strip() == truth.lower().strip():
            continue  # fark yok, atla
        f.write(json.dumps({"input": whisper, "output": truth, "category": "issai"}, ensure_ascii=False) + "\n")
        count += 1
    f.flush()
    return count

def load_done_set():
    """Daha önce işlenmiş audio isimlerini OUTPUT_FILE'dan yükle (resume desteği)."""
    done = set()
    if not Path(OUTPUT_FILE).exists():
        return done
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    obj = json.loads(line)
                    if "audio" in obj:
                        done.add(obj["audio"])
                except Exception:
                    pass
    return done

def process_with_whisper(pairs):
    from faster_whisper import WhisperModel, BatchedInferencePipeline

    # Resume: daha önce işlenenleri atla
    done = load_done_set()
    if done:
        print(f"  Resume: {len(done)} dosya zaten işlenmiş, atlanıyor.")
    remaining = [(p, gt) for p, gt in pairs if Path(p).name not in done]
    print(f"\nLoading faster-whisper {WHISPER_MODEL}...")
    model = WhisperModel(WHISPER_MODEL, device="cuda", compute_type="float16")
    batched_model = BatchedInferencePipeline(model)

    skipped = 0
    total_saved = len(done)
    buffer = []

    print(f"Processing {len(remaining)}/{len(pairs)} audio files...")
    mode = "a" if done else "w"
    with open(OUTPUT_FILE, mode, encoding="utf-8") as out_f:
        for i, (audio_path, ground_truth) in enumerate(remaining):
            if i % 500 == 0:
                pct = (len(done) + i) / len(pairs) * 100
                print(f"  {len(done)+i}/{len(pairs)} ({pct:.1f}%)", flush=True)

            try:
                segments, _ = batched_model.transcribe(
                    audio_path,
                    language="tr",
                    batch_size=BATCH_SIZE,
                    vad_filter=True,
                )
                whisper_text = " ".join(seg.text.strip() for seg in segments).strip()
                if not whisper_text:
                    skipped += 1
                    continue
                buffer.append({
                    "whisper": whisper_text,
                    "ground_truth": ground_truth,
                    "audio": Path(audio_path).name,
                })
            except Exception as e:
                skipped += 1
                if skipped <= 5:
                    print(f"  Error on {Path(audio_path).name}: {e}")

            # Her SAVE_EVERY dosyada bir diske yaz
            if len(buffer) >= SAVE_EVERY:
                saved = build_and_append_pairs(buffer, out_f)
                total_saved += saved
                print(f"  [{total_saved} pair kaydedildi]", flush=True)
                buffer = []

        # Kalan buffer'ı yaz
        if buffer:
            saved = build_and_append_pairs(buffer, out_f)
            total_saved += saved

    print(f"\nToplam kaydedilen: {total_saved} pair, skipped: {skipped}")
    print(f"Output: {OUTPUT_FILE}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tar_path = download_dataset()
    extract_dataset(tar_path)
    audio_pairs = find_pairs()
    process_with_whisper(audio_pairs)
    print("\nDone! Next step: SCP issai_pairs.jsonl to Mac, add to prepare_dataset.py")
