"""smart_dictionary.py — Kod tabanından identifier çıkar, Türkçe varyantları dictionary'e ekle.

Indexleme sırasında otomatik çağrılır. Bir Türk developer'ın Whisper'a söyleyeceği
şekillerde class/method isimlerinin varyantlarını üretir.

Örnek:
  SupabaseSavedOutfitRepository →
    triggers: ["supabase saved outfit repository",
               "superbase saved outfit reposteri",
               "superbase saved outfit repozitori", ...]
    replacement: "SupabaseSavedOutfitRepository"
"""

import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Türkçe fonetik kuralları — İngilizce teknik kelime → olası Türkçe telaffuzlar
# ---------------------------------------------------------------------------

_TURKISH_VARIANTS: dict[str, list[str]] = {
    # Framework / altyapı
    "supabase":       ["superbase", "superbased", "superbeys", "süperbase", "super base", "super bass", "superbass", "super 5", "superbeer"],
    "repository":     ["reposteri", "repozitori", "repositori", "reposter", "repozitoru", "tripoteri", "triposteri"],
    "notifier":       ["notifayr", "notifeyr", "notifayer"],
    "controller":     ["kontroler", "kontrolör", "kontroller"],
    "manager":        ["menejer", "manajer", "menecer"],
    "provider":       ["provayır", "provayider", "sağlayıcı"],
    "service":        ["servis"],
    "interface":      ["interfeys", "arayüz"],
    "factory":        ["faktori", "fabrika"],
    "builder":        ["bildır", "oluşturucu"],
    "observer":       ["obzerver", "gözlemci"],
    "dispatcher":     ["dispetçer", "dağıtıcı"],
    "middleware":     ["midılveyr", "arakatman"],
    "authentication": ["otantikasyon", "kimlik doğrulama"],
    "authorization":  ["yetkilendirme", "otorizasyon"],
    "configuration":  ["konfigürasyon", "konfigurasyon", "yapılandırma"],
    "exception":      ["ekzepşon", "hata"],
    "notification":   ["bildirim", "notifikasyon"],
    "pagination":     ["sayfalama", "paginasyon"],
    "serializer":     ["serializır", "serializör"],
    "validator":      ["validatör", "doğrulayıcı"],
    "interceptor":    ["interseptör"],
    "transformer":    ["transformır", "dönüştürücü"],
    "aggregator":     ["agregatör"],
    "subscriber":     ["subscrıyber", "abone"],
    "publisher":      ["yayıncı", "publishır"],
    "listener":       ["listınır", "dinleyici"],
    "handler":        ["hendler", "işleyici"],
    "wrapper":        ["repper", "sarmalayıcı"],
    "adapter":        ["adaptör"],
    "decorator":      ["dekoratör"],
    "singleton":      ["singleten", "tekil"],
    # Flutter/Dart spesifik
    "notifier":       ["notifayr", "notifeyr"],
    "riverpod":       ["rivırpod", "river pod"],
    "widget":         ["vidcet", "bileşen"],
    "scaffold":       ["iskafold", "scaffold"],
    "stateful":       ["steytful", "durumlu"],
    "stateless":      ["steytles", "durumsuz"],
    # Domain (oneri spesifik)
    "outfit":         ["autfit", "outfıt"],
    "wardrobe":       ["gardrop", "wardrop"],
    "compatibility":  ["uyumluluk", "kompatibilite"],
    "embeddings":     ["embedings", "vektörler"],
    "segmentation":   ["segmentasyon"],
    "enrichment":     ["zenginleştirme", "enrichmınt"],
    "inference":      ["inferans", "çıkarım"],
    "pipeline":       ["payplayn", "boru hattı"],
    # Genel yazılım — Whisper İngilizce kelime hataları
    "menu":           ["many", "meny", "menue"],
    "paste":          ["pace", "paced", "peyst", "pest"],
    "bar":            ["bar", "bır"],
    "view":           ["viu", "viev", "viev"],
    "model":          ["modıl", "modil"],
    "binding":        ["bayning", "bayndıng"],
    "fetch":          ["feç", "fech"],
    "cache":          ["keş", "kayş", "caş"],
    "mock":           ["mok", "moc"],
    "store":          ["stor", "stör"],
    "router":         ["rutır", "rautır"],
    "stack":          ["stek", "steck"],
    "query":          ["kueri", "query"],
    "token":          ["tökın", "tokin"],
    "hook":           ["huk", "hook"],
    "render":         ["rendır", "rendır"],
    "layout":         ["leyaut", "leayout"],
    "payload":        ["peyload", "paylod"],
    # Yazılım terimleri (kavramsal)
    "coupling":       ["kaplıng", "coupling", "kaplıng"],
    "dependency":     ["dependensi", "dipendenci", "bağımlılık"],
    "injection":      ["injeksiyon", "injecşon"],
    "abstraction":    ["abstraksiyon", "soyutlama"],
    "refactor":       ["rifaktör", "refaktör"],
    "architecture":   ["arkitektür", "arşitekçır", "mimari"],
    "migration":      ["migrasyon", "migrasyon"],
    "deployment":     ["dıploymınt", "deploy"],
    "concurrency":    ["concurrency", "eşzamanlılık"],
    "inheritance":    ["inheritance", "kalıtım"],
    "polymorphism":   ["polimorfizm", "çok biçimlilik"],
    "encapsulation":  ["enkapsülasyon", "kapsülleme"],
    # Genel yazılım
    "callback":       ["kolbek", "geri çağırma"],
    "async":          ["eysink", "asenkron"],
    "await":          ["aveyt"],
    "override":       ["overrayd", "geçersiz kılma"],
    "implement":      ["implementasyon", "uygulama"],
    "instance":       ["instans", "örnek"],
    "parameter":      ["parametre", "paramiter"],
    "argument":       ["argüman"],
    "boolean":        ["boolın", "mantıksal"],
    "integer":        ["ıntıcır", "tam sayı"],
    "string":         ["strıng", "metin"],
    "array":          ["errey", "dizi"],
    "object":         ["obje", "nesne"],
    "class":          ["klas", "sınıf"],
    "function":       ["fonksiyon", "fonksiyon"],
    "method":         ["metot", "yöntem"],
    "property":       ["propertı", "özellik"],
    "variable":       ["varyabl", "değişken"],
    "constant":       ["konstant", "sabit"],
    "interface":      ["interfeys", "arayüz"],
    "generic":        ["cenerik", "genel"],
    "extension":      ["ekstansiyon", "uzantı"],
    "protocol":       ["protokol"],
    "delegate":       ["delıget", "temsilci"],
    "enum":           ["inum", "sayım"],
    "struct":         ["strakt", "yapı"],
    "computed":       ["hesaplanan"],
    "optional":       ["opsiyonel", "isteğe bağlı"],
}


def _split_camel_case(name: str) -> list[str]:
    """PascalCase / camelCase → kelime listesi.

    SupabaseSavedOutfitRepository → ['Supabase', 'Saved', 'Outfit', 'Repository']
    getUserById → ['get', 'User', 'By', 'Id']
    """
    # Büyük harften önce boşluk ekle, ardışık büyük harfleri koru (e.g. XMLParser)
    parts = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    parts = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', parts)
    return [p for p in parts.split() if p]


def _extract_identifiers(folder_path: Path) -> set[str]:
    """Kod dosyalarından PascalCase/camelCase identifier'ları çıkar."""
    _CODE_EXTENSIONS = {".py", ".swift", ".ts", ".js", ".dart", ".go", ".java", ".kt"}
    identifiers: set[str] = set()

    # PascalCase: büyük harfle başlayan, en az 2 büyük harf veya 6+ karakter
    pascal_re = re.compile(r'\b([A-Z][a-zA-Z0-9]{5,})\b')
    # camelCase: küçükle başlar, içinde büyük var
    camel_re  = re.compile(r'\b([a-z][a-z0-9]+(?:[A-Z][a-z0-9]+)+)\b')

    for file_path in folder_path.rglob("*"):
        if any(p.startswith(".") or p == "__pycache__" or p == "node_modules" for p in file_path.parts):
            continue
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in _CODE_EXTENSIONS:
            continue
        if file_path.stat().st_size > 500_000:
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            identifiers.update(pascal_re.findall(text))
            identifiers.update(camel_re.findall(text))
        except Exception:
            pass

    # Çok kısa veya çok uzun olanları at
    return {i for i in identifiers if 6 <= len(i) <= 60}


def _generate_triggers(identifier: str) -> list[tuple[str, str]]:
    """Bir identifier için (trigger, replacement) çiftleri üret.

    tech_lexicon.generate_triggers() kullanır:
      UserService → ["user servis", "kullanıcı servis", "yuzır out", ...]
    """
    from voiceflow.services.tech_lexicon import generate_triggers
    triggers = generate_triggers(identifier)
    return [(t, identifier) for t in triggers if t != identifier.lower()]


async def build_smart_dictionary(folder_path: str, user_id: str) -> int:
    """Klasörü tara, identifier'ları çıkar, dictionary'e ekle.

    Returns: eklenen entry sayısı
    """
    import aiosqlite
    from pathlib import Path as P

    DB_PATH = P.home() / ".voiceflow" / "voiceflow.db"

    root = P(folder_path).expanduser().resolve()
    if not root.exists():
        return 0

    logger.info("Smart dictionary: scanning %s for user %s", root, user_id)
    identifiers = _extract_identifiers(root)
    logger.info("Smart dictionary: found %d identifiers", len(identifiers))

    all_pairs: list[tuple[str, str]] = []
    for ident in identifiers:
        all_pairs.extend(_generate_triggers(ident))

    # Deduplicate by trigger
    seen_triggers: set[str] = set()
    unique_pairs: list[tuple[str, str]] = []
    for trigger, replacement in all_pairs:
        if trigger and replacement and trigger not in seen_triggers and trigger != replacement.lower():
            seen_triggers.add(trigger)
            unique_pairs.append((trigger, replacement))

    if not unique_pairs:
        return 0

    added = 0
    async with aiosqlite.connect(DB_PATH) as db:
        # Mevcut trigger'ları al — üzerine yazma
        async with db.execute(
            "SELECT trigger FROM user_dictionary WHERE user_id = ?", (user_id,)
        ) as cursor:
            existing = {row[0] for row in await cursor.fetchall()}

        for trigger, replacement in unique_pairs:
            if trigger in existing:
                continue
            await db.execute(
                "INSERT INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) VALUES (?, ?, ?, ?, ?)",
                ("default", user_id, trigger, replacement, "smart"),
            )
            added += 1

        await db.commit()

    logger.info("Smart dictionary: added %d new entries for %s", added, user_id)
    return added
