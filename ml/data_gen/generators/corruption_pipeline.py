"""corruption_pipeline.py — Clean Turkish text → simulated Whisper errors.

Generates ~3000 (corrupted, clean) pairs at 3 difficulty levels:
  easy   — 1-2 corruptions
  medium — 3-5 corruptions
  hard   — 6+ corruptions

Output format (JSONL):
  {"input": "<corrupted>", "output": "<clean>", "difficulty": "easy|medium|hard"}

Usage:
  # From synthetic sentences built-in:
  python corruption_pipeline.py --generate-synthetic --output data_gen/corruption_pairs.jsonl

  # From text files on disk:
  python corruption_pipeline.py --input-dir /path/to/texts --output data_gen/corruption_pairs.jsonl
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Whisper-known error patterns for Turkish
# ---------------------------------------------------------------------------

# 1. ASCII Turkish — Whisper often strips diacritics
_TURKISH_CHAR_MAP: list[tuple[str, str]] = [
    ("â", "a"),
    ("ü", "u"),
    ("ö", "o"),
    ("ı", "i"),
    ("ş", "s"),
    ("ç", "c"),
    ("ğ", "g"),
    ("İ", "I"),
    ("Ü", "U"),
    ("Ö", "O"),
    ("Ş", "S"),
    ("Ç", "C"),
    ("Ğ", "G"),
]

# 2. Common filler words Whisper inserts or that remain in raw speech
_FILLERS = ["yani", "şey", "hani", "işte", "ee", "aa", "falan", "filen", "öyle yani"]

# 3. Common mishearings / homophones
_HOMOPHONE_PAIRS: list[tuple[str, str]] = [
    ("değil", "deil"),
    ("gideceğim", "gideceyim"),
    ("yapacağız", "yapacayiz"),
    ("olacak", "olacak"),
    ("başlamak", "baslamak"),
    ("çalışıyor", "calisiyor"),
    ("söylüyor", "soyluyor"),
    ("görüşürüz", "gorusuruz"),
    ("öğrenci", "ogrenci"),
    ("düşünüyorum", "dusunuyorum"),
]

# 4. Punctuation removal — Whisper rarely adds punctuation
# 5. Capitalization — Whisper often outputs lower-case

# ---------------------------------------------------------------------------
# Synthetic base sentences (100 Turkish sentences across domains)
# ---------------------------------------------------------------------------

_SYNTHETIC_SENTENCES: list[str] = [
    # General
    "Bugün hava çok güzel, dışarı çıkmak istiyorum.",
    "Toplantı saat üçte başlıyor, hazır ol lütfen.",
    "Bu akşam sinemaya gidiyoruz, sen de gelir misin?",
    "Öğle arası için sandviç aldım, seninle paylaşabilirim.",
    "Yarın sabah erken kalkmam gerekiyor, alarmı kurdum.",
    "Çocuklar bahçede oynuyor, çok eğleniyorlar.",
    "Yeni bir kitap okumaya başladım, çok ilginç.",
    "Hafta sonu pikniğe gidiyoruz, hazırlık yapıyoruz.",
    "Bu konuyu anlamak için biraz daha zaman lazım.",
    "Şirkete yeni bir çalışan katıldı, çok deneyimli biri.",
    # Engineering
    "AppViewModel içinde tüm state yönetimini yapıyoruz.",
    "Bu fonksiyonu düzeltmemiz gerekiyor, çok önemli.",
    "API endpoint'i JSON response döndürüyor, parse etmemiz lazım.",
    "Git commit mesajını doğru yazmak önemlidir.",
    "Docker container'ı yeniden başlatmak gerekiyor.",
    "Pull request açmadan önce testleri çalıştır.",
    "Database şemasını güncelledik, migration yazmalıyız.",
    "Backend servisi port 8000'de çalışıyor.",
    "Swift'te protocol kullanarak dependency injection yapıyoruz.",
    "MLX modeli Apple Silicon üzerinde çok hızlı çalışıyor.",
    "Whisper modelini fine-tune etmek için veri topluyoruz.",
    "LoRA adapter'ı kullanarak modeli özelleştireceğiz.",
    "Tokenizer chat template'i doğru uygulamalıyız.",
    "Training sırasında validation loss'u takip etmeliyiz.",
    "Model ağırlıklarını safetensors formatında kaydediyoruz.",
    # Office
    "Bu raporu yarın sabaha kadar tamamlamalıyım.",
    "Müşteri toplantısına hazırlık yapıyorum.",
    "Bütçe planlaması için Excel tablosunu güncelledim.",
    "Ekip arkadaşlarına email göndermem gerekiyor.",
    "Proje teslim tarihi gelecek Cuma.",
    "Departman müdürüyle görüşmem var öğleden sonra.",
    "Yıllık değerlendirme formu dolduruldu.",
    "Konferans odasını saat ikiye kadar ayırdım.",
    "Bu projeyi zamanında teslim etmemiz çok kritik.",
    "İnsan kaynakları departmanıyla koordineli çalışıyoruz.",
    # Medical
    "Doktor randevusu aldım, yarın saat dörtte.",
    "İlaçları düzenli almayı unutmamalıyım.",
    "Kan tahlili sonuçları normal çıktı.",
    "Hastane ziyaretleri belirli saatlerde yapılabilir.",
    "Sağlıklı beslenmek için düzenli alışveriş yapıyorum.",
    # Education
    "Üniversitede bilgisayar mühendisliği okuyorum.",
    "Ödev teslim tarihi bu akşam saat onda.",
    "Sınav hazırlığı için çalışma grubu kuruyoruz.",
    "Laboratuvar raporu yazmam gerekiyor.",
    "Hocamız konuyu çok güzel anlattı.",
    # Mixed context
    "Kahve içerken haberleri okudum.",
    "Trafikte çok zaman kaybettim.",
    "Market alışverişinde unuttuğum şeyler vardı.",
    "Spor salonuna düzenli gitmeye çalışıyorum.",
    "Arkadaşımla uzun süre konuştuk.",
    # More engineering
    "Async fonksiyonları await ile çağırmalıyız.",
    "Type hint eklemek kodun okunabilirliğini artırır.",
    "Unit testleri yazmak refactoring'i güvenli yapar.",
    "CI/CD pipeline otomatik olarak deploy ediyor.",
    "Environment variable'ları .env dosyasında tutuyoruz.",
    "Memory leak'i profiler ile tespit ettik.",
    "Race condition sorunu mutex ile çözdük.",
    "API rate limiting eklemek güvenlik açısından önemli.",
    "Log mesajlarını structured format'ta yazıyoruz.",
    "Cache invalidation stratejisini gözden geçirelim.",
    # Conversational
    "Sence bu karar doğru mu?",
    "Bence daha iyi bir çözüm bulabiliriz.",
    "Nasıl gidiyor, her şey yolunda mı?",
    "Bu konuda ne düşünüyorsun?",
    "Yardıma ihtiyacın olursa söyle.",
    "Teşekkür ederim, çok işe yaradı.",
    "Özür dilerim, geç kaldım.",
    "Bir saniye, şu işi bitireyim.",
    "Anlamadım, tekrar anlatır mısın?",
    "Harika bir fikir, hemen başlayalım.",
    # Technical Turkish
    "Kullanıcı arayüzü sezgisel olmalı.",
    "Veri tabanı sorgularını optimize etmeliyiz.",
    "Güvenlik açıkları düzenli olarak kontrol edilmeli.",
    "Yedekleme sistemi her gece çalışıyor.",
    "Sistem yükü yoğun saatlerde artıyor.",
    "Ağ bağlantısı zaman zaman kesiliyor.",
    "Sunucu kapasitesini artırmayı planlıyoruz.",
    "Kullanıcı geri bildirimleri değerlendirildi.",
    "Yazılım güncellemesi zorunlu hale geldi.",
    "Mobil uygulama yeni özellikler kazandı.",
    # Business
    "Satış rakamları beklentilerin üzerinde geldi.",
    "Yeni pazar stratejisi hazırlanıyor.",
    "Tedarik zinciri sorunları çözüme kavuştu.",
    "Müşteri memnuniyeti anketi gönderildi.",
    "Ortaklık anlaşması imzalandı.",
    "Yatırımcı toplantısı başarılı geçti.",
    "Ar-Ge bütçesi artırıldı.",
    "İhracat hedefleri tutturuldu.",
    "Marka bilinirliği çalışmaları sürüyor.",
    "Dijital dönüşüm projesi tamamlandı.",
    # More conversational
    "Bu fikri beğendim, devam edelim.",
    "Endişelenme, her şey yoluna girecek.",
    "Bu kadar zor olmak zorunda değil.",
    "Birlikte daha iyi çözümler bulabiliriz.",
    "Sabırsızlıkla bekliyorum.",
    "Umduğumdan daha iyi çıktı.",
    "Bir dahaki seferinde daha dikkatli olurum.",
    "Geçen hafta çok yoğundu.",
    "Dinlenmek için biraz zaman ayırmalıyım.",
    "Her şeyin bir sonu var, sabır lazım.",
]


# ---------------------------------------------------------------------------
# Corruption functions
# ---------------------------------------------------------------------------

def _remove_turkish_chars(text: str, count: int) -> str:
    """Replace Turkish-specific characters with ASCII equivalents."""
    chars_in_text = [(orig, repl) for orig, repl in _TURKISH_CHAR_MAP if orig in text]
    random.shuffle(chars_in_text)
    for orig, repl in chars_in_text[:count]:
        text = text.replace(orig, repl)
    return text


def _remove_punctuation(text: str) -> str:
    """Remove sentence-ending punctuation — Whisper rarely adds it."""
    return re.sub(r"[.,!?;:]", "", text)


def _lowercase_start(text: str) -> str:
    """Convert first letter to lowercase — common Whisper pattern."""
    if text and text[0].isupper():
        return text[0].lower() + text[1:]
    return text


def _insert_filler(text: str) -> str:
    """Insert a filler word at a random position."""
    filler = random.choice(_FILLERS)
    words = text.split()
    if len(words) < 2:
        return filler + " " + text
    pos = random.randint(1, len(words) - 1)
    words.insert(pos, filler)
    return " ".join(words)


def _apply_homophone(text: str) -> str:
    """Replace a word with a common mishearing."""
    for correct, misheard in random.sample(_HOMOPHONE_PAIRS, len(_HOMOPHONE_PAIRS)):
        if correct in text:
            return text.replace(correct, misheard, 1)
    return text


def _split_word(text: str) -> str:
    """Split a long word into two parts — spacing error."""
    words = text.split()
    long_words = [(i, w) for i, w in enumerate(words) if len(w) > 5]
    if not long_words:
        return text
    idx, word = random.choice(long_words)
    split_at = random.randint(2, len(word) - 2)
    words[idx] = word[:split_at] + " " + word[split_at:]
    return " ".join(words)


def _drop_word(text: str) -> str:
    """Drop a random short word — Whisper sometimes misses words."""
    words = text.split()
    if len(words) < 4:
        return text
    drop_candidates = [i for i, w in enumerate(words) if len(w) <= 4]
    if not drop_candidates:
        return text
    idx = random.choice(drop_candidates)
    words.pop(idx)
    return " ".join(words)


_ALL_CORRUPTIONS = [
    _remove_punctuation,
    _lowercase_start,
    _insert_filler,
    _apply_homophone,
    _split_word,
    _drop_word,
]


def _corrupt(text: str, difficulty: str) -> str:
    """Apply corruptions according to difficulty level."""
    corrupted = text

    if difficulty == "easy":
        # 1-2 corruptions: always remove Turkish chars (1) + one random
        corrupted = _remove_turkish_chars(corrupted, 1)
        extra = random.choice([
            _remove_punctuation,
            _lowercase_start,
        ])
        corrupted = extra(corrupted)

    elif difficulty == "medium":
        # 3-5 corruptions
        corrupted = _remove_turkish_chars(corrupted, 2)
        corrupted = _remove_punctuation(corrupted)
        corrupted = _lowercase_start(corrupted)
        extra_funcs = random.sample([_insert_filler, _apply_homophone, _split_word], 2)
        for fn in extra_funcs:
            corrupted = fn(corrupted)

    else:  # hard
        # 6+ corruptions
        corrupted = _remove_turkish_chars(corrupted, len(_TURKISH_CHAR_MAP))
        corrupted = _remove_punctuation(corrupted)
        corrupted = _lowercase_start(corrupted)
        for fn in [_insert_filler, _apply_homophone, _split_word, _drop_word]:
            corrupted = fn(corrupted)
        # Second pass
        corrupted = _insert_filler(corrupted)

    return corrupted


# ---------------------------------------------------------------------------
# Pair generation
# ---------------------------------------------------------------------------

def _generate_pairs(
    sentences: list[str],
    target: int,
    difficulty_distribution: dict[str, float],
) -> list[dict]:
    """Generate (input, output, difficulty) pairs from a sentence list."""
    pairs: list[dict] = []

    diff_labels = list(difficulty_distribution.keys())
    diff_weights = list(difficulty_distribution.values())

    # Cycle through sentences as many times as needed
    sentence_pool = sentences * (target // len(sentences) + 1)
    random.shuffle(sentence_pool)

    for sentence in sentence_pool[:target]:
        difficulty = random.choices(diff_labels, weights=diff_weights, k=1)[0]
        corrupted = _corrupt(sentence.strip(), difficulty)
        if corrupted != sentence.strip():
            pairs.append({
                "input": corrupted,
                "output": sentence.strip(),
                "difficulty": difficulty,
            })

    return pairs


def _load_sentences_from_dir(input_dir: Path) -> list[str]:
    """Load sentences from .txt files in a directory (one sentence per line)."""
    sentences: list[str] = []
    for txt_file in sorted(input_dir.glob("**/*.txt")):
        with open(txt_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and len(line) > 10:
                    sentences.append(line)
    return sentences


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate corrupted/clean Turkish text pairs for fine-tuning.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--generate-synthetic",
        action="store_true",
        help="Use built-in 100 synthetic Turkish sentences.",
    )
    source.add_argument(
        "--input-dir",
        type=Path,
        metavar="DIR",
        help="Directory with .txt files (one sentence per line).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_gen/corruption_pairs.jsonl"),
        help="Output JSONL file path.",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=3000,
        help="Target number of pairs to generate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--easy-ratio",
        type=float,
        default=0.4,
        help="Fraction of pairs with easy difficulty.",
    )
    parser.add_argument(
        "--medium-ratio",
        type=float,
        default=0.35,
        help="Fraction of pairs with medium difficulty.",
    )
    args = parser.parse_args()

    random.seed(args.seed)

    # Validate ratios
    hard_ratio = 1.0 - args.easy_ratio - args.medium_ratio
    if hard_ratio < 0:
        parser.error("--easy-ratio + --medium-ratio must be <= 1.0")

    distribution = {
        "easy": args.easy_ratio,
        "medium": args.medium_ratio,
        "hard": hard_ratio,
    }

    # Load sentences
    if args.generate_synthetic:
        sentences = _SYNTHETIC_SENTENCES
        print(f"Using {len(sentences)} synthetic sentences.", file=sys.stderr)
    else:
        sentences = _load_sentences_from_dir(args.input_dir)
        if not sentences:
            print(f"ERROR: No sentences found in {args.input_dir}", file=sys.stderr)
            sys.exit(1)
        print(f"Loaded {len(sentences)} sentences from {args.input_dir}.", file=sys.stderr)

    # Generate
    print(f"Generating {args.target} pairs...", file=sys.stderr)
    pairs = _generate_pairs(sentences, args.target, distribution)

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    counts = {}
    for p in pairs:
        counts[p["difficulty"]] = counts.get(p["difficulty"], 0) + 1

    print(f"Written {len(pairs)} pairs to {args.output}", file=sys.stderr)
    for diff, n in sorted(counts.items()):
        print(f"  {diff}: {n}", file=sys.stderr)


if __name__ == "__main__":
    main()
