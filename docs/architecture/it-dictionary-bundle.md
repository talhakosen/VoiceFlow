# IT Dictionary Bundle — Mimari ve Tasarım

## Genel Bakış

VoiceFlow'un transkripsiyon pipeline'ında Whisper → LLM arasına oturan
fonetik düzeltme katmanı. Türkçe aksanlı IT terimleri konuşmada fonetik
olarak söylendiğinde (ör. "databez", "küberneteste", "invayrınmınt"),
doğru İngilizce karşılığına ("database", "Kubernetes", "environment")
dönüştürür.

```
Whisper ASR → [Dictionary Bundle] → Snippets → LLM Correction
```

---

## Problem

Türk geliştiriciler IT terimlerini Türkçe fonetikle söyler:

| Söylenen | Anlaşılan | Whisper çıktısı |
|---|---|---|
| "databezde" | database'de | "databezde" (yanlış) |
| "küberneteste" | Kubernetes'te | "cube net este" (yanlış) |
| "invayrınmınt" | environment | "invayrınmınt" (yanlış) |
| "arketçiler" | architecture'lar | "arketçiler" (yanlış) |
| "peylod" | payload | "peylod" (yanlış) |

LLM bu hataları düzeltebilir ama maliyetli ve yavaş. Dictionary katmanı
bunu **regex/trie ile milisaniyeler içinde** halleder.

---

## Türkçe Fonetik Dönüşüm Kuralları

Sistematik olarak keşfedilen örüntüler:

| Kural | Örnek |
|---|---|
| `w` → `v` | workflow → "vorkflou", workload → "vorkload" |
| `-ure` sonu → `-ır/-er` | architecture → "arketçır", infrastructure → "infırstrakşır" |
| `-ment` sonu → `-mınt/-ment` | environment → "invayrınmınt" |
| `-tion` → `-şın/-sın` | exception → "eksepşın" |
| `-ity` → `-ıti` | scalability → "skeylebılıti" |
| `-th` → düşer/`t/d` | threshold → "treşould" |
| İng. `ay` sesi → `ey` | payload → "peylod", array → "ırey" |
| Kelime sonu `-er/-or` → `-ır` | container → "konteynır" |
| Kısaltmalar harf harf | kubectl → "kübekıtel", RBAC → "ar bey si" |
| Türkçeleştirme | hallucination → "halüsinasyon" |

---

## Bundle Mimarisi

### Dosya Yapısı

```
ml/dictionary/
├── generate_it_bundle.py   # Generator script — BASE_TERMS + suffix expansion
└── it_bundle_full.json     # Üretilen bundle (70K+ entry, git'e commit edilmez)
```

### Generator (`generate_it_bundle.py`)

İki bileşenden oluşur:

**1. BASE_TERMS** — `(türkçe_telaffuz, doğru_terim)` çiftleri (~1.660 terim)

```python
BASE_TERMS = [
    ("databez", "database"),
    ("invayrınmınt", "environment"),
    ("infırstrakçır", "infrastructure"),
    ("arketçır", "architecture"),
    ...
]
```

**2. SUFFIXES** — Türkçe çekim ekleri (42 ek)

```python
SUFFIXES = [
    ("de", "'de"),   # databezde → database'de
    ("den", "'den"), # databezden → database'den
    ("e", "'e"),     # databeze → database'e
    ("ler", "'ler"), # databezler → database'ler
    ...
]
```

Generator her BASE_TERM × SUFFIX kombinasyonunu üretir:

```
databez    → database
databeze   → database'e
databezde  → database'de
databezden → database'den
databezler → database'ler
databezlerden → database'lerden
... (43 varyant per terim)
```

**Çıktı:** ~70.000 entry, tüm Türkçe çekim halleriyle.

### Bundle Scope

DB'de `scope='bundle'` olarak saklanır:

| Scope | UI'da görünür | Pipeline'da aktif |
|---|---|---|
| `personal` | ✅ | ✅ |
| `team` | ✅ | ✅ |
| `bundle` | ❌ | ✅ |

Kullanıcı Sözlük ekranında bundle entry'lerini görmez; arka planda sessizce çalışır.

---

## Algoritma: Aho-Corasick

### Neden Aho-Corasick?

70.000 entry için naif regex döngüsü kabul edilemez:

| Yaklaşım | Karmaşıklık | 70K entry, 4 metin, 100 tekrar |
|---|---|---|
| Regex loop (eski) | O(N × \|metin\|) | ~3.300ms/metin |
| Aho-Corasick (yeni) | O(\|metin\|) | ~0.012ms/metin |
| **Hız farkı** | | **~275.000×** |

### Nasıl Çalışır

1. Tüm trigger'lar bir **trie** (prefix ağacı) üzerine yerleştirilir.
2. Aho-Corasick algoritması trie'ya **failure link**'ler ekler.
3. Metin **tek seferde** soldan sağa taranır — tüm eşleşmeler aynı anda bulunur.
4. Çakışan eşleşmeler: soldan sağa, **en uzun eşleşme** önce alınır.
5. **2 pass** yapılır: ikinci pass ilk pass'ın genişlettiği terimleri yakalar.

### Servis Seviyesi Cache

`RecordingService.__init__` içinde automaton tek instance olarak tutulur:

```python
self._dict_automaton = None
self._dict_entry_count = 0
```

`stop()` çağrısında:

```python
if len(entries) != self._dict_entry_count:
    self._dict_automaton = _build_automaton(entries)  # rebuild (36ms)
    self._dict_entry_count = len(entries)

result.text = _apply_aho_corasick(result.text, self._dict_automaton)  # 0.012ms
result.text = _apply_aho_corasick(result.text, self._dict_automaton)
```

Automaton **sadece dictionary değiştiğinde** rebuild edilir (bundle yükle/sil,
kullanıcı entry ekle/çıkar). Her kayıt için aynı automaton yeniden kullanılır.

---

## API

### Bundle Yükle

```bash
POST /api/dictionary/bundle
Content-Type: application/json

{"bundle_path": "/absolute/path/to/it_bundle_full.json"}
```

Mevcut bundle entry'leri temizler, yenilerini yükler.

```json
{"status": "loaded", "count": 70606}
```

### Bundle Temizle

```bash
DELETE /api/dictionary/bundle
```

---

## Bundle Güncelleme Akışı

1. `ml/dictionary/generate_it_bundle.py` içindeki `BASE_TERMS`'e yeni terimler ekle
2. Generator'ı çalıştır: `python3 ml/dictionary/generate_it_bundle.py`
3. Backend'e yükle:
   ```bash
   curl -X POST http://127.0.0.1:PORT/api/dictionary/bundle \
     -H "Content-Type: application/json" \
     -d '{"bundle_path": "/abs/path/to/it_bundle_full.json"}'
   ```
4. Automaton otomatik rebuild edilir (ilk kayıtta).

---

## Kapsanan IT Kategorileri (v1.0)

| Kategori | Terim Sayısı |
|---|---|
| Genel donanım / sistem | ~30 |
| Programlama dilleri | ~50 |
| Backend / API | ~80 |
| Frontend / Web | ~70 |
| Veritabanı | ~60 |
| Cloud / Altyapı | ~70 |
| DevOps / SRE | ~80 |
| Kubernetes / Container | ~60 |
| Güvenlik | ~70 |
| Ağ / Networking | ~40 |
| ML / AI | ~100 |
| Veri Mühendisliği | ~60 |
| Observability / Monitoring | ~50 |
| Tooling / IDE | ~60 |
| Mobile | ~30 |
| Mimari / Design Patterns | ~50 |
| Test / Kalite | ~40 |
| Agile / PM | ~30 |
| Türkiye Özel (KVKK, BTK...) | ~10 |
| **Kritik Tier-1 fonetikler** | ~60 |
| **Toplam base terim** | **~1.660** |
| **Suffix varyantlarıyla** | **~70.000** |

---

## Kritik Öğrenimler

**"arketçiler" vakası** — Whisper "architecture'lar" için "arketçiler" yazdı.
Bunun gibi `-ure` → `-çır/er` dönüşümü sistematik; tüm `*ture/*ure` sonlu
İngilizce terimlerin Türkçe fonetikleri eklenmeli.

**Fonetik önceliği** — Aynı pozisyonda birden fazla eşleşme olunca en uzun
trigger kazanır. Bu yüzden "databezlerden" doğru `"database'lerden"` üretir,
"databez" + "lerden" olarak bölünmez.

**False positive riski** — `set`, `map`, `type`, `list` gibi çok kısa İngilizce
kelimeler trigger olarak eklenmemeli; Türkçe metinde yanlış tetikler.
Sadece fonetik varyantları ekle (`lıst` → `list` güvenli, `list` → `list` değil).

**Suffix apostrofu** — Türkçe yazım kuralı: yabancı kelimeye ek gelince
apostrof zorunlu (`database'de`, `Kubernetes'te`). SUFFIXES listesinde
`"de"` → `"'de"` formatı bunu otomatik sağlar.
