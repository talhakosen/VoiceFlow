"""Türk developer persona'ları — konuşma stili, terimler, filler sıklığı."""

PERSONAS = {
    "ahmet_backend": {
        "name": "Ahmet",
        "role": "Senior Backend Developer",
        "age": 35,
        "city": "İstanbul",
        "style": "Hızlı konuşur, cümleleri kısa keser. Teknik terimleri cümle içine doğal serpiştir.",
        "filler_freq": "low",  # nadiren filler kullanır
        "backtrack_freq": "low",
        "common_terms": [
            "endpoint", "deployment", "container", "API", "database", "migration",
            "microservice", "load balancer", "Redis", "PostgreSQL", "Docker",
            "CI/CD", "pipeline", "rollback", "scaling", "caching", "queue",
            "REST", "GraphQL", "middleware", "ORM", "transaction",
        ],
        "example_sentences": [
            "Şu endpoint'i refactor etmemiz lazım, response time çok yüksek.",
            "Deployment pipeline'da sorun var, container image'ı pull edemiyor.",
            "Database migration'ı çalıştırdım, production'da sorun yok.",
            "Redis cache'i temizle, stale data dönüyor.",
            "Microservice'ler arası latency artmış, load balancer'ı kontrol et.",
        ],
    },

    "zeynep_flutter": {
        "name": "Zeynep",
        "role": "Flutter Developer",
        "age": 28,
        "city": "Ankara",
        "style": "Düzgün ve net konuşur ama teknik terimlerde Türk aksanı belirgin.",
        "filler_freq": "medium",
        "backtrack_freq": "low",
        "common_terms": [
            "widget", "StatefulWidget", "StatelessWidget", "Provider", "Riverpod",
            "BuildContext", "setState", "Navigator", "scaffold", "ListView",
            "Flutter", "Dart", "pubspec", "hot reload", "platform channel",
            "async", "Future", "Stream", "BLoC", "Cubit",
        ],
        "example_sentences": [
            "StatefulWidget'tan StatelessWidget'a çevirelim, state yönetimi Provider'da.",
            "BuildContext'e erişemiyorum, widget tree'de çok derinde.",
            "Hot reload çalışmıyor, pubspec'te bir şey değişmiş olabilir.",
            "Navigator push yerine go_router kullanmalıyız.",
            "Bu ListView çok yavaş, builder kullanmamız lazım.",
        ],
    },

    "emre_devops": {
        "name": "Emre",
        "role": "DevOps / SRE",
        "age": 30,
        "city": "İzmir",
        "style": "En çok İngilizce terim kullanan kişi. Kısa, komut gibi cümleler.",
        "filler_freq": "low",
        "backtrack_freq": "low",
        "common_terms": [
            "Kubernetes", "cluster", "Helm", "chart", "ingress", "pod",
            "node", "namespace", "Terraform", "Ansible", "Jenkins",
            "Prometheus", "Grafana", "alerting", "monitoring", "scaling",
            "Docker Compose", "registry", "volume", "secret", "configmap",
        ],
        "example_sentences": [
            "Kubernetes cluster'ı scale etmemiz gerekiyor, pod'lar limit'e geldi.",
            "Helm chart'ı güncelle, ingress konfigürasyonunu değiştir.",
            "Terraform plan çalıştır, infrastructure değişikliğini gör.",
            "Prometheus alert'leri patlıyor, disk usage yüzde doksanın üstünde.",
            "Jenkins pipeline fail oldu, Docker build aşamasında hata var.",
        ],
    },

    "elif_frontend": {
        "name": "Elif",
        "role": "Frontend / React Developer",
        "age": 26,
        "city": "Remote",
        "style": "Component ve hook terimleri çok kullanır. Açıklayıcı konuşur.",
        "filler_freq": "medium",
        "backtrack_freq": "medium",
        "common_terms": [
            "component", "hook", "useEffect", "useState", "useMemo",
            "React", "Next.js", "TypeScript", "props", "state",
            "Redux", "context", "render", "virtual DOM", "SSR",
            "Tailwind", "CSS", "responsive", "breakpoint", "flex",
        ],
        "example_sentences": [
            "useEffect'te dependency array eksik, sonsuz loop'a giriyor.",
            "Bu component'i memoize etmeliyiz, her render'da yeniden oluşturuluyor.",
            "Props drilling çok fazla, Context veya Redux kullanmalıyız.",
            "Next.js'te SSR ile pre-render edelim, SEO için önemli.",
            "Tailwind class'ları çok uzadı, component'e extract edelim.",
        ],
    },

    "burak_junior": {
        "name": "Burak",
        "role": "Junior Developer",
        "age": 23,
        "city": "İstanbul",
        "style": "En çok filler kullanan. Cümle yapısı dağınık, çok düşünür konuşurken. Sık backtrack yapar.",
        "filler_freq": "high",  # yani, şey, hani, ee çok kullanır
        "backtrack_freq": "high",
        "common_terms": [
            "function", "variable", "array", "object", "loop",
            "if else", "try catch", "console log", "git", "branch",
            "commit", "push", "pull request", "merge", "conflict",
            "npm", "package", "import", "export", "async await",
        ],
        "example_sentences": [
            "Yani şey, bu function'ı nasıl çağıracağız, parametre mi alıyor?",
            "Git'te branch açtım ama, hani, push yapamıyorum bir türlü.",
            "Ee, try catch koydum ama error hâlâ geliyor, neden acaba?",
            "Şey, bu array'i loop'la dönmem lazım ama index karışıyor.",
            "Yani, pull request açtım, review bekliyor, merge edebilir miyiz?",
        ],
    },

    "deniz_pm": {
        "name": "Deniz",
        "role": "Product Manager",
        "age": 32,
        "city": "İstanbul",
        "style": "İş İngilizcesi karışık Türkçe. Daha az teknik, daha çok süreç odaklı. Formal ton.",
        "filler_freq": "medium",
        "backtrack_freq": "low",
        "common_terms": [
            "sprint", "backlog", "roadmap", "milestone", "deadline",
            "stakeholder", "demo", "retrospective", "velocity", "story point",
            "scope", "requirement", "user story", "acceptance criteria",
            "deliverable", "blocker", "priority", "release", "MVP", "KPI",
        ],
        "example_sentences": [
            "Sprint goal'u değişmedi ama scope creep oluyor, dikkatli olalım.",
            "Stakeholder'lara demo yapmamız lazım, cuma gününe hazırlayalım.",
            "Bu feature'ın acceptance criteria'sı net değil, product owner'la konuşalım.",
            "Velocity düştü bu sprint'te, blocker'ları kaldırmamız lazım.",
            "MVP'yi çıkaralım önce, nice to have'ler backlog'da kalsın.",
        ],
    },
}

# Senaryo kategorileri
SCENARIOS = {
    "standup": {
        "name": "Daily Standup",
        "description": "Günlük toplantı — dün ne yaptım, bugün ne yapacağım, blocker var mı",
        "tone": "kısa, öz, raporlama",
    },
    "code_review": {
        "name": "Code Review",
        "description": "PR inceleme — hata bulma, öneri, onay/ret",
        "tone": "teknik, detaylı, eleştirel",
    },
    "pair_programming": {
        "name": "Pair Programming",
        "description": "Birlikte kodlama — yönlendirme, düzeltme, soru-cevap",
        "tone": "interaktif, hızlı, backtrack çok",
    },
    "debugging": {
        "name": "Debugging",
        "description": "Hata ayıklama — log okuma, deneme-yanılma, hipotez",
        "tone": "düşünceli, sorgulayıcı",
    },
    "meeting": {
        "name": "Toplantı / Planning",
        "description": "Sprint planning, roadmap review, teknik karar",
        "tone": "tartışma, önerme, karar",
    },
    "onboarding": {
        "name": "Onboarding",
        "description": "Yeni gelene anlatım — kurulum, süreç, araçlar",
        "tone": "açıklayıcı, adım adım",
    },
    "daily_chat": {
        "name": "Günlük Sohbet",
        "description": "İş dışı — yemek, hava, plan, dedikodu",
        "tone": "rahat, informal, kısa",
    },
    "slack": {
        "name": "Slack / Teams Mesajı",
        "description": "Yazılı ama sesli dikte — kısa, acil, informal",
        "tone": "kısa, direkt, noktalama az",
    },
}
