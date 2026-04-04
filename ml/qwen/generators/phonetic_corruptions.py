"""
phonetic_corruptions.py — Kural tabanlı fonetik bozukluk engine.

Whisper'in Turk developer konusmasinda yaptigi tipik hatalari simule eder:
- Teknik terimlerin fonetik yanlis yazimi (160+ terim)
- Noktalama/buyuk harf bozulmasi
- Turkce ek bozukluklari (apostrof silme)
- Turkce karakter → ASCII fallback
- Kelime siniri hatalari
- Filler enjeksiyonu (persona bazli)

Zero API calls. Zero external dependencies.

Usage:
    from phonetic_corruptions import full_corrupt
    corrupted = full_corrupt("Deployment pipeline'i kontrol et.", persona_style="senior")
"""

import random
import re
from typing import Literal

# ─────────────────────────────────────────────────────────────────────────────
# 1. PHONETIC VARIANTS — 160+ teknik terim, her birinin 2-3 Turk fonetik varyanti
# ─────────────────────────────────────────────────────────────────────────────

PHONETIC_VARIANTS: dict[str, list[str]] = {
    # ── Backend / Genel ──────────────────────────────────────────────────────
    "deployment": ["depiloyment", "diployment", "depoloyment"],
    "deploy": ["diploy", "depiloy", "dıploy"],
    "container": ["konteyner", "konteyinir", "kontaynir"],
    "endpoint": ["endpoynt", "end poynt", "endpoyint"],
    "middleware": ["middleweyr", "midilver", "midilveyr"],
    "authentication": ["otentikeysin", "otantikeysin", "otentikasyon"],
    "authorization": ["otorizasyon", "otorizeysin", "otorayzeysin"],
    "repository": ["repozitori", "repozetori", "repazitori"],
    "microservice": ["mikro servis", "maykroservis", "maykreservis"],
    "microservices": ["mikro servisler", "maykroservisler", "maykreservisler"],
    "database": ["deytebes", "databeys", "deytabeys"],
    "migration": ["maygresyon", "migreysin", "maygreysin"],
    "transaction": ["tranzeksin", "transeksin", "tranzaksiyon"],
    "callback": ["kolbek", "kalbek", "kolbak"],
    "refactor": ["rifaktir", "refaktor", "rifaktor"],
    "scalable": ["skeyilibil", "skeylebil", "iskeylebil"],
    "scaling": ["skeyling", "skeylink", "iskeylink"],
    "caching": ["kesing", "kesink", "kasink"],
    "rollback": ["rolbek", "rolbak", "rollbak"],
    "pipeline": ["payplayn", "payp layn", "paypılayn"],
    "load balancer": ["lod belensir", "lod balansir", "lodbalensir"],
    "API": ["eypiai", "apiay", "eypi ay"],
    "REST": ["rest", "rist", "rist"],
    "GraphQL": ["grafkuel", "girafkul", "grafkuil"],
    "ORM": ["oerem", "orm", "oarem"],
    "queue": ["kyu", "ku", "kyu"],
    "server": ["sorvir", "servir", "sorvir"],
    "cluster": ["klastir", "klaster", "kilastir"],
    "instance": ["instins", "instens", "instans"],
    "configuration": ["konfigurasyon", "konfigureysin", "konfigurasyın"],
    "infrastructure": ["infrastruktur", "infirastruktsir", "infirastrukcir"],
    "environment": ["envayirinmint", "envayirment", "envayirmint"],
    "query": ["kueri", "kuri", "kuiri"],
    "schema": ["sema", "skima", "sima"],
    "payload": ["peylod", "paylod", "peyloud"],
    "response": ["respons", "rispons", "risponz"],
    "request": ["rikuest", "rikuist", "rekuest"],
    "header": ["hedir", "heder", "hedor"],
    "token": ["tokin", "tokken", "tokin"],
    "session": ["sesin", "sessin", "sesyin"],
    "cache": ["kes", "kas", "keys"],
    "Redis": ["redis", "rediz", "ridis"],
    "WebSocket": ["vebsoket", "vebsaket", "websokıt"],
    "timeout": ["taymaut", "taym aut", "tayimaut"],
    "latency": ["leytensi", "latınsi", "leytınsi"],
    "throughput": ["tiruput", "truput", "tiruput"],
    "bandwidth": ["bendvit", "bandvit", "bendvitt"],
    "serialize": ["siriyalayz", "seriyalayz", "siriyalayz"],
    "deserialize": ["disiriyalayz", "diseriyalayz", "disiriyalayz"],
    "proxy": ["proksi", "proksi", "praksi"],
    "SSL": ["es es el", "eseşel", "ssl"],
    "certificate": ["sertifika", "sertifikeyt", "sertifikıt"],
    "daemon": ["dimon", "deymin", "daymon"],

    # ── DevOps ───────────────────────────────────────────────────────────────
    "Kubernetes": ["kubernetis", "cubernetes", "kubernitis"],
    "Docker": ["dokir", "doker", "dakir"],
    "Docker Compose": ["dokir kompoz", "doker compoz", "dakir kompoz"],
    "Helm": ["helm", "helim", "heylm"],
    "Terraform": ["teraform", "terrafom", "tereform"],
    "Ansible": ["ensibil", "ansibil", "ansıbıl"],
    "Jenkins": ["cenkins", "jenkinz", "cenkıns"],
    "Prometheus": ["prometeyus", "promiteus", "prometius"],
    "Grafana": ["grafana", "girafana"],
    "ingress": ["ingires", "ingres", "ingris"],
    "namespace": ["neymspeys", "naymspeys", "neymsipeys"],
    "configmap": ["konfig mep", "konfigmap", "konfıgmap"],
    "volume": ["volyum", "volyum", "volyim"],
    "secret": ["sikret", "sekret", "sikrit"],
    "pod": ["pod", "pad", "poad"],
    "node": ["nod", "noud", "noud"],
    "registry": ["recistri", "recistri", "recistri"],
    "orchestration": ["orkestrasyon", "orkestreysin", "orkistreysin"],
    "provisioning": ["provizyoning", "provijining", "proviziyoning"],
    "nginx": ["enginiks", "enciniks", "niginks"],
    "serverless": ["sorverles", "servirles", "sorvırles"],
    "cron": ["kiron", "kron", "kiron"],
    "monitoring": ["monitorink", "monitorink", "monitöring"],

    # ── Flutter / Mobile ─────────────────────────────────────────────────────
    "widget": ["vicet", "vicet", "viget"],
    "StatefulWidget": ["steytful vicet", "statefu widget", "isteytful vicet"],
    "StatelessWidget": ["steytles vicet", "stateles widget", "isteytles vicet"],
    "Provider": ["provaydr", "provaydir", "provaydır"],
    "Riverpod": ["rivırpod", "riverpod", "rivırpad"],
    "BuildContext": ["bild kontekst", "bild context", "bildkontekst"],
    "setState": ["set steyt", "setsteyt", "set isteyt"],
    "Navigator": ["nevıgeytir", "navigator", "nevigeytir"],
    "scaffold": ["iskefold", "skaffold", "iskafold"],
    "ListView": ["list vyu", "listvu", "listvyu"],
    "Flutter": ["flatir", "flater", "flatır"],
    "Dart": ["dart", "dart"],
    "pubspec": ["pabspek", "pubspek", "pabispek"],
    "hot reload": ["hot rilod", "hat rilod", "hat rilöd"],
    "StreamBuilder": ["strim bildır", "stiriym bilder", "strim bilder"],
    "FutureBuilder": ["fyucir bilder", "fucır bilder", "fyucır bildır"],
    "BLoC": ["bilok", "blak", "bilak"],
    "GetX": ["getiks", "geteks", "gettiks"],

    # ── Frontend / React ─────────────────────────────────────────────────────
    "component": ["komponent", "componenti", "kompanent"],
    "hook": ["huk", "hok", "hök"],
    "useEffect": ["yusifekt", "yuz ifekt", "yuzifekt"],
    "useState": ["yussteyt", "yuz steyt", "yuz isteyt"],
    "useMemo": ["yusmemo", "yuz memo", "yusımemo"],
    "useCallback": ["yuskolbek", "yuz kolbek", "yusıkolbek"],
    "useRef": ["yusref", "yuz ref", "yusıref"],
    "React": ["riyekt", "riekt", "riyakt"],
    "Next.js": ["nekst ceys", "nekstceys", "nekist ceys"],
    "TypeScript": ["tayp skript", "taypskript", "tayıp skript"],
    "props": ["praps", "props", "propslar"],
    "Redux": ["ridaks", "ridux", "ridöks"],
    "render": ["rendir", "render", "rindır"],
    "virtual DOM": ["vorcuil dom", "virtual dom", "vorcıl dam"],
    "SSR": ["es es ar", "esesar", "ss ar"],
    "Tailwind": ["teylvind", "teylvind", "taylvind"],
    "responsive": ["rispansiv", "responsiv", "risponsif"],
    "breakpoint": ["breykpoynt", "brekpoynt", "breyikpoynt"],
    "memoize": ["mimoyız", "memoyız", "memoyiz"],
    "dependency": ["dipendınsi", "dependensi", "dıpındınsi"],
    "hydration": ["haydreysin", "hidreysin", "hayıdreysin"],
    "CSS": ["si es es", "sises", "css"],
    "flexbox": ["fleksboks", "fleksbaks", "fleksiboks"],
    "grid": ["grid", "girid", "girid"],
    "layout": ["leyaut", "leyyaut", "leyavut"],
    "navigation": ["nevigeysin", "nevigasyon", "neyvigesyon"],
    "routing": ["ravutink", "ravuting", "ruting"],
    "context": ["kontekst", "kantekst", "konteks"],
    "provider": ["provaydir", "providir", "provaydir"],
    "lifecycle": ["layfsaykil", "laifsikil", "layfsikıl"],

    # ── Git ───────────────────────────────────────────────────────────────────
    "commit": ["komit", "kommit", "komıt"],
    "branch": ["brans", "biranc", "bıranç"],
    "merge": ["morc", "merc", "mörc"],
    "pull request": ["pul rikuest", "pul rekuest", "pulrikuist"],
    "push": ["pus", "puş", "puuş"],
    "conflict": ["konfilikt", "konflikt", "konflıkt"],
    "rebase": ["ribeys", "ribeys", "ribas"],
    "stash": ["stes", "istes", "stas"],
    "cherry-pick": ["ceri pik", "cherri pik", "çeri pık"],
    "checkout": ["cekavut", "cekovt", "çekaut"],
    "clone": ["kilon", "kloon", "kilon"],
    "fork": ["fork", "fork", "foruk"],
    "tag": ["tek", "tag", "teğ"],
    "release": ["riliz", "rilis", "riliyz"],
    "diff": ["dif", "diff", "dıf"],

    # ── Testing ──────────────────────────────────────────────────────────────
    "unit test": ["yunit test", "unit tist", "yunit test"],
    "integration test": ["integrasyon test", "intigresyon test", "integireysin test"],
    "mock": ["mok", "maak", "mök"],
    "stub": ["stab", "istap", "stöb"],
    "assertion": ["asorsin", "asırsin", "asersin"],
    "coverage": ["kavric", "kavrıc", "kaveric"],
    "snapshot": ["snepsat", "isnepsat", "snepsot"],
    "regression": ["rigresyon", "rigresin", "regresyın"],
    "end-to-end": ["end tu end", "endtuyend", "end to end"],
    "fixture": ["fikstir", "fiksçir", "fikscir"],
    "benchmark": ["bencmark", "bencmaark", "bençmark"],
    "test suite": ["test süt", "test sut", "test suyt"],

    # ── Genel IT / Programlama ───────────────────────────────────────────────
    "function": ["fanksin", "fonksiyon", "fanksiyon"],
    "variable": ["veriybil", "variyebil", "veriyabıl"],
    "array": ["erey", "arey", "ırey"],
    "object": ["obcekt", "objekt", "abcekt"],
    "loop": ["lup", "lup", "lüp"],
    "console": ["konsol", "konsoul"],
    "package": ["peykic", "paket", "pekıc"],
    "import": ["import", "impört"],
    "export": ["eksport", "eksport"],
    "async": ["eysink", "asink", "eysingk"],
    "await": ["eveyt", "aveyit", "iveyt"],
    "interface": ["interfeys", "intırfeys", "intorfeys"],
    "abstract": ["ebstrekt", "abstrakt", "abstırakt"],
    "framework": ["freymvork", "freymwork", "freymvirk"],
    "library": ["laybirri", "laybıri", "laybreri"],
    "debug": ["dibag", "debag", "dıbag"],
    "debugging": ["dibaging", "dibagink", "dıbagink"],
    "feature": ["ficir", "ficer", "fiiçır"],
    "production": ["prodaksin", "prodaksiyon", "prodüksin"],
    "staging": ["steycing", "steycink", "isteycing"],
    "performance": ["porformans", "performens", "porformens"],
    "optimize": ["optimayız", "optimayz", "optimız"],
    "implement": ["impliment", "implıment", "implement"],
    "architecture": ["arkitekcir", "arkitektşır", "arkitecır"],
    "algorithm": ["algoritma", "algorıtma", "algıritma"],
    "exception": ["eksepsin", "eksepsn", "iksepsin"],
    "null": ["nal", "nul", "naal"],
    "boolean": ["buliin", "buliyen", "booliin"],
    "string": ["string", "istring", "strink"],
    "integer": ["inticir", "intıcır", "intecir"],
    "class": ["kilas", "kleas", "klas"],
    "method": ["metid", "metod", "metıt"],
    "socket": ["soket", "sakit", "sakıt"],
    "protocol": ["protokol", "protokal", "protokol"],
    "binary": ["baynıri", "bayneri", "binıri"],
    "encryption": ["enkripsıyon", "inkiripsiyon", "enkripsin"],
    "hashing": ["hesing", "hesink", "hasing"],
    "JSON": ["ceyson", "jason", "jeyson"],
    "YAML": ["yemel", "yaml", "yemıl"],
    "XML": ["eksml", "iksimel", "eksıml"],
    "HTML": ["eyctiml", "html", "eyçtiemil"],
    "HTTP": ["eyctitipi", "http", "eyctitipi"],
    "SSH": ["eseseyc", "ssh", "esieseyc"],
    "DNS": ["dienes", "dns", "diines"],
    "URL": ["yüarel", "url", "yuarel"],
    "SDK": ["esdikey", "sdk", "esdikay"],
    "IDE": ["aydii", "ide", "aydıi"],
    "CLI": ["sielay", "seelay", "cli"],
    "thread": ["tired", "tred", "tıret"],
    "process": ["proses", "prosis", "prauses"],
    "runtime": ["rantaym", "runtaym", "rantayim"],
    "compiler": ["kompaylir", "kompaylir", "kompiler"],
    "version": ["versiyon", "vorsiyon", "versiyon"],
    "update": ["apdeyt", "abdıyt", "apdeyit"],
    "upgrade": ["apgreyd", "apgireyd", "apgireid"],

    # ── PM / Business ────────────────────────────────────────────────────────
    "sprint": ["sprint", "sipırint", "ispırint"],
    "backlog": ["beklog", "baklog", "beklög"],
    "roadmap": ["rodmep", "rodmap", "roudmep"],
    "milestone": ["maylston", "maylstoun", "mayliston"],
    "deadline": ["dedlayn", "dedlayin", "dadlayn"],
    "stakeholder": ["steykholdr", "steykholdır", "steykholdir"],
    "demo": ["demo", "dimo", "dimoo"],
    "retrospective": ["retrospektif", "retraspektiv", "retraspektif"],
    "velocity": ["velositi", "vilositi", "vilosıti"],
    "story point": ["stori poynt", "stori poynt", "istori poynt"],
    "scope": ["skop", "skoup", "iskop"],
    "requirement": ["rikuayrment", "rikuayirment", "rikuayırmınt"],
    "user story": ["yuzir stori", "yuzır stori", "yuzir istori"],
    "acceptance criteria": ["akseptins kiraytiriya", "akseptıns kraytırya"],
    "deliverable": ["diliveribil", "deliveribil", "dılıverıbıl"],
    "blocker": ["blokir", "blaker", "blokır"],
    "priority": ["pirayoriti", "prayoriti", "pirayorıti"],
    "MVP": ["em vi pi", "mvp", "em vi pii"],
    "KPI": ["key pi ay", "kpi", "keypiay"],
    "standup": ["istendap", "stendap", "stendop"],
    "agile": ["ecayl", "ecıyl", "agayl"],
    "scrum": ["skiram", "iskram", "skirom"],
    "kanban": ["kenban", "kanben", "kanbaan"],
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. FILLER KELIMELER — persona bazli sıklık profili
# ─────────────────────────────────────────────────────────────────────────────

FILLERS_LOW = ["yani", "iste", "hani"]
FILLERS_MEDIUM = ["yani", "sey", "iste", "hani", "ee", "aa", "tamam"]
FILLERS_HIGH = [
    "yani", "sey", "iste", "hani", "ee", "aa", "falan", "nasil diyeyim",
    "bi dakika", "him", "simdi", "aslinda", "bir nevi", "dur bi saniye",
    "neyse", "tamam", "ya",
]

_FILLER_MAP = {
    "low": FILLERS_LOW,
    "medium": FILLERS_MEDIUM,
    "high": FILLERS_HIGH,
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. TURKCE EK BOZUKLUK KALIPLARI
# ─────────────────────────────────────────────────────────────────────────────

_SUFFIX_CORRUPTIONS: list[tuple[str, str]] = [
    # Apostrof + ek → birlestirme
    ("'ı ", "ı "), ("'i ", "i "), ("'u ", "u "), ("'ü ", "ü "),
    ("'a ", "a "), ("'e ", "e "),
    ("'da ", "da "), ("'de ", "de "),
    ("'dan ", "dan "), ("'den ", "den "),
    ("'ta ", "ta "), ("'te ", "te "),
    ("'tan ", "tan "), ("'ten ", "ten "),
    ("'la ", "la "), ("'le ", "le "),
    ("'ın ", "ın "), ("'in ", "in "),
    ("'nın ", "nın "), ("'nin ", "nin "),
    ("'ya ", "ya "), ("'ye ", "ye "),
    # Nokta oncesi varyantlari
    ("'ı.", "ı."), ("'i.", "i."), ("'a.", "a."), ("'e.", "e."),
    ("'da.", "da."), ("'de.", "de."), ("'dan.", "dan."), ("'den.", "den."),
    ("'nın.", "nın."), ("'nin.", "nin."), ("'ya.", "ya."), ("'ye.", "ye."),
    # Virgul oncesi
    ("'ı,", "ı,"), ("'i,", "i,"), ("'a,", "a,"), ("'e,", "e,"),
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. TURKCE KARAKTER → ASCII (Whisper diacritics fallback)
# ─────────────────────────────────────────────────────────────────────────────

_TURKISH_DIACRITICS: list[tuple[str, str]] = [
    ("ç", "c"), ("Ç", "C"),
    ("ş", "s"), ("Ş", "S"),
    ("ğ", "g"), ("Ğ", "G"),
    ("ı", "i"), ("İ", "I"),
    ("ö", "o"), ("Ö", "O"),
    ("ü", "u"), ("Ü", "U"),
]

# ─────────────────────────────────────────────────────────────────────────────
# 5. BOZUKLUK FONKSIYONLARI
# ─────────────────────────────────────────────────────────────────────────────


def corrupt_technical_terms(text: str, prob: float = 0.6) -> str:
    """Teknik terimleri fonetik varyantlarla degistir."""
    result = text
    # Uzun terimlerden basla (multi-word terimler once)
    sorted_terms = sorted(PHONETIC_VARIANTS.keys(), key=len, reverse=True)
    for term in sorted_terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        matches = list(pattern.finditer(result))
        for match in reversed(matches):
            if random.random() < prob:
                variant = random.choice(PHONETIC_VARIANTS[term])
                result = result[:match.start()] + variant + result[match.end():]
    return result


def corrupt_punctuation(text: str, prob: float = 0.5) -> str:
    """Noktalama isaretlerini sil veya boz."""
    result = []
    for ch in text:
        if ch in ".,;:!?" and random.random() < prob:
            continue  # drop
        result.append(ch)
    return "".join(result)


def corrupt_capitalization(text: str, prob: float = 0.7) -> str:
    """Cumle basindaki ve ozel adlardaki buyuk harfleri kucult."""
    if not text:
        return text
    result = list(text)
    # Cumle basi
    if result[0].isupper() and random.random() < prob:
        result[0] = result[0].lower()
    # Diger buyuk harfler
    for i in range(1, len(result)):
        if result[i].isupper() and random.random() < prob * 0.4:
            result[i] = result[i].lower()
    return "".join(result)


def corrupt_turkish_chars(text: str, prob: float = 0.4) -> str:
    """Turkce ozel karakterleri ASCII karsiliklariyla degistir."""
    result = []
    for ch in text:
        replaced = False
        for turkish, ascii_eq in _TURKISH_DIACRITICS:
            if ch == turkish and random.random() < prob:
                result.append(ascii_eq)
                replaced = True
                break
        if not replaced:
            result.append(ch)
    return "".join(result)


def corrupt_turkish_suffixes(text: str, prob: float = 0.6) -> str:
    """Turkce apostrof+ek kaliplarini boz (Whisper birlestiriyor)."""
    result = text
    for correct, corrupted in _SUFFIX_CORRUPTIONS:
        if correct in result and random.random() < prob:
            result = result.replace(correct, corrupted, 1)
    return result


def add_fillers(text: str, freq: Literal["low", "medium", "high"] = "medium") -> str:
    """Persona'ya gore filler kelime ekle.

    low: 0-1 filler, medium: 1-3, high: 3-6
    """
    fillers = _FILLER_MAP.get(freq, FILLERS_MEDIUM)
    words = text.split()
    if len(words) < 3:
        return text

    max_possible = max(1, len(words) - 1)

    if freq == "low":
        n = random.randint(0, min(1, max_possible))
    elif freq == "medium":
        n = random.randint(1, min(3, max_possible))
    else:
        n = random.randint(min(3, max_possible), min(6, max_possible))

    if n == 0:
        return text

    # Cumle basina filler
    if random.random() < 0.5:
        words.insert(0, random.choice(fillers))
        n -= 1

    # Geri kalani rastgele pozisyonlara
    for _ in range(n):
        if len(words) > 2:
            pos = random.randint(1, len(words) - 1)
            words.insert(pos, random.choice(fillers))

    return " ".join(words)


def corrupt_word_boundaries(text: str, prob: float = 0.1) -> str:
    """Kelime sinirlarini boz — birlestirme veya ayirma."""
    words = text.split()
    result = []
    i = 0
    while i < len(words):
        if i < len(words) - 1 and random.random() < prob:
            # Iki kelimeyi birlestir
            result.append(words[i] + words[i + 1])
            i += 2
        elif len(words[i]) > 7 and random.random() < prob * 0.5:
            # Uzun kelimeyi ayir
            mid = len(words[i]) // 2
            result.append(words[i][:mid])
            result.append(words[i][mid:])
            i += 1
        else:
            result.append(words[i])
            i += 1
    return " ".join(result)


# ─────────────────────────────────────────────────────────────────────────────
# 6. PERSONA STIL AYARLARI
# ─────────────────────────────────────────────────────────────────────────────

PERSONA_STYLES = {
    "senior": {
        "filler_freq": "low",
        "tech_corrupt_prob": 0.5,
        "punct_corrupt_prob": 0.3,
        "cap_corrupt_prob": 0.5,
        "turkish_char_prob": 0.3,
        "suffix_corrupt_prob": 0.4,
        "word_boundary_prob": 0.05,
    },
    "mid": {
        "filler_freq": "medium",
        "tech_corrupt_prob": 0.6,
        "punct_corrupt_prob": 0.5,
        "cap_corrupt_prob": 0.6,
        "turkish_char_prob": 0.4,
        "suffix_corrupt_prob": 0.5,
        "word_boundary_prob": 0.08,
    },
    "junior": {
        "filler_freq": "high",
        "tech_corrupt_prob": 0.8,
        "punct_corrupt_prob": 0.6,
        "cap_corrupt_prob": 0.7,
        "turkish_char_prob": 0.5,
        "suffix_corrupt_prob": 0.6,
        "word_boundary_prob": 0.12,
    },
    "pm": {
        "filler_freq": "medium",
        "tech_corrupt_prob": 0.4,
        "punct_corrupt_prob": 0.4,
        "cap_corrupt_prob": 0.5,
        "turkish_char_prob": 0.35,
        "suffix_corrupt_prob": 0.5,
        "word_boundary_prob": 0.06,
    },
}


def full_corrupt(text: str, persona_style: str = "mid") -> str:
    """Tum bozukluk katmanlarini uygula — Whisper output simulasyonu.

    Args:
        text: Temiz, dogru formatli Turkce metin.
        persona_style: "senior", "mid", "junior", "pm" stillerinden biri.

    Returns:
        Whisper'in ham ciktisini simule eden bozuk metin.
    """
    style = PERSONA_STYLES.get(persona_style, PERSONA_STYLES["mid"])

    # Siralama onemli: teknik terimler → karakterler → yapisal bozukluklar
    result = corrupt_technical_terms(text, prob=style["tech_corrupt_prob"])
    result = corrupt_turkish_chars(result, prob=style["turkish_char_prob"])
    result = corrupt_turkish_suffixes(result, prob=style["suffix_corrupt_prob"])
    result = corrupt_punctuation(result, prob=style["punct_corrupt_prob"])
    result = corrupt_capitalization(result, prob=style["cap_corrupt_prob"])
    result = corrupt_word_boundaries(result, prob=style["word_boundary_prob"])
    result = add_fillers(result, freq=style["filler_freq"])

    # Coklu bosluk temizle
    result = " ".join(result.split())
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Quick test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    random.seed(42)
    test_sentences = [
        "Deployment pipeline'ı kontrol et, Kubernetes cluster'da bir sorun var.",
        "Bu component'in useEffect hook'unda memory leak var.",
        "Repository'yi klonlayıp branch açın, pull request'i ben review edeceğim.",
        "Authentication middleware'de timeout hatası alıyoruz, cache'i temizle.",
        "Sprint retrospective'de backend deployment süresini konuşalım.",
    ]

    for sent in test_sentences:
        print(f"CLEAN:   {sent}")
        for style_name in ["senior", "mid", "junior", "pm"]:
            print(f"  [{style_name:>6}] {full_corrupt(sent, style_name)}")
        print()

    print(f"\nToplam fonetik terim sayisi: {len(PHONETIC_VARIANTS)}")
