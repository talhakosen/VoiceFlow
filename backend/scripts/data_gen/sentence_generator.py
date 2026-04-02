"""sentence_generator.py — Qwen-max ile IT persona cümleleri üret.

Her persona için farklı senaryolarda doğal Türkçe IT cümleleri üretir.
Çıktı: whisper_sentences.jsonl — {persona, scenario, text, terms_used}

Kullanım:
    python sentence_generator.py                    # tüm personalar
    python sentence_generator.py --persona backend_dev
    python sentence_generator.py --count 50         # persona başına cümle sayısı
    python sentence_generator.py --dry-run          # API çağrısı yapmadan örnek göster
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from persona_terms import PERSONAS, Persona

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY  = os.getenv("ALIBABA_API_KEY", "")
ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL    = "qwen-max"

OUTPUT   = Path(__file__).parent / "whisper_sentences.jsonl"

# Senaryolar — her persona için farklı konuşma bağlamları
SCENARIOS = [
    ("standup",      "Sabah stand-up toplantısı. Dün ne yaptım, bugün ne yapacağım."),
    ("code_review",  "Kod incelemesi sırasında yorum yapıyorum."),
    ("debugging",    "Bir hatayı araştırıyorum ve bulguları açıklıyorum."),
    ("planning",     "Sprint planlama. Görevi açıklıyorum ve tahmin veriyorum."),
    ("pair",         "Pair programming. Neden böyle yazdığımı açıklıyorum."),
    ("slack",        "Slack'te kısa teknik mesaj yazıyorum (sesle)."),
    ("pr_comment",   "Pull request yorumu. Değişikliği özetliyorum."),
]

SYSTEM_PROMPT = """Sen deneyimli bir Türk yazılım geliştiricisisin.
Görevin: verilen teknik terimler ve senaryoya uygun, GERÇEK bir geliştiricinin söyleyeceği
kısa Türkçe cümleler üretmek.

Kurallar:
- Her cümle 1-3 cümlelik kısa konuşma parçası olsun (sesli dikte gibi)
- Teknik terimleri olduğu gibi İngilizce kullan (Docker, Kubernetes vb.)
- Doğal konuşma dili — çok resmi olmasın
- Filler kelime KULLANMA (yani, şey, işte)
- Her satırda sadece bir cümle/konuşma parçası
- JSON formatında döndür: {{"sentences": ["cümle1", "cümle2", ...]}}
- Tam olarak {count} farklı cümle üret"""

USER_PROMPT = """Persona: {persona_desc}
Senaryo: {scenario_desc}
Kullanılacak terimler (hepsini kullanmak zorunda değilsin, doğal gelenleri seç): {terms}
Üretilecek cümle sayısı: {count}

JSON formatında döndür."""

# Terim-odaklı üretim için ayrı prompt
TERM_SYSTEM_PROMPT = """Sen deneyimli bir Türk yazılım geliştiricisisin.
Görevin: verilen teknik terimi içeren {count} farklı kısa Türkçe cümle üretmek.

Kurallar:
- Her cümle farklı bir bağlamda olsun (standup, code review, debug, plan, slack vb.)
- Terimi olduğu gibi İngilizce kullan, Türkçe ekler takılabilir (Docker'ı, Kubernetes'te)
- 1-2 cümlelik kısa konuşma parçası (sesli dikte gibi)
- Filler kelime KULLANMA (yani, şey, işte)
- JSON formatında döndür: {{"sentences": ["cümle1", "cümle2", ...]}}
- Tam olarak {count} farklı cümle üret"""

TERM_USER_PROMPT = """Terim: {term}
Türkçe telaffuz varyantları (bilgi için): {variants}
Bağlam: Türkiye IT sektöründe çalışan geliştirici

{count} farklı cümle üret. Her cümle farklı bir iş bağlamında olsun."""


# ── API ───────────────────────────────────────────────────────────────────────

def _parse_response(content: str) -> list[str]:
    """Qwen yanıtını parse et — markdown code block, düz JSON, control char temizle."""
    import re
    content = content.strip()
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    # Control characters temizle (Qwen bazen \n içinde \r veya benzeri atar)
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    return json.loads(content).get("sentences", [])


def call_qwen(persona: Persona, scenario: tuple[str, str], count: int) -> list[str]:
    terms_sample = random.sample(persona.terms, min(8, len(persona.terms)))
    terms_str = ", ".join(t[0] for t in terms_sample)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(count=count)},
        {"role": "user",   "content": USER_PROMPT.format(
            persona_desc=persona.description,
            scenario_desc=scenario[1],
            terms=terms_str,
            count=count,
        )},
    ]

    resp = httpx.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "temperature": 0.9, "max_tokens": 1500},
        timeout=60,
    )
    resp.raise_for_status()
    return _parse_response(resp.json()["choices"][0]["message"]["content"])


def call_qwen_term(term: str, variants: list[str], count: int) -> list[str]:
    """Tek terim için odaklı cümle üret."""
    variants_str = ", ".join(variants[:4]) if variants else term

    messages = [
        {"role": "system", "content": TERM_SYSTEM_PROMPT.format(count=count)},
        {"role": "user",   "content": TERM_USER_PROMPT.format(
            term=term,
            variants=variants_str,
            count=count,
        )},
    ]

    resp = httpx.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "temperature": 0.9, "max_tokens": 1500},
        timeout=60,
    )
    resp.raise_for_status()
    return _parse_response(resp.json()["choices"][0]["message"]["content"])


# ── Ana Akış ──────────────────────────────────────────────────────────────────

def generate(
    personas: list[Persona],
    count_per_scenario: int = 10,
    dry_run: bool = False,
    output: Path | None = None,
) -> list[dict]:
    results = []

    for persona in personas:
        print(f"\n▶ {persona.name} ({len(persona.terms)} terim)", flush=True)

        for scenario in SCENARIOS:
            if dry_run:
                print(f"  [dry-run] {scenario[0]}: {count_per_scenario} cümle atlandı", flush=True)
                continue

            try:
                sentences = call_qwen(persona, scenario, count_per_scenario)
                batch = []
                for sent in sentences:
                    sent = sent.strip()
                    if len(sent) < 10:
                        continue
                    entry = {"persona": persona.name, "scenario": scenario[0], "text": sent}
                    results.append(entry)
                    batch.append(entry)
                if output and batch:
                    with open(output, "a") as f:
                        for e in batch:
                            f.write(json.dumps(e, ensure_ascii=False) + "\n")
                print(f"  ✓ {scenario[0]}: {len(sentences)} cümle", flush=True)
                time.sleep(0.5)
            except Exception as e:
                print(f"  ✗ {scenario[0]}: {e}", flush=True)
                time.sleep(2)

    return results


def generate_term_focused(
    count_per_term: int = 10,
    dry_run: bool = False,
    output: Path | None = None,
) -> list[dict]:
    """Her terim için odaklı cümleler üret (terim başına count_per_term cümle)."""
    from persona_terms import get_all_terms
    all_terms = get_all_terms()
    results = []

    print(f"\n▶ Terim-odaklı üretim: {len(all_terms)} terim × {count_per_term} cümle")

    for i, (term, variants) in enumerate(all_terms, 1):
        if dry_run:
            print(f"  [dry-run] {term}: {count_per_term} cümle atlandı")
            continue
        try:
            sentences = call_qwen_term(term, variants, count_per_term)
            batch = []
            for sent in sentences:
                sent = sent.strip()
                if len(sent) < 8:
                    continue
                entry = {"persona": "term_focused", "scenario": "term_focused", "term": term, "text": sent}
                results.append(entry)
                batch.append(entry)
            if output and batch:
                with open(output, "a") as f:
                    for e in batch:
                        f.write(json.dumps(e, ensure_ascii=False) + "\n")
            print(f"  ✓ [{i:3}/{len(all_terms)}] {term}: {len(sentences)} cümle", flush=True)
            time.sleep(0.4)
        except Exception as e:
            print(f"  ✗ [{i:3}/{len(all_terms)}] {term}: {e}")
            time.sleep(2)

    return results


def save(results: list[dict], path: Path) -> None:
    existing: list[dict] = []
    if path.exists():
        with open(path) as f:
            existing = [json.loads(l) for l in f if l.strip()]

    all_results = existing + results
    with open(path, "w") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n✅ {len(results)} yeni cümle → {path} (toplam: {len(all_results)})")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Qwen-max ile IT cümleleri üret")
    parser.add_argument("--mode",      choices=["persona", "term", "all"], default="all",
                        help="persona: senaryo bazlı | term: terim odaklı | all: ikisi (default: all)")
    parser.add_argument("--persona",   help="Sadece bu persona (ör: backend_dev) — mode=persona ile kullan")
    parser.add_argument("--count",     type=int, default=10, help="Senaryo/terim başına cümle (default: 10)")
    parser.add_argument("--dry-run",   action="store_true", help="API çağrısı yapma")
    parser.add_argument("--output",    default=str(OUTPUT), help="Çıktı dosyası")
    args = parser.parse_args()

    if not API_KEY and not args.dry_run:
        print("HATA: ALIBABA_API_KEY env var eksik")
        sys.exit(1)

    out_path = Path(args.output)
    print(f"Model  : {MODEL} @ DashScope")
    print(f"Çıktı  : {out_path}")
    if args.dry_run:
        print("[DRY RUN — API çağrısı yapılmayacak]")

    results = []

    if args.mode in ("persona", "all"):
        selected = PERSONAS
        if args.persona:
            selected = [p for p in PERSONAS if p.name == args.persona]
            if not selected:
                print(f"Persona bulunamadı: {args.persona}")
                print(f"Mevcut: {[p.name for p in PERSONAS]}")
                sys.exit(1)
        total = len(selected) * len(SCENARIOS) * args.count
        print(f"\nPersona modu: ~{total} cümle ({[p.name for p in selected]})")
        results += generate(selected, count_per_scenario=args.count, dry_run=args.dry_run, output=out_path)

    if args.mode in ("term", "all"):
        from persona_terms import get_all_terms
        total = len(get_all_terms()) * args.count
        print(f"\nTerim modu: ~{total} cümle ({len(get_all_terms())} terim × {args.count})")
        results += generate_term_focused(count_per_term=args.count, dry_run=args.dry_run, output=out_path)

    if not args.dry_run and results:
        save(results, Path(args.output))
    elif args.dry_run:
        print(f"\n[dry-run] toplam ~{len(results) or '?'} cümle üretilecekti")


if __name__ == "__main__":
    main()
