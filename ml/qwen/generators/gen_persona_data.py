"""
gen_persona_data.py — Turk developer persona'lari x senaryolar -> bozuk/dogru ciftler.

6 Persona x 8 Senaryo, hardcoded cumleler + phonetic_corruptions engine.
Zero API calls. Zero external dependencies (phonetic_corruptions haric).

Personas:
  1. Ahmet  — Senior Backend (hizli, kesik cumleler, filler az)
  2. Zeynep — Flutter Dev (duzgun ama aksanli teknik terimler)
  3. Emre   — DevOps/SRE (en cok Ingilizce terim)
  4. Elif   — Frontend/React (hook/component terimleri)
  5. Burak  — Junior Dev (en cok filler, cok backtrack)
  6. Deniz  — Product Manager (is Ingilizcesi, daha az teknik)

Scenarios: standup, codereview, pairing, debugging, meeting, onboarding, daily, slack

Output: ../data/persona_*.jsonl
Target: 2000+ pairs

Usage:
    python3 ml/qwen/generators/gen_persona_data.py
"""

import json
import random
import pathlib

from phonetic_corruptions import full_corrupt

random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# Persona tanimlari: (persona_style, persona_name)
# persona_style: phonetic_corruptions.PERSONA_STYLES'daki key
# ─────────────────────────────────────────────────────────────────────────────

# Tuple format: (persona_style, correct_sentence)

# =============================================================================
# SENARYO 1: STANDUP
# =============================================================================

STANDUP = [
    # ── Ahmet — Senior Backend ───────────────────────────────────────────────
    ("senior", "Dun deployment'i tamamladim, bugun API entegrasyonuna bakacagim."),
    ("senior", "Database migration'i production'a aldim, sorunsuz gecti."),
    ("senior", "Redis cache stratejisini degistirdim, response time dustu."),
    ("senior", "Microservice'ler arasi authentication flow'u bitirdim."),
    ("senior", "CI/CD pipeline'i duzelttim, build suresi yariya indi."),
    ("senior", "Container image'lari optimize ettim, boyut yuzde kirk azaldi."),
    ("senior", "Load balancer konfigurasyonunu guncelledim."),
    ("senior", "REST API'nin rate limiting'ini ekledim."),
    ("senior", "Bugun middleware'deki memory leak'i inceleyecegim."),
    ("senior", "Dun aksam hotfix yaptim, rollback'e gerek kalmadi."),

    # ── Zeynep — Flutter Dev ─────────────────────────────────────────────────
    ("mid", "Dun Provider yapisini Riverpod'a tasidim."),
    ("mid", "Widget tree'yi sadelestirdim, performans iyilesti."),
    ("mid", "Hot reload sorunu duzeldi, pubspec'teki versiyon cakismasiydi."),
    ("mid", "Navigator yerine go_router entegrasyonunu bitirdim."),
    ("mid", "ListView builder'a gectim, scroll performansi duzeldi."),
    ("mid", "Platform channel ile native kamera erisimi ekledim."),
    ("mid", "Bugun BLoC pattern'ine gecis yapacagim."),
    ("mid", "Dart null safety migration'i devam ediyor."),
    ("mid", "StatefulWidget'lari gereksiz yere kullanmisiz, temizliyorum."),
    ("mid", "Flutter test coverage'i yuzde altmisa cikardim."),

    # ── Emre — DevOps/SRE ────────────────────────────────────────────────────
    ("senior", "Kubernetes cluster'ina yeni node ekledim."),
    ("senior", "Helm chart'lari versiyonladim, rollback kolaylasti."),
    ("senior", "Terraform state'i remote backend'e tasidim."),
    ("senior", "Jenkins pipeline'da Docker build cache'i aktif ettim."),
    ("senior", "Prometheus alert'leri duzenledim, false positive azaldi."),
    ("senior", "Grafana dashboard'ina yeni metrik paneli ekledim."),
    ("senior", "Ingress konfigurasyonunu SSL termination ile guncelledim."),
    ("senior", "Namespace izolasyonunu tamamladim, her takimin ayri namespace'i var."),
    ("senior", "Bugun Ansible playbook'lari gunceleyecegim."),
    ("senior", "Docker registry'yi private registry'ye tasidim."),

    # ── Elif — Frontend/React ────────────────────────────────────────────────
    ("mid", "useEffect dependency array'ini duzelttim, sonsuz loop gitti."),
    ("mid", "Component'leri memoize ettim, render sayisi azaldi."),
    ("mid", "Next.js'te SSR'dan static generation'a gectim."),
    ("mid", "Tailwind config'i customize ettim, tema renkleri eklendi."),
    ("mid", "Redux store'u context API'ye tasidim, daha basit oldu."),
    ("mid", "TypeScript strict mode actim, yirmi hata cikti."),
    ("mid", "Responsive breakpoint'leri guncelledim, mobil duzeldi."),
    ("mid", "React hook'larini custom hook'a extract ettim."),
    ("mid", "Bugun accessibility audit yapacagim."),
    ("mid", "Virtual DOM reconciliation sorununu cozdum."),

    # ── Burak — Junior Dev ───────────────────────────────────────────────────
    ("junior", "Dun git branch actim ama merge'de conflict cikti."),
    ("junior", "Try catch ekledim ama hala error aliyorum."),
    ("junior", "Function'i async yaptim, await koymay unutmusum."),
    ("junior", "Array'i map ile donuyorum ama undefined geliyor."),
    ("junior", "Pull request actim, review bekliyor."),
    ("junior", "Console log'larla debug ediyorum, breakpoint kullanmayi ogrenecegim."),
    ("junior", "Package'i npm install ile yukledim ama import edemiyorum."),
    ("junior", "Git stash yaptim ama geri alamiyorum."),
    ("junior", "Bugun commit mesajlarini duzeltmem lazim."),
    ("junior", "Variable isimlendirmesini duzelttim, code review'dan dondu."),

    # ── Deniz — Product Manager ──────────────────────────────────────────────
    ("pm", "Sprint velocity bu hafta yuzde on bes dustu."),
    ("pm", "Dun stakeholder meeting'i yaptik, feedback olumlu."),
    ("pm", "Backlog grooming'de bes yeni story ekledik."),
    ("pm", "Acceptance criteria'lari netlestirdim, dev'lere ilettim."),
    ("pm", "Release date'i bir hafta erteledik, blocker var."),
    ("pm", "Demo hazirligi yapiyorum, cuma gunu sunacagiz."),
    ("pm", "KPI dashboard'ini guncelledim, churn rate dusmus."),
    ("pm", "MVP scope'unu daralttik, iki feature cikardik."),
    ("pm", "Bugun roadmap review yapacagiz."),
    ("pm", "User story'lere story point verdik, toplam kirk iki."),
]

# =============================================================================
# SENARYO 2: CODE REVIEW
# =============================================================================

CODE_REVIEW = [
    # ── Ahmet ────────────────────────────────────────────────────────────────
    ("senior", "Bu endpoint'te null check eksik, production'da NPE aliriz."),
    ("senior", "Transaction scope'u cok genis, daraltmamiz lazim."),
    ("senior", "Database query'de N+1 problemi var, eager loading yap."),
    ("senior", "Error handling eksik, try catch ekle."),
    ("senior", "Bu API response'ta sensitive data donuyor, filtrele."),
    ("senior", "Cache invalidation stratejisi yanlis, stale data donebilir."),
    ("senior", "Rate limiting olmadan production'a alamayiz."),
    ("senior", "Logging eksik, debug edemeyiz sorun cikinca."),
    ("senior", "Bu middleware'de authentication bypass var, duzelt."),
    ("senior", "Connection pool size'i cok dusuk, artir."),

    # ── Zeynep ───────────────────────────────────────────────────────────────
    ("mid", "Widget build method'u cok uzun, extract et."),
    ("mid", "setState cok sik cagriliyor, performans sorunu olur."),
    ("mid", "Bu Provider'i dispose etmemissin, memory leak olur."),
    ("mid", "StatefulWidget yerine StatelessWidget kullanabilirsin burada."),
    ("mid", "BuildContext'i async gap'in otesinde kullanma."),
    ("mid", "Navigator push'ta route ismini constant yap."),
    ("mid", "ListView'da itemCount vermemissin, sonsuz scroll olur."),
    ("mid", "StreamBuilder'da snapshot.hasData kontrolu eksik."),
    ("mid", "Scaffold'un body'sinde gereksiz Container var, kaldir."),
    ("mid", "Flutter analyze'dan gelen warning'leri duzelt."),

    # ── Emre ─────────────────────────────────────────────────────────────────
    ("senior", "Dockerfile'da multi-stage build kullan, image kuculsun."),
    ("senior", "Secret'lari environment variable'dan al, hardcode etme."),
    ("senior", "Helm values'da default'lar eksik."),
    ("senior", "Kubernetes manifest'te resource limits belirlenmemis."),
    ("senior", "Prometheus metric isimlendirmesi convention'a uymuyor."),
    ("senior", "Docker compose'da health check ekle."),
    ("senior", "Ingress annotation'lari eksik, timeout cok kisa."),
    ("senior", "ConfigMap'i mount etmemissin, pod environment'i bos."),
    ("senior", "Terraform module'u versiyonlanmamis, lock file ekle."),
    ("senior", "CI pipeline'da test stage'i yok, direkt deploy oluyor."),

    # ── Elif ─────────────────────────────────────────────────────────────────
    ("mid", "useEffect cleanup function'i yok, unmount'ta sorun olur."),
    ("mid", "Bu component'te prop drilling cok fazla, context kullan."),
    ("mid", "TypeScript any kullanmissin, dogru type ver."),
    ("mid", "Bu async function'da error boundary yok."),
    ("mid", "CSS specificity sorunu var, important kullanma."),
    ("mid", "useMemo'nun dependency array'i eksik."),
    ("mid", "Bu component her render'da yeni object olusturuyor, memoize et."),
    ("mid", "React.memo kullanmissin ama props referans degisiyor."),
    ("mid", "Form validation client-side'da eksik."),
    ("mid", "Responsive breakpoint'ler hardcoded, theme'den al."),

    # ── Burak ────────────────────────────────────────────────────────────────
    ("junior", "Bu function cok uzun, bolelim."),
    ("junior", "Variable ismi anlasilmiyor, daha aciklayici yap."),
    ("junior", "Bu import kullanilmiyor, sil."),
    ("junior", "Git commit mesaji aciklayici degil, duzelt."),
    ("junior", "Bu if-else zincirleme cok uzun, switch case kullan."),
    ("junior", "Console log'lari kalmis, sil."),
    ("junior", "Bu array'i map yerine forEach ile donmussun, map kullan."),
    ("junior", "Async function'da return eksik."),

    # ── Deniz ────────────────────────────────────────────────────────────────
    ("pm", "Story point'i yanlis vermisiz, bu daha karmasik."),
    ("pm", "Acceptance criteria karsilanmamis, su feature eksik."),
    ("pm", "Bu ticket'in description'i belirsiz, netlestir."),
    ("pm", "Priority yanlis, bu blocker olmali."),
]

# =============================================================================
# SENARYO 3: PAIR PROGRAMMING
# =============================================================================

PAIR_PROGRAMMING = [
    # ── Ahmet ────────────────────────────────────────────────────────────────
    ("senior", "Su satiri degistir, endpoint URL'ini config'den alsin."),
    ("senior", "Hayir orasi degil, alttaki function'i duzenle."),
    ("senior", "Once migration'i calistir, sonra seed data'yi ekle."),
    ("senior", "Database connection pool'u artir, concurrent request'ler artmis."),
    ("senior", "Cache'e TTL ekle, sonsuza kadar tutmasin."),
    ("senior", "Bu service class'i singleton yap, her seferinde new yapma."),
    ("senior", "Middleware'i route'tan once register et, sirasi onemli."),

    # ── Zeynep ───────────────────────────────────────────────────────────────
    ("mid", "Bu widget'i ayri dosyaya tasiyalim."),
    ("mid", "Navigator'i burada kullanma, callback ile geri don."),
    ("mid", "Bu State'i parent'a tasiyalim, child'lar oradan okusun."),
    ("mid", "Scaffold'a AppBar ekle, back button otomatik gelir."),
    ("mid", "StreamBuilder yerine FutureBuilder kullan, tek seferlik data."),
    ("mid", "Bu widget'i const yap, rebuild'i onle."),
    ("mid", "GestureDetector yerine InkWell kullan, ripple efekti olsun."),

    # ── Emre ─────────────────────────────────────────────────────────────────
    ("senior", "Kubectl apply yap, manifest dosyasini goster."),
    ("senior", "Terraform plan'a bak, neleri degistirecegini gor."),
    ("senior", "Docker compose up yap, servisleri ayaga kaldir."),
    ("senior", "Helm upgrade yap, yeni values dosyasini ver."),
    ("senior", "Pod'un log'larina bak, kubectl logs ile."),
    ("senior", "Ingress'e annotation ekle, timeout'u artir."),
    ("senior", "Prometheus config'e yeni scrape target ekle."),

    # ── Elif ─────────────────────────────────────────────────────────────────
    ("mid", "useEffect'i kaldir, useMemo ile cozelim."),
    ("mid", "Component'i bolelim, header ayri footer ayri olsun."),
    ("mid", "Responsive tasarimi kontrol et, mobilde bozuk."),
    ("mid", "Bu API call'u try catch icine al."),
    ("mid", "TypeScript generic kullan, her type icin ayri function yazma."),
    ("mid", "CSS module kullan, global style kirliligi olmasin."),
    ("mid", "useCallback ile wrap et, child component gereksiz render olmasin."),

    # ── Burak ────────────────────────────────────────────────────────────────
    ("junior", "Dur bekle, o degil, obur dosyayi ac."),
    ("junior", "Hayir hayir, for loop yerine map kullan."),
    ("junior", "Su import'u sil, lazim degil."),
    ("junior", "Console log'lari sil, debug bitti."),
    ("junior", "Degisken ismini degistir, ne oldugu anlasilmiyor."),
    ("junior", "Once git pull yap, sonra branch olustur."),
    ("junior", "Commit etmeden once diff'e bak, ne degistirdigini gor."),

    # ── Deniz ────────────────────────────────────────────────────────────────
    ("pm", "Burada kullanici akisini simule edelim, dogru mu calisiyor?"),
    ("pm", "Bu ekran tasarimdaki gibi degil, Figma'yi kontrol et."),
    ("pm", "Demo'da bu butonu gosterecegim, calisir hale getir."),
    # ── Ekstra cumleler ──────────────────────────────────────────────────────
    ("senior", "Bu API call async olmali, thread block ediyor."),
    ("mid", "Padding degerleri hardcoded, constant'a tasi."),
    ("junior", "Semicolon unutmusum, hata onu gosteriyor."),
    ("senior", "Index ekle, query performance artsin."),
    ("mid", "Color hex'i yanlis, Figma'dan tekrar al."),
    ("junior", "Function parametresini yanlis vermisim, type error aliyor."),
    ("pm", "Su akisi kullaniciya karmasik geldi, sadelestirmemiz lazim."),
    ("senior", "Connection string'i env'den oku, hardcode etme."),
    ("mid", "AnimatedContainer kullan, gecis animasyonu olsun."),
    ("junior", "Import path'i yanlis yazmisim, dosyayi bulamiyor."),
]

# =============================================================================
# SENARYO 4: DEBUGGING
# =============================================================================

DEBUGGING = [
    # ── Ahmet ────────────────────────────────────────────────────────────────
    ("senior", "Stack trace'e bak, error middleware'den geliyor."),
    ("senior", "Database connection timeout aliyoruz, pool size'i kontrol et."),
    ("senior", "Memory leak var, heap dump al, analiz et."),
    ("senior", "API response suresi uc saniyeyi geciyor, profiling yap."),
    ("senior", "DNS resolution timeout, resolv.conf'u kontrol et."),
    ("senior", "Thread deadlock var, lock sirasini kontrol et."),
    ("senior", "Query plan'a bak, index eksik olabilir."),

    # ── Zeynep ───────────────────────────────────────────────────────────────
    ("mid", "Widget rebuild surekli oluyor, key eksik olabilir."),
    ("mid", "Hot reload calismiyor, Flutter clean yapip tekrar dene."),
    ("mid", "Null pointer exception aliyor, optional chaining ekle."),
    ("mid", "State guncellenmiyor, immutability kuralini cignemisiz."),
    ("mid", "Platform channel hata veriyor, native tarafta log'a bak."),
    ("mid", "Build context hata veriyor, async gap sorunu."),
    ("mid", "Riverpod provider'i dispose olmuyor, ref.onDispose ekle."),

    # ── Emre ─────────────────────────────────────────────────────────────────
    ("senior", "Container restart loop'a girmis, log'lara bak."),
    ("senior", "Pod CrashLoopBackOff'ta, describe pod yap."),
    ("senior", "Ingress'ten 502 donuyor, backend service'i kontrol et."),
    ("senior", "Prometheus scrape fail oluyor, port mapping kontrol et."),
    ("senior", "Helm upgrade fail oldu, rollback yap."),
    ("senior", "Docker build cache bozulmus, no-cache ile rebuild et."),
    ("senior", "Terraform state lock kalmis, force unlock yap."),

    # ── Elif ─────────────────────────────────────────────────────────────────
    ("mid", "Component mount edilmiyor, conditional render'da sorun var."),
    ("mid", "useEffect iki kere calisiyor, React strict mode yuzunden."),
    ("mid", "CSS'te z-index savasi var, stacking context'i duzelt."),
    ("mid", "Hydration mismatch aliyor, server ve client farkli render ediyor."),
    ("mid", "Form state resetlenmiyor, key prop ekle."),
    ("mid", "Layout shift oluyor, image dimensions ver."),
    ("mid", "Bundle size cok buyuk, lazy import kullan."),

    # ── Burak ────────────────────────────────────────────────────────────────
    ("junior", "Error mesajini okuyamiyorum, turkce degil."),
    ("junior", "Console'da bir suru warning var, hangisi onemli?"),
    ("junior", "Git merge conflict'i cozemedim, dosya karismis."),
    ("junior", "Async await'te sira karismis, Promise.all kullanmaliydin."),
    ("junior", "Npm install hata veriyor, node versiyonunu kontrol et."),
    ("junior", "Bu hata ilk defa cikti, dun calisiyordu."),
    ("junior", "Stack overflow hatasi aliyor, recursive function sonsuz donuyor."),

    # ── Deniz ────────────────────────────────────────────────────────────────
    ("pm", "Sprint'teki bug sayisi artti, root cause analysis yapalim."),
    ("pm", "Musteri bu hatayi raporladi, oncelikli duzelt."),
    ("pm", "Demo'da crash oldu, hotfix gerekiyor."),
    # ── Ekstra cumleler ──────────────────────────────────────────────────────
    ("senior", "Cache hit rate cok dusuk, key pattern'i yanlis."),
    ("mid", "Overflow hatasi aliyor, SingleChildScrollView ekle."),
    ("junior", "Undefined is not a function hatasi, typo olabilir."),
    ("senior", "Race condition var, mutex ekle."),
    ("mid", "Build mode'u release'de calisiyor, debug'a cevir."),
    ("junior", "Git diff'e baktim ama ne degistirdigimi anlamadim."),
    ("pm", "Kullanici bu ekranda sikiliyor, analytics verisi dusuk."),
    ("senior", "Connection leak var, finally block'ta close cagir."),
    ("mid", "Theme data override olmamis, default renk geliyor."),
    ("junior", "Boolean logic yanlis, true yerine false koymusum."),
]

# =============================================================================
# SENARYO 5: MEETING
# =============================================================================

MEETING = [
    # ── Ahmet ────────────────────────────────────────────────────────────────
    ("senior", "Deployment stratejisini blue-green'e gecirelim."),
    ("senior", "Microservice architecture'a gecis planini konusalim."),
    ("senior", "API versioning stratejimiz ne olacak?"),
    ("senior", "Monitoring ve alerting stratejimizi gozden gecirelim."),
    ("senior", "Performance budget belirleyelim, sayfa yuklenme suresi iki saniye olsun."),
    ("senior", "Database sharding'e ihtiyacimiz var mi, trafik artiyor."),
    ("senior", "Backend team olarak bu ceyregin hedeflerini belirleyelim."),

    # ── Zeynep ───────────────────────────────────────────────────────────────
    ("mid", "Flutter'dan React Native'e gecmeli miyiz, arti eksileri tartisalim."),
    ("mid", "Component library olusturalim, design system standardize olsun."),
    ("mid", "Mobil uygulama performans metrikleri nasil, bakabilir miyiz?"),
    ("mid", "Widget test coverage'i dusuk, test sprint'i ayiralim."),
    ("mid", "Platform specific kod cok artti, abstract layer ekleyelim."),

    # ── Emre ─────────────────────────────────────────────────────────────────
    ("senior", "Kubernetes upgrade'i yapmaliyiz, versiyon eski kaldi."),
    ("senior", "Cloud cost optimization yapmamiz lazim, aylik fatura artti."),
    ("senior", "Disaster recovery planimiz var mi, test edelim."),
    ("senior", "CI/CD pipeline sureleri cok uzun, optimize edelim."),
    ("senior", "Infrastructure as code'a tam gecis yapalim."),

    # ── Elif ─────────────────────────────────────────────────────────────────
    ("mid", "Technical debt cok birikti, bir sprint ayiralim."),
    ("mid", "Design system'i Storybook'a tasiyalim."),
    ("mid", "Frontend bundle size'i cok buyuk, code splitting yapalim."),
    ("mid", "Accessibility standartlarina uyum saglamaliyiz."),
    ("mid", "Web vitals skorlarimiz dusuk, iyilestirme plani yapalim."),

    # ── Burak ────────────────────────────────────────────────────────────────
    ("junior", "Bu toplantinin amaci ne, gundem var mi?"),
    ("junior", "Ben bu konuda cok bilgili degilim, biri aciklayabilir mi?"),
    ("junior", "Junior'lar icin mentorluk programi baslatalim."),
    ("junior", "Dokumentasyon cok eski, guncellememiz lazim."),
    ("junior", "Onboarding sureci uzun, kisaltamaz miyiz?"),

    # ── Deniz ────────────────────────────────────────────────────────────────
    ("pm", "Q3 roadmap'i gozden gecirelim, migration ne durumda?"),
    ("pm", "Bu feature'in ROI'si nedir, onceliklendirelim."),
    ("pm", "Sprint retrospective'de neler cikti, aksiyonlar ne?"),
    ("pm", "Deadline'i kaciracagiz, scope'u daraltmamiz lazim."),
    ("pm", "Stakeholder'lardan feedback geldi, requirement degisti."),
    ("pm", "User research sonuclarini paylasayim, ilginc bulgular var."),
    ("pm", "Release cycle'i iki haftadan bir haftaya dusurelim."),
    ("pm", "MVP'den sonra hangi feature'lari ekleyecegiz?"),
    ("pm", "Budget'i astik, maliyet optimizasyonu yapmamiz lazim."),
]

# =============================================================================
# SENARYO 6: ONBOARDING
# =============================================================================

ONBOARDING = [
    # ── Ahmet ────────────────────────────────────────────────────────────────
    ("senior", "Once repository'yi klonla, git clone komutuyla."),
    ("senior", "Env dosyasini kopyala, env.example'dan env dosyasi yap."),
    ("senior", "Docker compose up yap, tum servisler ayaga kalksin."),
    ("senior", "Database migration'lari calistir, tablolari olustursun."),
    ("senior", "Postman collection'i import et, API endpoint'lerini test edebilirsin."),
    ("senior", "VPN baglan, internal servislere erisim icin gerekli."),
    ("senior", "Logging framework'u olarak Winston kullaniyoruz."),

    # ── Zeynep ───────────────────────────────────────────────────────────────
    ("mid", "Flutter SDK'yi kur, versiyon uc nokta on olsun."),
    ("mid", "Pubspec'teki paketleri indir, flutter pub get yap."),
    ("mid", "Figma'daki design'lari incele, component listesi orada."),
    ("mid", "Storybook'u calistir, component'leri orada gorebilirsin."),
    ("mid", "iOS icin Xcode kurulumu gerekli, son versiyonu yukle."),
    ("mid", "Android Studio'da AVD olustur, emulatorde test edebilirsin."),
    ("mid", "Flutter doctor calistir, eksik bagimlilik var mi bak."),

    # ── Emre ─────────────────────────────────────────────────────────────────
    ("senior", "Kubernetes cluster'a erisim icin kubeconfig'i al."),
    ("senior", "Helm repo'yu ekle, chart'lari indir."),
    ("senior", "Docker Desktop'i kur, local development icin gerekli."),
    ("senior", "Terraform CLI'yi kur, workspace'i initialize et."),
    ("senior", "AWS CLI konfigure et, credential'lari ayarla."),
    ("senior", "Kubectl context'ini staging'e ayarla, production'a dokunma."),
    ("senior", "Monitoring dashboard'larin linklerini paylasiyorum."),

    # ── Elif ─────────────────────────────────────────────────────────────────
    ("mid", "Node modules'u yukle, npm install yap."),
    ("mid", "TypeScript compiler'i kontrol et, tsconfig dogru mu bak."),
    ("mid", "Code style icin ESLint ve Prettier konfigure edilmis, otomatik format."),
    ("mid", "VS Code extension'larini yukle, listesi README'de."),
    ("mid", "Husky pre-commit hook kurulu, commit oncesi lint calisir."),
    ("mid", "Dev server'i calistir, npm run dev ile."),
    ("mid", "Browser'da React DevTools extension'ini kur."),

    # ── Burak ────────────────────────────────────────────────────────────────
    ("junior", "Git branch olustur, feature branch'ten calis, main'e direkt push etme."),
    ("junior", "Pull request actiginda reviewer olarak beni ekle."),
    ("junior", "Sorun olursa Slack'ten yaz, hizli cevap alirsin."),
    ("junior", "Jira board'u kullaniyoruz, sprint backlog'dan task al."),
    ("junior", "Daily standup her sabah dokuzda, zamaninda katil."),
    ("junior", "Kod yazarken linter'a dikkat et, CI'da fail olmasin."),
    ("junior", "Test yazmadan PR acma, coverage dusmesin."),

    # ── Deniz ────────────────────────────────────────────────────────────────
    ("pm", "Confluence'da dokumantasyon var, once oraya bak."),
    ("pm", "Sprint planning her pazartesi, backlog'u onceden incele."),
    ("pm", "Retrospective notlarini oku, takimin aliskanliklarini ogren."),
    ("pm", "Stakeholder listesini paylasiyorum, kiminle ne konusacagini bil."),
]

# =============================================================================
# SENARYO 7: DAILY CHAT (gunluk sohbet, teknik olmayan)
# =============================================================================

DAILY_CHAT = [
    # ── Ahmet ────────────────────────────────────────────────────────────────
    ("senior", "Toplanti odasi dolu, baska yer bulalim."),
    ("senior", "Ofiste internet yavasladi, IT'ye haber verelim."),
    ("senior", "Projeksiyonu acar misin, sunumu gosterecegim."),
    ("senior", "Aksam yemegini siparis edelim mi, gec kalacagiz."),
    ("senior", "Yeni MacBook geldi, kurulumu yapiyorum."),

    # ── Zeynep ───────────────────────────────────────────────────────────────
    ("mid", "Ogle yemegine cikalim mi, asagidaki restoran guzel."),
    ("mid", "Bugun hava cok guzel, disarida oturalim."),
    ("mid", "Kahve molasi verelim, bes dakika ara."),
    ("mid", "Yarin izin alacagim, doktora gitmem lazim."),
    ("mid", "Yeni kahve makinesi cok iyi, espresso dene."),

    # ── Emre ─────────────────────────────────────────────────────────────────
    ("senior", "Klima cok soguk, biraz kisabilir miyiz?"),
    ("senior", "Asansor yine bozulmus, merdivenden cikalim."),
    ("senior", "Server odasinin kilidi degismis, yeni anahtari al."),
    ("senior", "UPS bipledi, elektrik kesintisi olabilir."),
    ("senior", "Ofis tasiniyor, yeni adresi paylasiyorum."),

    # ── Elif ──────────────────────────────────────────────────────────────────
    ("mid", "Bugun erken cikacagim, cocugu okuldan almam lazim."),
    ("mid", "Bayram tatili ne zaman basliyor, plan yapmam lazim."),
    ("mid", "Yeni gelen arkadas cok iyi, ekibe uyum sagladi."),
    ("mid", "Kantindeki yemek bugun fena degildi aslinda."),
    ("mid", "Dogum gunu kutlamasi saat ucte, kat otoparkin yaninda."),

    # ── Burak ────────────────────────────────────────────────────────────────
    ("junior", "Aksam bir seyler yapalim mi, sinema falan?"),
    ("junior", "Hafta sonu ne yapiyorsun, futbol var mi?"),
    ("junior", "Dun gece maci izledin mi, cok guzel gol vardi."),
    ("junior", "Bu hafta cok yoruldum, cuma erken cikayim."),
    ("junior", "Yemek uygulamasindan siparis verelim mi?"),
    ("junior", "Ofiste koltuk degistirmek istiyorum, su kose daha rahat."),
    ("junior", "Netflix'te yeni dizi baslamis, tavsiye ederim."),

    # ── Deniz ────────────────────────────────────────────────────────────────
    ("pm", "Team building etkinligi ayarliyorum, ne yapalim?"),
    ("pm", "Musteriye hediye gonderelim, bayram icin."),
    ("pm", "Ofis temizligi icin mesaj attim, yarin gelecekler."),
    ("pm", "Toplanti sonrasi kahve iceriz, konusalim."),
    # ── Ekstra cumleler ──────────────────────────────────────────────────────
    ("senior", "Bugun Cuma, bir saat erken cikalim."),
    ("mid", "Printer bozulmus, IT'ye ticket acalim."),
    ("junior", "Yeni klavye geldi, mekanik, cok guzel."),
    ("pm", "Ofis kurallarini guncelliyoruz, mail attim."),
    ("mid", "Yarin kar yagacakmis, dikkatli gelin."),
    ("junior", "Spotify'da guzel bir playlist var, atiyorum."),
    ("senior", "Sunumdaki slaytlari hazirliyorum, yarin sabaha kadar biter."),
    ("mid", "Arkadasi karsilayalim, lobi'de bekliyor."),
    ("junior", "Bugun dogum gunum, pasta getirdim."),
    ("pm", "Hafta sonu hackathon var, katilmak isteyen var mi?"),
]

# =============================================================================
# SENARYO 8: SLACK (kisa, informal mesajlar)
# =============================================================================

SLACK = [
    # ── Ahmet ────────────────────────────────────────────────────────────────
    ("senior", "Merge conflict var, bakar misin?"),
    ("senior", "Production'da 500 error aliyoruz, acil bak."),
    ("senior", "Deployment basarili, staging'e gecti."),
    ("senior", "Hotfix branch'i actim, cherry-pick yaptim."),
    ("senior", "SSL sertifikasi yarin expire oluyor, yenile."),
    ("senior", "Cache temizledim, response time dustu."),
    ("senior", "API rate limit'e takiliyoruz, artirmamiz lazim."),

    # ── Zeynep ───────────────────────────────────────────────────────────────
    ("mid", "Flutter build fail oldu, Xcode guncelle."),
    ("mid", "Component hazir, test yazacagim."),
    ("mid", "Widget test gecti, PR'a push ettim."),
    ("mid", "Hot reload bozuldu, flutter clean yaptim duzledi."),
    ("mid", "Riverpod migration bitti, review'a hazir."),

    # ── Emre ─────────────────────────────────────────────────────────────────
    ("senior", "Kubernetes pod restart oldu, log'lara baktim sorun yok."),
    ("senior", "Docker image push ettim, registry'de."),
    ("senior", "Grafana'da alert geldi, CPU yuzde doksanda."),
    ("senior", "Terraform apply basarili, infra guncellendi."),
    ("senior", "Jenkins build fail oldu, disk dolu."),

    # ── Elif ─────────────────────────────────────────────────────────────────
    ("mid", "API dokumantasyonu guncellendi, Swagger'a bak."),
    ("mid", "Code freeze yarin, son commit'leri bugun at."),
    ("mid", "Bundle size'i yuzde yirmi dusurduk."),
    ("mid", "Lighthouse skoru doksan bes'e cikti."),
    ("mid", "Design token'lari guncellendi, CSS variable'lari degisti."),

    # ── Burak ────────────────────────────────────────────────────────────────
    ("junior", "Bu nasil calisiyor, aciklar misin?"),
    ("junior", "Branch'i sildim yanlislikla, geri getirebilir miyiz?"),
    ("junior", "Npm install hata veriyor, node versiyonunu kontrol et."),
    ("junior", "PR'im iki gundur review bekliyor, bakabilir misin?"),
    ("junior", "Git push reject oldu, once pull yapmam mi lazim?"),
    ("junior", "Test yazdim ama fail oluyor, nerede hata var?"),

    # ── Deniz ────────────────────────────────────────────────────────────────
    ("pm", "PR'a approve verdim, merge edebilirsin."),
    ("pm", "Sprint planning yarin saat onda, davetiye attim."),
    ("pm", "Figma'daki design degisti, yeni mock-up'lara bak."),
    ("pm", "Meeting'i iptal ettim, async halledelim."),
    ("pm", "Backlog'a yeni bug ekledim, bak istersen."),
    ("pm", "Release note'lari hazirliyorum, degisiklikleri listeleyin."),
    # ── Ekstra cumleler ──────────────────────────────────────────────────────
    ("senior", "Migration'i geri aldim, rollback basarili."),
    ("mid", "Build suresi artmis, investigate ediyorum."),
    ("junior", "Merge ettim ama test fail oldu, duzeltiyorum."),
    ("senior", "Database backup'i tamamlandi, schedule calisiyor."),
    ("mid", "Pub get fail oluyor, cache temizle."),
    ("junior", "Commit push ettim, CI bekliyor."),
    ("pm", "Demo linki hazirliyorum, bitmeden gonderirim."),
    ("senior", "Load test sonuclari geldi, bin concurrent user kaldiriyor."),
    ("mid", "Lighthouse report'u paylasiyorum."),
    ("junior", "Bu error'u Google'ladim ama cozum bulamadim."),
]

# =============================================================================
# TUM SENARYOLAR
# =============================================================================

ALL_SCENARIOS = {
    "standup": STANDUP,
    "codereview": CODE_REVIEW,
    "pairing": PAIR_PROGRAMMING,
    "debugging": DEBUGGING,
    "meeting": MEETING,
    "onboarding": ONBOARDING,
    "daily": DAILY_CHAT,
    "slack": SLACK,
}

OUT_DIR = pathlib.Path(__file__).parent.parent / "data"


def generate_pairs(
    scenario_name: str,
    sentences: list[tuple[str, str]],
    variants_per_sentence: int = 7,
) -> list[dict]:
    """Her cumle icin birden fazla bozuk varyant uret (farkli random bozukluklar).

    Args:
        scenario_name: Senaryo adi (dosya adinda kullanilir).
        sentences: (persona_style, correct_sentence) tuple listesi.
        variants_per_sentence: Her cumle icin kac bozuk varyant uretilecegi.

    Returns:
        {"input": bozuk, "output": dogru} dict listesi.
    """
    pairs = []
    seen_inputs = set()

    for persona_style, correct in sentences:
        for v in range(variants_per_sentence):
            # Tekrarlanabilir ama her varyant farkli
            random.seed(hash((correct, v, scenario_name)) & 0xFFFFFFFF)
            corrupted = full_corrupt(correct, persona_style)

            # Eger bozukluk uygulanmadiysa, en azindan noktalama ve buyuk harf boz
            if corrupted.strip() == correct.strip():
                corrupted = correct.lower()
                for ch in ".,?!;:":
                    corrupted = corrupted.replace(ch, "")
                corrupted = corrupted.strip()

            # Deduplicate
            if corrupted not in seen_inputs and corrupted != correct:
                seen_inputs.add(corrupted)
                pairs.append({"input": corrupted, "output": correct})

    random.seed(42)  # reset
    return pairs


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0

    print("Generating persona data...\n")

    for name, sentences in ALL_SCENARIOS.items():
        pairs = generate_pairs(name, sentences)
        out_path = OUT_DIR / f"persona_{name}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for pair in pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")
        total += len(pairs)
        print(f"  persona_{name}.jsonl — {len(pairs):>4d} pairs ({len(sentences)} base sentences)")

    print(f"\n{'='*60}")
    print(f"TOTAL: {total} persona pairs written to {OUT_DIR}")
    print(f"{'='*60}")

    if total < 2000:
        print(f"\nWARNING: {total} < 2000 target. Consider increasing variants_per_sentence.")


if __name__ == "__main__":
    main()
