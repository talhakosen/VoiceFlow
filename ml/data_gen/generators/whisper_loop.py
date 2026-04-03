"""whisper_loop.py — macOS `say` TTS → Whisper → real error pairs.

Synthesizes Turkish speech with the Yelda voice, transcribes with mlx-whisper,
and saves (whisper_output, reference_text) pairs — genuine transcription errors.

Requirements:
  - macOS (uses `say -v Yelda`)
  - mlx-whisper installed
  - soundfile installed

Output format (JSONL):
  {"input": "<whisper_transcription>", "output": "<reference>", "source": "whisper_loop"}

Usage:
  python whisper_loop.py --output data_gen/whisper_pairs.jsonl --target 500
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Reference sentences (50 Turkish sentences)
# ---------------------------------------------------------------------------

_REFERENCE_SENTENCES: list[str] = [
    "Bugün hava çok güzel, dışarı çıkmak istiyorum.",
    "Toplantı saat üçte başlıyor, hazır ol lütfen.",
    "AppViewModel içinde tüm state yönetimini yapıyoruz.",
    "Bu fonksiyonu düzeltmemiz gerekiyor, çok önemli.",
    "API endpoint'i JSON response döndürüyor.",
    "Git commit mesajını doğru yazmak önemlidir.",
    "Docker container'ı yeniden başlatmak gerekiyor.",
    "Pull request açmadan önce testleri çalıştır.",
    "Database şemasını güncelledik, migration yazmalıyız.",
    "Backend servisi port 8000'de çalışıyor.",
    "Swift'te protocol kullanarak dependency injection yapıyoruz.",
    "MLX modeli Apple Silicon üzerinde çok hızlı çalışıyor.",
    "Whisper modelini fine-tune etmek için veri topluyoruz.",
    "Bu raporu yarın sabaha kadar tamamlamalıyım.",
    "Müşteri toplantısına hazırlık yapıyorum.",
    "Bütçe planlaması için Excel tablosunu güncelledim.",
    "Proje teslim tarihi gelecek Cuma.",
    "Bu akşam sinemaya gidiyoruz, sen de gelir misin?",
    "Yeni bir kitap okumaya başladım, çok ilginç.",
    "Hafta sonu pikniğe gidiyoruz, hazırlık yapıyoruz.",
    "Async fonksiyonları await ile çağırmalıyız.",
    "Type hint eklemek kodun okunabilirliğini artırır.",
    "Unit testleri yazmak refactoring'i güvenli yapar.",
    "CI/CD pipeline otomatik olarak deploy ediyor.",
    "Environment variable'ları .env dosyasında tutuyoruz.",
    "Memory leak'i profiler ile tespit ettik.",
    "Race condition sorunu mutex ile çözdük.",
    "Log mesajlarını structured format'ta yazıyoruz.",
    "Kullanıcı arayüzü sezgisel olmalı.",
    "Veri tabanı sorgularını optimize etmeliyiz.",
    "Güvenlik açıkları düzenli olarak kontrol edilmeli.",
    "Yedekleme sistemi her gece çalışıyor.",
    "Sistem yükü yoğun saatlerde artıyor.",
    "Sunucu kapasitesini artırmayı planlıyoruz.",
    "Satış rakamları beklentilerin üzerinde geldi.",
    "Yeni pazar stratejisi hazırlanıyor.",
    "Müşteri memnuniyeti anketi gönderildi.",
    "Ortaklık anlaşması imzalandı.",
    "Ar-Ge bütçesi artırıldı.",
    "Dijital dönüşüm projesi tamamlandı.",
    "Sence bu karar doğru mu?",
    "Bence daha iyi bir çözüm bulabiliriz.",
    "Yardıma ihtiyacın olursa söyle.",
    "Teşekkür ederim, çok işe yaradı.",
    "Anlamadım, tekrar anlatır mısın?",
    "Harika bir fikir, hemen başlayalım.",
    "Endişelenme, her şey yoluna girecek.",
    "Bir dahaki seferinde daha dikkatli olurum.",
    "Geçen hafta çok yoğundu.",
    "Her şeyin bir sonu var, sabır lazım.",
]


# ---------------------------------------------------------------------------
# TTS + Whisper
# ---------------------------------------------------------------------------

def _say_to_wav(text: str, wav_path: str, voice: str = "Yelda") -> bool:
    """Use macOS `say` to synthesize text and save as WAV."""
    try:
        # Use AIFF first, then convert to WAV via afconvert
        aiff_path = wav_path.replace(".wav", ".aiff")
        result = subprocess.run(
            ["say", "-v", voice, "-o", aiff_path, text],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            return False
        # Convert AIFF to WAV (16kHz mono — Whisper's preferred format)
        result = subprocess.run(
            [
                "afconvert",
                "-f", "WAVE",
                "-d", "LEI16@16000",
                "-c", "1",
                aiff_path,
                wav_path,
            ],
            capture_output=True,
            timeout=30,
        )
        # Clean up AIFF
        try:
            os.remove(aiff_path)
        except OSError:
            pass
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _transcribe_wav(wav_path: str, model_name: str) -> str | None:
    """Transcribe WAV file with mlx-whisper and return the text."""
    try:
        import mlx_whisper
    except ImportError:
        print("ERROR: mlx_whisper not installed.", file=sys.stderr)
        return None

    try:
        result = mlx_whisper.transcribe(
            wav_path,
            path_or_hf_repo=model_name,
            language="tr",
            task="transcribe",
        )
        text = result.get("text", "").strip()
        return text if text else None
    except Exception as e:
        print(f"  Transcription error: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    if platform.system() != "Darwin":
        print(
            "WARNING: whisper_loop.py requires macOS (`say -v Yelda`). "
            "Skipping on non-macOS platform.",
            file=sys.stderr,
        )
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="Generate real Whisper error pairs via macOS TTS.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_gen/whisper_pairs.jsonl"),
        help="Output JSONL file path.",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=500,
        help="Target number of pairs (only pairs where Whisper differs are saved).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="mlx-community/whisper-small-mlx",
        help="mlx-whisper model to use.",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default="Yelda",
        help="macOS TTS voice name (Turkish: Yelda).",
    )
    parser.add_argument(
        "--all-pairs",
        action="store_true",
        help="Save all pairs, including perfect transcriptions (no diff).",
    )
    args = parser.parse_args()

    sentences = _REFERENCE_SENTENCES
    args.output.parent.mkdir(parents=True, exist_ok=True)

    pairs: list[dict] = []
    attempts = 0
    # Cycle through sentences multiple times to reach target
    sentence_pool = (sentences * (args.target // len(sentences) + 2))[: args.target * 3]

    print(f"Generating pairs with voice '{args.voice}' and model '{args.model}'...", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp_dir:
        for sentence in sentence_pool:
            if len(pairs) >= args.target:
                break

            attempts += 1
            wav_path = os.path.join(tmp_dir, "tts_output.wav")

            # Synthesize
            if not _say_to_wav(sentence, wav_path, voice=args.voice):
                print(f"  TTS failed for: {sentence[:40]}...", file=sys.stderr)
                continue

            # Transcribe
            transcription = _transcribe_wav(wav_path, args.model)
            if transcription is None:
                continue

            # Filter: only save if there's a difference (unless --all-pairs)
            if args.all_pairs or transcription.lower().strip() != sentence.lower().strip():
                pairs.append({
                    "input": transcription,
                    "output": sentence,
                    "source": "whisper_loop",
                })
                print(
                    f"  [{len(pairs)}/{args.target}] OK: {transcription[:50]}",
                    file=sys.stderr,
                    end="\r",
                )

    print(f"\nProcessed {attempts} sentences, collected {len(pairs)} pairs.", file=sys.stderr)

    with open(args.output, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"Written {len(pairs)} pairs to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
