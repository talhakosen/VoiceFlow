"""
domain_generator.py — Proje-spesifik domain training pair üreteci.

Kullanım:
  python domain_generator.py \
      --project oneri \
      --output ../oneri_pairs.jsonl \
      --count 2000

Her pair: Whisper'ın yanlış yazacağı input → doğru output
Örnek:
  input:  "normalized product class'ını güncelle"
  output: "NormalizedProduct class'ını güncelle."
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path
from itertools import product as iterproduct


# ---------------------------------------------------------------------------
# Oneri project vocabulary
# ---------------------------------------------------------------------------

ONERI_VOCAB = {
    # Core entities
    "classes": [
        ("NormalizedProduct",       "normalized product"),
        ("WardrobeItem",            "wardrobe item"),
        ("Outfit",                  "outfit"),
        ("OutfitOrder",             "outfit order"),
        ("SavedOutfit",             "saved outfit"),
        ("StyleProfile",            "style profile"),
        ("UserProfile",             "user profile"),
        ("UserPreferences",         "user preferences"),
        ("PriceAlert",              "price alert"),
        ("FeedFilter",              "feed filter"),
        ("BlogPost",                "blog post"),
        ("ItemFeedbackData",        "item feedback data"),
        ("OutfitFeedbackData",      "outfit feedback data"),
    ],
    # Repositories / Services
    "repositories": [
        ("SupabaseProductRepository",       "supabase product repository"),
        ("SupabaseWardrobeRepository",      "supabase wardrobe repository"),
        ("SupabaseOutfitOrderRepository",   "supabase outfit order repository"),
        ("SupabaseSavedOutfitRepository",   "supabase saved outfit repository"),
        ("SupabaseFeedbackRepository",      "supabase feedback repository"),
        ("SupabasePipelineRepository",      "supabase pipeline repository"),
        ("SupabaseUserRepository",          "supabase user repository"),
        ("SupabaseAuthRepository",          "supabase auth repository"),
        ("SupabaseAlertRepository",         "supabase alert repository"),
        ("SupabaseNotificationRepository",  "supabase notification repository"),
        ("ProductRepository",               "product repository"),
        ("WardrobeRepository",              "wardrobe repository"),
        ("OutfitOrderRepository",           "outfit order repository"),
    ],
    # State notifiers (Riverpod)
    "notifiers": [
        ("ProductFeedNotifier",         "product feed notifier"),
        ("OutfitOrdersNotifier",        "outfit orders notifier"),
        ("WardrobeItemsNotifier",       "wardrobe items notifier"),
        ("StyleProfileNotifier",        "style profile notifier"),
        ("UserProfileNotifier",         "user profile notifier"),
        ("AuthNotifier",                "auth notifier"),
        ("PipelineHealthNotifier",      "pipeline health notifier"),
        ("BlogNotifier",                "blog notifier"),
        ("NotificationsNotifier",       "notifications notifier"),
        ("FeedFilterNotifier",          "feed filter notifier"),
        ("ProductBrowseNotifier",       "product browse notifier"),
        ("OutfitFeedbackNotifier",      "outfit feedback notifier"),
        ("OrderFormNotifier",           "order form notifier"),
    ],
    # ML / Technical
    "ml": [
        ("TypeAwareProjection",     "type aware projection"),
        ("CompatibilityScorer",     "compatibility scorer"),
        ("SigLIP",                  "siglip"),
        ("SegFormer",               "seg former"),
        ("SigLIP",                  "sig lip"),
        ("SegFormer",               "segformer"),
        ("TypeAwareProjection",     "type aware projeksiyon"),
    ],
    # Screens / UI
    "screens": [
        ("WardrobeScreen",                  "wardrobe screen"),
        ("WardrobeItemCard",                "wardrobe item card"),
        ("WardrobeItemDetailScreen",        "wardrobe item detail screen"),
        ("WardrobeEnrichmentStatusCard",    "wardrobe enrichment status card"),
        ("WardrobeStyleAnalysisCard",       "wardrobe style analysis card"),
        ("ProfileScreen",                   "profile screen"),
        ("OnboardingScreen",                "onboarding screen"),
        ("OutfitCard",                      "outfit card"),
        ("ProductFeedCard",                 "product feed card"),
        ("CompatibleProductsSection",       "compatible products section"),
        ("BodyTypeSelectorSheet",           "body type selector sheet"),
        ("BodyMeasurementGuide",            "body measurement guide"),
    ],
    # Enums / Status
    "enums": [
        ("ClassificationStatus",    "classification status"),
        ("ProcessingStatus",        "processing status"),
        ("EnrichmentStatus",        "enrichment status"),
    ],
    # Turkish domain terms (common mistakes)
    "turkish_terms": [
        ("kıyafet",     "kiyafet"),
        ("gardrop",     "gardrap"),
        ("kombin",      "kombim"),
        ("uyum",        "uyun"),
        ("siluet",      "silüet"),
        ("arketip",     "arketib"),
        ("formality",   "formalite"),
        ("versatility", "versatility"),
        ("embedding",   "embeding"),
        ("segmentation","segmentasyon"),
    ],
}

# ---------------------------------------------------------------------------
# Sentence templates — developer speech patterns
# ---------------------------------------------------------------------------

# {class} = correct class name, {whisper} = what whisper hears
TEMPLATES_REFERENCE = [
    ("{class} class'ına bak",               "{whisper} class'ına bak"),
    ("{class} modelini güncelle",            "{whisper} modelini güncelle"),
    ("{class} interface'ini implement et",   "{whisper} interface'ini implement et"),
    ("{class} içinde bir hata var",          "{whisper} içinde bir hata var"),
    ("{class} neden çalışmıyor",             "{whisper} neden çalışmıyor"),
    ("{class} kullanarak veriyi çek",        "{whisper} kullanarak veriyi çek"),
    ("{class} objesini oluştur",             "{whisper} objesini oluştur"),
    ("{class} tipini kontrol et",            "{whisper} tipini kontrol et"),
    ("{class}'ı inject et",                  "{whisper}'ı inject et"),
    ("{class} constructor'ına parametre ekle", "{whisper} constructor'ına parametre ekle"),
    ("bu {class} ne yapıyor",               "bu {whisper} ne yapıyor"),
    ("{class}'ı refactor et",               "{whisper}'ı refactor et"),
    ("{class} testini yaz",                 "{whisper} testini yaz"),
    ("yeni bir {class} oluştur",            "yeni bir {whisper} oluştur"),
    ("{class}'ın metodunu ekle",            "{whisper}'ın metodunu ekle"),
]

TEMPLATES_REPO = [
    ("{class}'den veri çek",                "{whisper}'den veri çek"),
    ("{class}'e kaydet",                    "{whisper}'e kaydet"),
    ("{class} üzerinden query çalıştır",    "{whisper} üzerinden query çalıştır"),
    ("{class}'i mock'la",                   "{whisper}'i mock'la"),
    ("{class} metodunu override et",        "{whisper} metodunu override et"),
    ("{class}'den kullanıcıyı getir",       "{whisper}'den kullanıcıyı getir"),
    ("{class} ile outfit'i kaydet",         "{whisper} ile outfit'i kaydet"),
    ("{class}'e yeni method ekle",          "{whisper}'e yeni method ekle"),
    ("{class} dependency'sini düzelt",      "{whisper} dependency'sini düzelt"),
]

TEMPLATES_NOTIFIER = [
    ("{class}'ı dinle",                     "{whisper}'ı dinle"),
    ("{class} state'ini sıfırla",           "{whisper} state'ini sıfırla"),
    ("{class}'den veri al",                 "{whisper}'den veri al"),
    ("{class} provider'ını tanımla",        "{whisper} provider'ını tanımla"),
    ("{class} refresh et",                  "{whisper} refresh et"),
    ("{class}'e error state'i ekle",        "{whisper}'e error state'i ekle"),
    ("{class}'ın loading state'ini yönet",  "{whisper}'ın loading state'ini yönet"),
    ("bu {class} neden tekrar build alıyor", "bu {whisper} neden tekrar build alıyor"),
]

TEMPLATES_ML = [
    ("{class} modelini yükle",              "{whisper} modelini yükle"),
    ("{class} ile embedding hesapla",       "{whisper} ile embedding hesapla"),
    ("{class} inference çalıştır",          "{whisper} inference çalıştır"),
    ("{class} kaç boyutlu",                 "{whisper} kaç boyutlu"),
    ("{class} checkpoint'ini kaydet",       "{whisper} checkpoint'ini kaydet"),
    ("{class} modeli eğit",                 "{whisper} modeli eğit"),
    ("{class} score'u hesapla",             "{whisper} score'u hesapla"),
    ("{class} pipeline'ını çalıştır",       "{whisper} pipeline'ını çalıştır"),
]

TEMPLATES_SCREEN = [
    ("{class}'ı açtığında",                 "{whisper}'ı açtığında"),
    ("{class} widget'ını ekle",             "{whisper} widget'ını ekle"),
    ("{class}'de navigation düzelt",        "{whisper}'de navigation düzelt"),
    ("{class}'in tasarımını değiştir",      "{whisper}'in tasarımını değiştir"),
    ("{class}'de loading göster",           "{whisper}'de loading göster"),
    ("bu {class} çok fazla rebuild alıyor", "bu {whisper} çok fazla rebuild alıyor"),
    ("{class}'e animasyon ekle",            "{whisper}'e animasyon ekle"),
]

TEMPLATES_TURKISH = [
    ("kıyafet önerisi oluştur",             "kiyafet önerisi oluştur"),
    ("gardrop analizi yap",                 "gardrap analizi yap"),
    ("kombin uyumu hesapla",                "kombim uyumu hesapla"),
    ("siluet bilgisini kaydet",             "silüet bilgisini kaydet"),
    ("arketip etiketlerini güncelle",       "arketib etiketlerini güncelle"),
    ("embedding boyutunu kontrol et",       "embeding boyutunu kontrol et"),
    ("segmentation sonucunu parse et",      "segmentasyon sonucunu parse et"),
    ("formality seviyesini ayarla",         "formalite seviyesini ayarla"),
    ("versatility score'unu hesapla",       "versatiliti score'unu hesapla"),
    ("kıyafet kategorisini bul",            "kiyafet kategorisini bul"),
]

# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def _add_punctuation(text: str) -> str:
    """Cümle sonuna nokta ekle (yoksa)."""
    text = text.strip()
    if text and text[-1] not in '.!?…':
        text += '.'
    return text[0].upper() + text[1:] if text else text


def _make_whisper_input(whisper_text: str) -> str:
    """Whisper'ın üretebileceği gürültülü input: küçük harf, bazen ekstra boşluk."""
    return whisper_text.strip().lower()


def generate_pairs(vocab: dict, count: int, seed: int = 42) -> list[dict]:
    random.seed(seed)
    pairs = []

    # Her kategori için template'lerle pair üret
    category_map = [
        ("classes",      TEMPLATES_REFERENCE),
        ("repositories", TEMPLATES_REPO),
        ("notifiers",    TEMPLATES_NOTIFIER),
        ("ml",           TEMPLATES_ML),
        ("screens",      TEMPLATES_SCREEN),
    ]

    for category, templates in category_map:
        for (correct, whisper_form) in vocab[category]:
            for tmpl_correct, tmpl_whisper in templates:
                output_text = tmpl_correct.replace("{class}", correct)
                input_text  = tmpl_whisper.replace("{whisper}", whisper_form)

                input_clean  = _make_whisper_input(input_text)
                output_clean = _add_punctuation(output_text)

                if input_clean == output_clean.lower().rstrip('.'):
                    continue  # fark yoksa atla

                pairs.append({
                    "input":    input_clean,
                    "output":   output_clean,
                    "category": f"domain_oneri_{category}",
                })

    # Turkish term pairs
    for tmpl_out, tmpl_in in TEMPLATES_TURKISH:
        pairs.append({
            "input":    _make_whisper_input(tmpl_in),
            "output":   _add_punctuation(tmpl_out),
            "category": "domain_oneri_turkish",
        })

    # Deduplicate
    seen = set()
    deduped = []
    for p in pairs:
        key = (p["input"], p["output"])
        if key not in seen:
            seen.add(key)
            deduped.append(p)

    # Shuffle + cap
    random.shuffle(deduped)
    if count and len(deduped) > count:
        deduped = deduped[:count]

    return deduped


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Domain-specific training pair generator.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--project", default="oneri", help="Project name (for category tag).")
    parser.add_argument("--output",  type=Path, default=Path("../oneri_pairs.jsonl"))
    parser.add_argument("--count",   type=int,  default=0, help="Max pairs (0 = all).")
    parser.add_argument("--seed",    type=int,  default=42)
    args = parser.parse_args()

    pairs = generate_pairs(ONERI_VOCAB, args.count, args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"Generated {len(pairs)} pairs → {args.output}", file=sys.stderr)
    print(f"Categories: {set(p['category'] for p in pairs)}", file=sys.stderr)


if __name__ == "__main__":
    main()
