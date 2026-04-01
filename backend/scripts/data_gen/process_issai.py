"""
ISSAI Turkish Speech Corpus → Whisper Error Pairs
--------------------------------------------------
1. HuggingFace'ten ISSAI_TSC_218.tar.gz indir
2. Ses dosyalarını faster-whisper ile işle
3. Whisper çıktısı vs. ground truth → pair oluştur
4. issai_pairs.jsonl olarak kaydet (train_runpod.py formatı)

Çalıştır:
  python process_issai.py

Çıktı:
  /workspace/issai_pairs.jsonl  — fine-tuning için hazır
"""

import os
import json
import tarfile
import re
from pathlib import Path

OUTPUT_FILE  = "/workspace/issai_pairs.jsonl"
DOWNLOAD_DIR = "/workspace/issai_raw"
EXTRACT_DIR  = "/workspace/issai_extracted"
WHISPER_MODEL = "large-v3"   # RTX 4090 kaldırır
BATCH_SIZE   = 16            # GPU paralel işlem
HF_TOKEN     = os.environ.get("HF_TOKEN", "")

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

    print(f"Found {len(audio_files)} audio files")

    # Yapıyı anlamak için ilk 3'ü göster
    for af in audio_files[:3]:
        print(f"  Sample: {af}")
        siblings = list(af.parent.iterdir())
        print(f"  Siblings: {[s.name for s in siblings[:5]]}")

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
# 4. Whisper ile işle
# ---------------------------------------------------------------------------
def process_with_whisper(pairs):
    from faster_whisper import WhisperModel

    print(f"\nLoading faster-whisper {WHISPER_MODEL}...")
    model = WhisperModel(WHISPER_MODEL, device="cuda", compute_type="float16")

    results = []
    skipped = 0

    print(f"Processing {len(pairs)} audio files...")
    for i, (audio_path, ground_truth) in enumerate(pairs):
        if i % 500 == 0:
            print(f"  {i}/{len(pairs)} ({i/len(pairs)*100:.1f}%)")

        try:
            segments, info = model.transcribe(
                audio_path,
                language="tr",
                beam_size=5,
                vad_filter=True,
            )
            whisper_text = " ".join(seg.text.strip() for seg in segments).strip()

            if not whisper_text:
                skipped += 1
                continue

            results.append({
                "whisper": whisper_text,
                "ground_truth": ground_truth,
                "audio": Path(audio_path).name,
            })
        except Exception as e:
            skipped += 1
            if skipped <= 5:
                print(f"  Error on {Path(audio_path).name}: {e}")

    print(f"Processed: {len(results)}, skipped: {skipped}")
    return results

# ---------------------------------------------------------------------------
# 5. Pair oluştur + kaydet
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = "Sen bir Türkçe transkripsiyon düzeltme asistanısın. Verilen metni düzelt, başka bir şey ekleme."

def build_pairs(results):
    pairs_corrected = []
    pairs_clean = []

    for r in results:
        whisper = r["whisper"]
        truth   = r["ground_truth"]

        # Eğitim formatı: whisper → ground truth
        text = (
            f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
            f"<|im_start|>user\n{whisper}<|im_end|>\n"
            f"<|im_start|>assistant\n{truth}<|im_end|>"
        )

        if whisper.lower().strip() != truth.lower().strip():
            pairs_corrected.append({"text": text, "source": "issai"})
        else:
            pairs_clean.append({"text": text, "source": "issai_clean"})

    print(f"\nCorrected pairs: {len(pairs_corrected)}")
    print(f"Clean pairs (no change needed): {len(pairs_clean)}")
    return pairs_corrected + pairs_clean

def save_pairs(pairs):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"\nSaved {len(pairs)} pairs → {OUTPUT_FILE}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tar_path = download_dataset()
    extract_dataset(tar_path)
    audio_pairs = find_pairs()
    whisper_results = process_with_whisper(audio_pairs)
    final_pairs = build_pairs(whisper_results)
    save_pairs(final_pairs)
    print("\nDone! Next step: SCP issai_pairs.jsonl to Mac, add to prepare_dataset.py")
