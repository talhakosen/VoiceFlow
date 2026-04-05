"""tech_lexicon.py — Turkish developer phonetic lexicon for technical identifiers.

Two layers:
  Layer 1 (UNIVERSAL): Software architecture suffixes valid for any IT project.
                        e.g. Service → ["servis", "out", "sörvis", ...]
  Layer 2 (PROJECT):   Domain-specific words per project.
                        e.g. Outfit → ["autfit", "outfıt"]

Usage:
  from voiceflow.services.tech_lexicon import generate_triggers
  triggers = generate_triggers("UserService")
  # → ["user servis", "yuzır servis", "kullanıcı servis", "user out", ...]
"""

from __future__ import annotations
import re

# ---------------------------------------------------------------------------
# Layer 1 — Universal suffix lexicon
# Every Turkish dev says these words; covers all IT departments.
# ---------------------------------------------------------------------------

UNIVERSAL_SUFFIXES: dict[str, list[str]] = {
    # Architecture patterns
    "Service":       ["servis", "sörvis", "servisim", "servisi", "out", "öt", "ot"],
    "Repository":    ["repo", "reposteri", "repozitori", "repositori", "reposu", "tripoteri"],
    "ViewModel":     ["view model", "vyu model", "viu model", "viewmodel", "fyu model"],
    "Controller":    ["kontroler", "kontrolör", "kontroller", "controller"],
    "UseCase":       ["use case", "yuz keys", "yus kays", "yuz kays", "use keys"],
    "Interactor":    ["interaktör", "interactor"],
    "Presenter":     ["prezenter", "presenter"],
    "Coordinator":   ["koordinatör", "coordinator"],
    "Router":        ["rutır", "router", "rautır"],
    "Navigator":     ["navigator", "navigatör"],

    # Data / persistence
    "Manager":       ["menejer", "manajer", "manager", "menecer"],
    "Store":         ["stor", "stör", "store"],
    "Cache":         ["keş", "kayş", "cache"],
    "Database":      ["veritabanı", "database", "deytabeys"],
    "DataSource":    ["data source", "deyta sors", "veri kaynağı"],

    # UI
    "View":          ["vyu", "viu", "view", "fyu"],
    "Screen":        ["skrin", "ekran", "screen"],
    "Widget":        ["vidcet", "widget", "bicet"],
    "Component":     ["komponent", "bileşen", "component"],
    "Cell":          ["sel", "hücre", "cell"],
    "Layout":        ["leyaut", "leayout", "düzen"],

    # Patterns
    "Provider":      ["provayır", "provayider", "provider", "sağlayıcı"],
    "Factory":       ["faktori", "fabrika", "factory"],
    "Builder":       ["bildır", "builder", "oluşturucu"],
    "Handler":       ["hendler", "handler", "işleyici"],
    "Observer":      ["obzerver", "observer", "gözlemci"],
    "Listener":      ["listınır", "listener", "dinleyici"],
    "Adapter":       ["adaptör", "adapter"],
    "Wrapper":       ["repper", "wrapper", "sarmalayıcı"],
    "Decorator":     ["dekoratör", "decorator"],
    "Interceptor":   ["interseptör", "interceptor"],
    "Dispatcher":    ["dispetçer", "dispatcher"],
    "Notifier":      ["notifayr", "notifeyr", "notifier"],
    "Subscriber":    ["subscrıyber", "subscriber"],
    "Publisher":     ["yayıncı", "publisher"],

    # Networking / API
    "Client":        ["klayınt", "client", "istemci"],
    "Request":       ["rikuest", "request", "istek"],
    "Response":      ["rıspons", "response", "yanıt"],
    "Endpoint":      ["endpoynt", "endpoint"],
    "Gateway":       ["geytway", "gateway", "geçit"],
    "Middleware":    ["midılveyr", "middleware", "arakatman"],

    # Auth / Security
    "Auth":          ["out", "ot", "aut", "öt", "auth"],
    "Token":         ["tökın", "token"],
    "Session":       ["seşın", "session", "oturum"],

    # Testing
    "Mock":          ["mok", "mock"],
    "Stub":          ["stab", "stub"],
    "Spy":           ["spay", "spy"],

    # State management (Flutter/React)
    "State":         ["steyt", "state", "durum"],
    "Bloc":          ["blok", "bloc"],
    "Cubit":         ["kübit", "cubit"],
    "Reducer":       ["rıdusır", "reducer"],
    "Action":        ["aksiyon", "action", "eylem"],
    "Event":         ["ivent", "event", "olay"],
    "Effect":        ["efekt", "effect"],

    # ML / Data
    "Model":         ["modıl", "model", "modeli"],
    "Embedding":     ["embeding", "embedding"],
    "Pipeline":      ["payplayn", "pipeline"],
    "Processor":     ["prosesör", "processor"],
    "Transformer":   ["transformır", "transformer"],

    # Misc
    "Helper":        ["helper", "helpır", "yardımcı"],
    "Utils":         ["yutıls", "utils", "araçlar"],
    "Extension":     ["ekstansiyon", "extension"],
    "Protocol":      ["protokol", "protocol"],
    "Delegate":      ["delıget", "delegate"],
    "Config":        ["konfig", "config", "yapılandırma"],
    "Logger":        ["logır", "logger"],
    "Error":         ["eror", "hata", "error"],
    "Exception":     ["ekzepşon", "exception", "hata"],
}

# ---------------------------------------------------------------------------
# Layer 1 — Common domain words (English → Turkish phonetic variants)
# Words that appear as prefixes/middle parts in identifiers.
# ---------------------------------------------------------------------------

COMMON_DOMAINS: dict[str, list[str]] = {
    # Turkish → English bridging (Türk dev Türkçe söyler)
    "User":          ["kullanıcı", "yuzır", "yuser"],
    "Order":         ["sipariş", "order"],
    "Payment":       ["ödeme", "peyment", "payment"],
    "Product":       ["ürün", "prodakt", "product"],
    "Cart":          ["sepet", "kart", "cart"],
    "Profile":       ["profil", "proyfil"],
    "Auth":          ["out", "ot", "aut", "yetki", "kimlik"],
    "Home":          ["anasayfa", "home", "houm"],
    "Detail":        ["detay", "diteyl", "detail"],
    "List":          ["liste", "list", "liyst"],
    "Search":        ["arama", "sörc", "search"],
    "Settings":      ["ayarlar", "settings"],
    "Notification":  ["bildirim", "notifikasyon"],
    "Image":         ["resim", "imıc", "görsel"],
    "Upload":        ["yükleme", "upload", "apload"],
    "Download":      ["indirme", "download", "daunload"],
    "Network":       ["ağ", "network", "netwerk"],
    "Local":         ["yerel", "local", "lokal"],
    "Remote":        ["uzak", "remote", "rimot"],
    "Cache":         ["önbellek", "keş", "cache"],
    "Database":      ["veritabanı", "database"],
    "Analytics":     ["analitik", "analytics"],
    "Crash":         ["çökme", "kreş", "crash"],
    "Log":           ["log", "kayıt"],
    "Push":          ["puş", "push", "itme"],
    "Deep":          ["dip", "deep", "derin"],
    "Base":          ["beys", "base", "temel"],
    "Abstract":      ["soyut", "abstrekt", "abstract"],
    "Main":          ["ana", "meyn", "main"],
    "App":           ["uygulama", "ep", "app"],
    "Root":          ["kök", "rut", "root"],
    "Bottom":        ["alt", "botom", "bottom"],
    "Top":           ["üst", "top"],
    "Navigation":    ["navigasyon", "navigation", "yönlendirme"],
    "Tab":           ["sekme", "teb", "tab"],
}

# ---------------------------------------------------------------------------
# Core: split PascalCase → parts
# ---------------------------------------------------------------------------

def split_pascal(name: str) -> list[str]:
    """PascalCase / camelCase → word list.
    UserService → ['User', 'Service']
    """
    parts = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    parts = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', parts)
    return [p for p in parts.split() if p]


def _variants_for_word(word: str) -> list[str]:
    """Return all known variants for a single word (suffix + domain lookup)."""
    variants: list[str] = [word.lower()]  # always include lowercase original

    if word in UNIVERSAL_SUFFIXES:
        variants.extend(UNIVERSAL_SUFFIXES[word])

    if word in COMMON_DOMAINS:
        variants.extend(COMMON_DOMAINS[word])

    return list(dict.fromkeys(variants))  # deduplicate, preserve order


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_triggers(symbol_name: str) -> list[str]:
    """Generate all trigger phrases for a PascalCase symbol name.

    UserService → [
        "user service",
        "user servis",
        "kullanıcı servis",
        "yuzır servis",
        "user out",          ← "out" is a variant of "Service" (auth→out Whisper error)
        ...
    ]

    Returns deduplicated list, shortest first.
    """
    parts = split_pascal(symbol_name)
    if not parts:
        return []

    # Build variant list per part
    part_variants: list[list[str]] = [_variants_for_word(p) for p in parts]

    # Cartesian product — but cap combinations to avoid explosion
    triggers: list[str] = []
    _cartesian(part_variants, [], triggers, max_results=60)

    # Deduplicate, sort by length (shorter = more likely to match speech)
    seen: set[str] = set()
    result: list[str] = []
    for t in sorted(triggers, key=len):
        if t not in seen and len(t) >= 3:
            seen.add(t)
            result.append(t)

    return result


def _cartesian(
    part_variants: list[list[str]],
    current: list[str],
    results: list[str],
    max_results: int,
) -> None:
    """Recursive cartesian product with result cap."""
    if len(results) >= max_results:
        return
    if not part_variants:
        results.append(" ".join(current))
        return
    for variant in part_variants[0]:
        _cartesian(part_variants[1:], current + [variant], results, max_results)
