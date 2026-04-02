"""persona_terms.py — IT persona vocabulary + Turkish pronunciation variants.

8 persona, her biri teknik terim listesi + nasıl yanlış duyulduğuna dair varyantlar.
sentence_generator.py bu veriyi kullanarak Opus'a cümle ürettirir.
"""

from dataclasses import dataclass, field


@dataclass
class Persona:
    name: str
    description: str
    # (correct_term, [turkish_pronunciation_variants])
    terms: list[tuple[str, list[str]]]


PERSONAS: list[Persona] = [

    Persona(
        name="backend_dev",
        description="Python/Java/Go backend geliştirici. Mikroservis, API, veritabanı konuşur.",
        terms=[
            ("Docker",           ["doker", "dökır", "dokır"]),
            ("Kubernetes",       ["kübernetis", "kubernetis", "kubernitis", "k8s"]),
            ("microservice",     ["mikroservis", "mikro servis"]),
            ("endpoint",         ["end point", "en point"]),
            ("middleware",       ["midılveyır", "midlvare"]),
            ("PostgreSQL",       ["postgres", "post gre es kuel", "postgresekuel"]),
            ("Redis",            ["redis", "rediss"]),
            ("Kafka",            ["kafka"]),
            ("RabbitMQ",         ["rabbit em kyu", "rabitmq", "rabbit em queue"]),
            ("JWT",              ["jay double-u ti", "ce double-u ti", "jeydubbti"]),
            ("OAuth",            ["o oth", "o ayıth", "ovath"]),
            ("CRUD",             ["crud", "si ar yu di"]),
            ("REST",             ["rest api", "resst"]),
            ("GraphQL",          ["grafikul", "graf kul", "grafküel", "grap kuel"]),
            ("gRPC",             ["g rpc", "gerpc", "ji ar pi si"]),
            ("FastAPI",          ["fast api", "fast eypiai"]),
            ("SQLAlchemy",       ["es kuel alkemi", "sql alkemi"]),
            ("Pydantic",         ["pydantik", "paydantik"]),
            ("uvicorn",          ["yuvikorn", "uvikorn"]),
            ("Celery",           ["seleri", "selery"]),
            ("load balancer",    ["load balancer", "lod balenser"]),
            ("rate limiting",    ["reyt limiting"]),
            ("idempotent",       ["aydempotent", "idempotent"]),
            ("N+1 problem",      ["n artı bir problemi"]),
            ("index",            ["indeks"]),
            ("migration",        ["migrasyon", "migreyşın"]),
        ],
    ),

    Persona(
        name="frontend_dev",
        description="React/Vue/Angular frontend geliştirici. Component, state, UI konuşur.",
        terms=[
            ("React",            ["riyakt", "riekt"]),
            ("TypeScript",       ["tayp skript", "tayp eskript", "taypskript"]),
            ("JavaScript",       ["cava skript", "javascript"]),
            ("Webpack",          ["vebpak", "uebpak", "webpek"]),
            ("Vite",             ["vayt", "vit"]),
            ("npm",              ["en pi em", "en pem"]),
            ("yarn",             ["yarn"]),
            ("Redux",            ["ridaks", "rıdaks"]),
            ("Zustand",          ["zustand", "züstand"]),
            ("Tailwind",         ["teylwind", "tailwind"]),
            ("component",        ["komponent"]),
            ("hook",             ["huk"]),
            ("props",            ["praps", "props"]),
            ("state",            ["steyt"]),
            ("useEffect",        ["yuz efekt", "use efekt"]),
            ("useState",         ["yuz steyt", "use steyt"]),
            ("SSR",              ["es es ar", "server side rendering"]),
            ("CSR",              ["si es ar"]),
            ("hydration",        ["haydreysın", "hidrasyon"]),
            ("lazy loading",     ["leyzi loading"]),
            ("bundle",           ["bandıl"]),
            ("tree shaking",     ["tri şeyking"]),
            ("CSS",              ["si es es"]),
            ("responsive",       ["respansiv"]),
            ("breakpoint",       ["breykpoint"]),
        ],
    ),

    Persona(
        name="flutter_dev",
        description="Flutter/Dart mobil geliştirici.",
        terms=[
            ("Flutter",          ["flatter", "flötür", "fılatter", "fladır"]),
            ("Dart",             ["dart"]),
            ("widget",           ["vijet", "widget"]),
            ("setState",         ["set steyt", "setsteyt"]),
            ("BLoC",             ["bilok", "bi el o si", "blok"]),
            ("Provider",         ["provider", "provayıder"]),
            ("Riverpod",         ["riverpod", "rivırpod"]),
            ("pubspec",          ["pabspek", "pub spek"]),
            ("Navigator",        ["navigator"]),
            ("BuildContext",     ["bild kontext", "build kontext"]),
            ("StatefulWidget",   ["steyful vijet"]),
            ("StatelessWidget",  ["steytles vijet"]),
            ("FutureBuilder",    ["fıyçır bilder"]),
            ("StreamBuilder",    ["strim bilder"]),
            ("GetX",             ["get eks"]),
            ("dio",              ["di o", "diyou"]),
            ("Hive",             ["hayv"]),
            ("sqflite",          ["es kyu flayt", "sq flayt"]),
            ("flavors",          ["fleyvorz", "flavor"]),
            ("platform channel", ["platform çenel"]),
        ],
    ),

    Persona(
        name="dotnet_dev",
        description=".NET/C# geliştirici. Enterprise, Azure, EF Core konuşur.",
        terms=[
            ("C#",               ["si sharp", "si şarp"]),
            ("ASP.NET",          ["asp net", "a es pi net"]),
            ("Entity Framework", ["entity framework", "entity freymvork"]),
            ("LINQ",             ["link", "linq"]),
            ("NuGet",            ["nüget", "nyu get"]),
            ("Blazor",           ["bleyzor"]),
            ("SignalR",          ["sinyal ar", "signal ar"]),
            ("dependency injection", ["dipendency injection", "bağımlılık enjeksiyonu"]),
            ("IEnumerable",      ["ay enumerabl", "i enumerabl"]),
            ("async await",      ["eysink evveyt", "async avvait"]),
            ("middleware pipeline", ["midlvare pipeline"]),
            ("Swagger",          ["swagger"]),
            ("EF Core",          ["ef kor", "entity framework kor"]),
            ("DbContext",        ["di bi kontext"]),
            ("appsettings",      ["app settings"]),
            ("Azure",            ["ejur", "ayjur"]),
            ("Minimal API",      ["minimal api"]),
        ],
    ),

    Persona(
        name="mobile_dev",
        description="iOS/Android native geliştirici.",
        terms=[
            ("Swift",            ["svift", "suift"]),
            ("Kotlin",           ["kotlin"]),
            ("Xcode",            ["eks kod", "eksıkod"]),
            ("CocoaPods",        ["kokoa pods", "kokoapods"]),
            ("Gradle",           ["greydıl", "graydl"]),
            ("ADB",              ["a di bi"]),
            ("SwiftUI",          ["svift yu ay", "swift ui"]),
            ("UIKit",            ["yu ay kit", "ui kit"]),
            ("ViewModel",        ["view model", "viyumodel"]),
            ("CoreData",         ["kor data", "core data"]),
            ("Combine",          ["kombain"]),
            ("Jetpack Compose",  ["jetpek compose", "jetpack kampoz"]),
            ("Room",             ["rum database"]),
            ("Retrofit",         ["retrofit"]),
            ("provisioning profile", ["provijning profil"]),
            ("TestFlight",       ["test flayt"]),
            ("App Store Connect",["app store connect"]),
        ],
    ),

    Persona(
        name="devops",
        description="CI/CD, container, cloud altyapı uzmanı.",
        terms=[
            ("CI/CD",            ["si ay si di", "siyay siydi", "ci cd"]),
            ("Jenkins",          ["cenkins", "jenkins"]),
            ("GitHub Actions",   ["github ekşıns", "githab actions"]),
            ("Terraform",        ["terraform", "teraform"]),
            ("Helm",             ["helm"]),
            ("namespace",        ["nemspeys"]),
            ("pod",              ["pod"]),
            ("deployment",       ["diployment", "deplovment"]),
            ("ingress",          ["ingres"]),
            ("ConfigMap",        ["config map"]),
            ("Secret",           ["secret", "sikrit"]),
            ("kubectl",          ["kubkontrol", "kube kontrol", "kübektıl"]),
            ("Dockerfile",       ["docker file"]),
            ("image",            ["imaj", "docker imaj"]),
            ("registry",         ["registry", "recistry"]),
            ("ArgoCD",           ["argo si di", "argocd"]),
            ("Prometheus",       ["prometiyas", "promethias"]),
            ("Grafana",          ["grafana"]),
            ("Ansible",          ["ansibıl", "ansible"]),
        ],
    ),

    Persona(
        name="junior_dev",
        description="Yeni başlayan geliştirici. Git, temel araçlar konuşur.",
        terms=[
            ("Git",              ["git"]),
            ("GitHub",           ["git hab", "githab", "git hub"]),
            ("commit",           ["komit"]),
            ("push",             ["puş", "push"]),
            ("pull",             ["pul"]),
            ("merge",            ["merg", "merç"]),
            ("branch",           ["branç", "branch"]),
            ("pull request",     ["pul request", "PR"]),
            ("code review",      ["kod rıvyu", "code review"]),
            ("issue",            ["işu", "isu"]),
            ("fork",             ["fork"]),
            ("clone",            ["klon"]),
            ("rebase",           ["ribes", "rebase"]),
            ("stash",            ["steş", "stas"]),
            ("conflict",         ["konflikt"]),
            ("merge conflict",   ["merg konflikt"]),
            ("VS Code",          ["vi es kod", "vscode"]),
            ("IntelliJ",         ["intelicy", "ıntelij"]),
            ("terminal",         ["terminal"]),
            ("localhost",        ["lokal host", "localhost"]),
            ("debug",            ["dibag", "debug"]),
            ("breakpoint",       ["breykpoint"]),
            ("stack trace",      ["stek treys"]),
        ],
    ),

    Persona(
        name="ml_data",
        description="ML/data mühendisi. Model eğitimi, veri işleme konuşur.",
        terms=[
            ("PyTorch",          ["pay torç", "pytorç"]),
            ("TensorFlow",       ["tensor flow", "tensırflow"]),
            ("pandas",           ["pandas"]),
            ("numpy",            ["nampay", "nampi"]),
            ("embedding",        ["embedding", "imbeding"]),
            ("fine-tune",        ["fayn tıyun", "fine tune"]),
            ("LoRA",             ["lora", "lo ra"]),
            ("transformer",      ["transformer"]),
            ("tokenizer",        ["tokenayzer"]),
            ("checkpoint",       ["çekpoint", "checkpoint"]),
            ("epoch",            ["epok", "epoch"]),
            ("batch size",       ["beç sayz", "batch size"]),
            ("learning rate",    ["lörning reyt"]),
            ("loss",             ["los", "loss function"]),
            ("overfitting",      ["ovırfitting"]),
            ("validation",       ["validasyon"]),
            ("inference",        ["inferans", "ınferens"]),
            ("GPU",              ["ge pi yu"]),
            ("CUDA",             ["küda", "cuda"]),
            ("HuggingFace",      ["haging feys", "hagingfeys"]),
            ("Jupyter",          ["yupiter", "jupitır"]),
            ("MLflow",           ["em el flow"]),
            ("A/B test",         ["a bölü b test", "a b test"]),
        ],
    ),
]


def get_all_terms() -> list[tuple[str, list[str]]]:
    """Tüm persona'lardan benzersiz (correct, variants) çiftleri döner."""
    seen: set[str] = set()
    result = []
    for persona in PERSONAS:
        for correct, variants in persona.terms:
            if correct not in seen:
                seen.add(correct)
                result.append((correct, variants))
    return result


def get_persona(name: str) -> Persona | None:
    for p in PERSONAS:
        if p.name == name:
            return p
    return None


if __name__ == "__main__":
    total_terms = sum(len(p.terms) for p in PERSONAS)
    unique_terms = len(get_all_terms())
    total_variants = sum(len(v) for _, v in get_all_terms())

    print(f"Personalar     : {len(PERSONAS)}")
    print(f"Toplam terim   : {total_terms} ({unique_terms} benzersiz)")
    print(f"Toplam varyant : {total_variants}")
    print()
    for p in PERSONAS:
        print(f"  {p.name:20} — {len(p.terms):3} terim")
