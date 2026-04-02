"""tts_generator.py — whisper_sentences.jsonl → WAV dosyaları.

Edge TTS veya OpenAI TTS ile Türkçe ses üretir.
OpenAI: alloy, nova, onyx, shimmer (4 ses × 1 cümle = 4 WAV)
Edge:   tr-TR-EmelNeural, tr-TR-AhmetNeural (2 ses × 1 cümle = 2 WAV)

Kullanım:
    python tts_generator.py --engine openai --limit 10   # OpenAI TTS, ilk 10
    python tts_generator.py --engine edge                # Edge TTS, tümü
    python tts_generator.py --offset 1000 --limit 500   # 1000. cümleden 500 cümle
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import httpx

# ── Config ────────────────────────────────────────────────────────────────────

INPUT   = Path(__file__).parent / "whisper_sentences.jsonl"
OUT_DIR = Path(__file__).parent / "wav_raw"

OPENAI_VOICES = ["alloy", "nova", "onyx", "shimmer"]
EDGE_VOICES   = ["tr-TR-EmelNeural", "tr-TR-AhmetNeural"]

SAMPLE_RATE = 16000


# ── OpenAI TTS ────────────────────────────────────────────────────────────────

def _synthesize_openai(text: str, voice: str, out_path: Path, api_key: str) -> bool:
    mp3_path = out_path.with_suffix(".mp3")
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "tts-1-hd", "input": text, "voice": voice, "response_format": "mp3"},
            timeout=30,
        )
        resp.raise_for_status()
        mp3_path.write_bytes(resp.content)

        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3_path),
             "-ar", str(SAMPLE_RATE), "-ac", "1", "-acodec", "pcm_s16le", str(out_path)],
            capture_output=True, timeout=30,
        )
        mp3_path.unlink(missing_ok=True)
        return result.returncode == 0
    except Exception as e:
        mp3_path.unlink(missing_ok=True)
        print(f"    OpenAI TTS hata: {e}", flush=True)
        return False


# ── Edge TTS ──────────────────────────────────────────────────────────────────

async def _synthesize_edge(text: str, voice: str, out_path: Path) -> bool:
    import edge_tts
    mp3_path = out_path.with_suffix(".mp3")
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(mp3_path))

        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3_path),
             "-ar", str(SAMPLE_RATE), "-ac", "1", "-acodec", "pcm_s16le", str(out_path)],
            capture_output=True, timeout=30,
        )
        mp3_path.unlink(missing_ok=True)
        return result.returncode == 0
    except Exception as e:
        mp3_path.unlink(missing_ok=True)
        print(f"    Edge TTS hata: {e}", flush=True)
        return False


# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_filename(text: str, max_len: int = 40) -> str:
    clean = re.sub(r'[^\w\s-]', '', text.lower())
    clean = re.sub(r'\s+', '_', clean.strip())
    return clean[:max_len]


def voice_tag(voice: str) -> str:
    return voice.split("-")[-1].lower() if "-" in voice else voice


# ── Ana Akış ──────────────────────────────────────────────────────────────────

async def run(sentences: list[dict], out_dir: Path, engine: str, api_key: str) -> tuple[int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    voices = OPENAI_VOICES if engine == "openai" else EDGE_VOICES

    ok = err = 0
    for i, item in enumerate(sentences):
        text = item["text"].strip()
        if not text:
            continue

        fname_base = f"{i:05d}_{safe_filename(text)}"

        for voice in voices:
            tag = voice_tag(voice)
            wav_path = out_dir / f"{fname_base}_{tag}.wav"

            if wav_path.exists():
                ok += 1
                continue

            if engine == "openai":
                success = _synthesize_openai(text, voice, wav_path, api_key)
            else:
                success = await _synthesize_edge(text, voice, wav_path)

            if success:
                ok += 1
            else:
                err += 1

        if (i + 1) % 10 == 0:
            print(f"  [{i+1:4}/{len(sentences)}] ✓{ok} ✗{err}", flush=True)

    return ok, err


def main() -> None:
    parser = argparse.ArgumentParser(description="whisper_sentences.jsonl → WAV")
    parser.add_argument("--engine",     choices=["openai", "edge"], default="openai")
    parser.add_argument("--input",      default=str(INPUT))
    parser.add_argument("--output_dir", default=str(OUT_DIR))
    parser.add_argument("--limit",      type=int, default=None)
    parser.add_argument("--offset",     type=int, default=0)
    args = parser.parse_args()

    api_key = ""
    if args.engine == "openai":
        # .env'den oku (root proje dizini)
        env_path = Path(__file__).parents[3] / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
        api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            print("HATA: OPENAI_API_KEY bulunamadı (.env veya env var)")
            sys.exit(1)

    with open(args.input) as f:
        sentences = [json.loads(l) for l in f if l.strip()]

    sentences = sentences[args.offset:]
    if args.limit:
        sentences = sentences[:args.limit]

    voices = OPENAI_VOICES if args.engine == "openai" else EDGE_VOICES
    out_dir = Path(args.output_dir)

    print(f"Engine       : {args.engine.upper()} TTS")
    if args.engine == "openai":
        print(f"Model        : tts-1-hd")
    print(f"Sesler       : {', '.join(voices)}")
    print(f"Cümle sayısı : {len(sentences)}")
    print(f"WAV sayısı   : {len(sentences) * len(voices)}")
    print(f"Çıktı        : {out_dir}")
    print()

    ok, err = asyncio.run(run(sentences, out_dir, args.engine, api_key))
    total = len(sentences) * len(voices)
    print(f"\n✅ Tamamlandı: {ok}/{total} WAV ({err} hata)")


if __name__ == "__main__":
    main()
