"""filler_generator.py — Türkçe ASR filler/disfluency temizleme pair'leri üretir.

Kategoriler:
  filler       — şey, yani, hani, işte, ee, aa → kaldır (anlamsız kullanım)
  semantic     — yani/işte anlam taşıyorsa KOR (zor vaka)
  backtrack    — "hayır dur şöyle diyeyim", "pardon" → geri al, son niyet al
  stutter      — "bu bu bu fonksiyon" → "bu fonksiyon"
  number       — "iki bin yirmi altı" → "2026", "yüzde seksen" → "%80"

Her kategori 3 zorluk seviyesinde (easy/medium/hard) üretilir.
Toplamda ~1700 pair hedef.

Usage:
  ANTHROPIC_API_KEY=sk-... python filler_generator.py \\
      --output ../data/filler_pairs.jsonl \\
      --target 1700
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: pip install anthropic", file=sys.stderr)
    sys.exit(1)

MODEL = "claude-opus-4-6"  # Anthropic — filler kalıplarında kalite kritik

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM = """\
Sen bir Türkçe ASR (otomatik konuşma tanıma) eğitim verisi üreticisisin.
Senden (input, output) çiftleri isteyeceğim.

input  → kullanıcının mikrofona söylediği ham metin (Whisper çıktısı gibi)
output → düzeltilmiş, temiz Türkçe metin

KURALLAR:
1. input gerçekçi olsun — insanlar böyle konuşur, çok yapay olmasın
2. output sadece gerekli düzeltmeleri yapsın — kelime ekleyip çıkarma yok
3. Semantik anlam değiştirilmesin
4. JSON array dışında hiçbir şey yazma
5. Her pair farklı bir cümle konusu içersin (tekrar yok)

Format:
[
  {"input": "...", "output": "...", "difficulty": "easy|medium|hard", "type": "<kategori>"},
  ...
]"""

# ---------------------------------------------------------------------------
# Kategori prompt'ları
# ---------------------------------------------------------------------------

_PROMPTS = {

"filler_easy": """\
{n} adet KOLAY filler temizleme pair'i üret.
Kural: Cümlenin başında veya sonunda tek bir filler kelime var.
Filler listesi: şey, yani, hani, işte, ee, aa, efendim (dolgu olarak), tamam yani

Örnekler:
  input: "Şey, toplantı yarın saat üçte."
  output: "Toplantı yarın saat üçte."

  input: "Bugün markete gideceğim yani."
  output: "Bugün markete gideceğim."

  input: "Ee, bu raporu bitirmem lazım."
  output: "Bu raporu bitirmem lazım."

type değeri: "filler", difficulty: "easy"
JSON array döndür.""",

"filler_medium": """\
{n} adet ORTA filler temizleme pair'i üret.
Kural: Cümle ortasında veya birden fazla filler var. Karmaşık duraklamalar.

Örnekler:
  input: "Bu projeyi, şey, önümüzdeki haftaya kadar, yani, teslim etmem gerekiyor."
  output: "Bu projeyi önümüzdeki haftaya kadar teslim etmem gerekiyor."

  input: "Müdüre, ee, şey, mail attım ama hani cevap gelmedi."
  output: "Müdüre mail attım ama cevap gelmedi."

  input: "Yani şey, bu sistemi hani düzeltmemiz lazım."
  output: "Bu sistemi düzeltmemiz lazım."

type değeri: "filler", difficulty: "medium"
JSON array döndür.""",

"filler_hard": """\
{n} adet ZOR filler temizleme pair'i üret.
Kural: Filler'lar cümle yapısını bozuyor, temizleme sonrası yeniden düzenleme gerekiyor.
Konu: iş, teknik, günlük — karışık.

Örnekler:
  input: "Yani şey hani bu kodu, şey, ee, refactor etmemiz, yani, çok önemli aslında şey."
  output: "Bu kodu refactor etmemiz çok önemli."

  input: "Ee şey yani toplantıda şey dediler ki hani bütçe şey kesilecekmiş yani."
  output: "Toplantıda bütçenin kesileceğini söylediler."

  input: "Şey şey şey nasıl desem yani bu kişiyle çalışmak hani zor oluyor işte."
  output: "Bu kişiyle çalışmak zor oluyor."

type değeri: "filler", difficulty: "hard"
JSON array döndür.""",

"semantic_yani": """\
{n} adet SEMANTİK YANI pair'i üret.
ÖNEMLI KURAL:
  - "yani" dolgu ise → KALDIR
  - "yani" "yani ki / demek ki / şu demek / yani şöyle" anlamındaysa → KORU veya "yani" yerine daha doğal ifade koy

Örnekler:
  input: "Toplantıya gidemeyeceğim, yani, hastalandım."
  output: "Toplantıya gidemeyeceğim; hastalandım."   ← dolgu, kaldırıldı

  input: "Proje bitti, yani artık deploy edebiliriz."
  output: "Proje bitti, yani artık deploy edebiliriz."  ← anlamlı, korundu

  input: "Yani bu karar yanlış, yani gerçekten düşünmeliyiz."
  output: "Bu karar yanlış, gerçekten düşünmeliyiz."  ← 1. yani dolgu, 2. yani korundu

type değeri: "semantic", difficulty: "hard"
JSON array döndür.""",

"backtrack": """\
{n} adet GERİ ALMA / DÜZELTME pair'i üret.
Kural: Kullanıcı konuşurken kendini düzeltiyor. Son niyet alınır, önceki iptal edilir.

Türkçe geri alma ifadeleri: "hayır dur", "pardon", "aslında", "yok yok",
  "dur bir saniye", "şöyle diyeyim", "scratch that", "onu sil"

Örnekler:
  input: "Toplantı salı günü, hayır dur, çarşamba günü saat ikide."
  output: "Toplantı çarşamba günü saat ikide."

  input: "Bütçe iki yüz bin, pardon, iki yüz elli bin lira olarak belirlendi."
  output: "Bütçe iki yüz elli bin lira olarak belirlendi."

  input: "Ali'ye mail at, yok yok, Mehmet'e at."
  output: "Mehmet'e mail at."

  input: "Bu fonksiyonu sil, dur bir saniye, şöyle diyeyim: bu fonksiyonu refactor et."
  output: "Bu fonksiyonu refactor et."

type değeri: "backtrack", difficulty: "medium"
JSON array döndür.""",

"stutter": """\
{n} adet TEKRAR / KEKEME pair'i üret.
Kural: Kelime veya hece tekrarlanıyor, sadece bir kez yaz.

Örnekler:
  input: "Bu bu fonksiyonu düzeltmem lazım."
  output: "Bu fonksiyonu düzeltmem lazım."

  input: "Top toplantı saat saat üçte başlıyor."
  output: "Toplantı saat üçte başlıyor."

  input: "Gi-gidecek misin yarın?"
  output: "Gidecek misin yarın?"

  input: "Şey şey şey nasıl açıklasam."
  output: "Nasıl açıklasam."

type değeri: "stutter", difficulty: "easy"
JSON array döndür.""",

"number": """\
{n} adet SAYI NORMALİZASYON pair'i üret.
Kural: Sözel sayıları rakama çevir (kontext'e uygun).

Örnekler:
  input: "İki bin yirmi altı yılında başladı."
  output: "2026 yılında başladı."

  input: "Yüzde seksen beş başarı oranına ulaştık."
  output: "%85 başarı oranına ulaştık."

  input: "Saat on beşte toplantı var."
  output: "Saat 15:00'te toplantı var."

  input: "Üç yüz elli milyon lira bütçe ayrıldı."
  output: "350 milyon lira bütçe ayrıldı."

  input: "Birinci çeyrek sonuçları açıklandı."
  output: "1. çeyrek sonuçları açıklandı."

Çeşitli konular: tarih, saat, para, yüzde, sıra sayısı, telefon, ölçü.
type değeri: "number", difficulty: "medium"
JSON array döndür.""",

}

# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def _call(client, prompt_key: str, n: int, retries: int = 3) -> list[dict]:
    prompt = _PROMPTS[prompt_key].format(n=n)
    for attempt in range(1, retries + 1):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            if raw.endswith("```"):
                raw = raw[:-3].strip()

            pairs = json.loads(raw)
            if not isinstance(pairs, list):
                raise ValueError("not a list")

            validated = []
            for p in pairs:
                if (
                    isinstance(p, dict)
                    and isinstance(p.get("input"), str)
                    and isinstance(p.get("output"), str)
                    and p["input"].strip()
                    and p["output"].strip()
                    and p["input"].strip() != p["output"].strip()  # anlamsız identity pair'leri dışla
                ):
                    validated.append({
                        "input": p["input"].strip(),
                        "output": p["output"].strip(),
                        "type": p.get("type", prompt_key.split("_")[0]),
                        "difficulty": p.get("difficulty", "medium"),
                    })
            return validated

        except Exception as e:
            print(f"  [attempt {attempt}/{retries}] {prompt_key}: {e}", file=sys.stderr)
            if attempt < retries:
                time.sleep(2 ** attempt)
    return []


# ---------------------------------------------------------------------------
# Plan: kaç pair, hangi kategoriden
# ---------------------------------------------------------------------------

# (prompt_key, target_count)
_PLAN = [
    ("filler_easy",    250),
    ("filler_medium",  250),
    ("filler_hard",    200),
    ("semantic_yani",  150),
    ("backtrack",      200),
    ("stutter",        150),
    ("number",         200),
    # Kalan pair'ler filler_medium'dan tamamlanır (en sık karşılaşılan durum)
]

TOTAL_TARGET = sum(t for _, t in _PLAN)  # 1400 — prepare_dataset.py ile ISSAI+eski data eklenir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Türkçe filler/disfluency temizleme pair'leri üret (Anthropic API).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--output", type=Path,
                        default=Path("../data/filler_pairs.jsonl"))
    parser.add_argument("--target", type=int, default=TOTAL_TARGET,
                        help="Toplam hedef pair sayısı (plan'ı orantılı ölçekler)")
    parser.add_argument("--batch-size", type=int, default=15,
                        help="Her API çağrısında kaç pair istenir")
    parser.add_argument("--delay", type=float, default=0.3,
                        help="API çağrıları arası bekleme (saniye)")
    parser.add_argument("--api-key", type=str, default=None)
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY eksik", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Hedefi plan oranlarına göre ölçekle
    scale = args.target / TOTAL_TARGET
    plan = [(k, max(10, int(t * scale))) for k, t in _PLAN]
    # Yuvarlama farkını son kategoriye ekle
    total_planned = sum(t for _, t in plan)
    if total_planned < args.target:
        plan[-1] = (plan[-1][0], plan[-1][1] + (args.target - total_planned))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    all_pairs: list[dict] = []

    for prompt_key, target in plan:
        collected: list[dict] = []
        print(f"\n[{prompt_key}] hedef={target}", file=sys.stderr)

        while len(collected) < target:
            remaining = target - len(collected)
            batch = min(args.batch_size, remaining)
            pairs = _call(client, prompt_key, batch)
            if pairs:
                collected.extend(pairs[:remaining])
                print(f"  {len(collected)}/{target}", file=sys.stderr, end="\r")
            else:
                print(f"  WARN: boş batch, tekrar deneniyor...", file=sys.stderr)
            if len(collected) < target:
                time.sleep(args.delay)

        print(f"  ✓ {len(collected)} pair", file=sys.stderr)
        all_pairs.extend(collected)

    random.shuffle(all_pairs)

    with open(args.output, "w", encoding="utf-8") as f:
        for p in all_pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\n{'─'*50}", file=sys.stderr)
    print(f"Toplam: {len(all_pairs)} pair → {args.output}", file=sys.stderr)
    counts: dict[str, int] = {}
    for p in all_pairs:
        k = f"{p['type']}:{p['difficulty']}"
        counts[k] = counts.get(k, 0) + 1
    for k, n in sorted(counts.items()):
        print(f"  {k}: {n}", file=sys.stderr)


if __name__ == "__main__":
    main()
