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
    from pathlib import Path as P

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

    from ..db.storage import bulk_add_smart_entries
    added = await bulk_add_smart_entries(user_id=user_id, tenant_id="default", pairs=unique_pairs)
    logger.info("Smart dictionary: added %d new entries for %s", added, user_id)
    return added
