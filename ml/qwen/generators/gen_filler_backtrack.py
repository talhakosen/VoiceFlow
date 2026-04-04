"""
gen_filler_backtrack.py — Backtracking + filler combo examples.
Zero API calls. Zero external dependencies.
Output: ../data/filler_backtrack.jsonl
"""

import json
import pathlib

DATA = [
    # ── Pure backtrack (no fillers) ───────────────────────────────────────
    {"input": "raporu aç, hayır yok yok, o diğer raporu aç", "output": "O diğer raporu aç."},
    {"input": "saat 3'te, hani 4'te", "output": "Saat 4'te."},
    {"input": "bunu sil, dur dur, bunu kopyala", "output": "Bunu kopyala."},
    {"input": "şu branch'e geç, hayır master'a geç", "output": "Master'a geç."},
    {"input": "commit at, bekle bekle, önce test çalıştır", "output": "Önce test çalıştır."},
    {"input": "toplantı cuma, ya da perşembe", "output": "Toplantı perşembe."},
    {"input": "deploy yapalım, hayır hayır, önce review lazım", "output": "Önce review lazım."},
    {"input": "bütçe 50K, yani 60K", "output": "Bütçe 60K."},
    {"input": "servisi yeniden başlat, dur, önce log'a bak", "output": "Önce log'a bak."},
    {"input": "o dosyayı sil, aslında taşı", "output": "O dosyayı taşı."},
    {"input": "saat 2'de çıkalım, hayır 3'te", "output": "Saat 3'te çıkalım."},
    {"input": "Ahmed'e yaz, yok Ali'ye yaz", "output": "Ali'ye yaz."},
    {"input": "production'a al, dur dur, staging'e al önce", "output": "Staging'e al önce."},
    {"input": "bu fonksiyonu refactor et, aslında sil", "output": "Bu fonksiyonu sil."},
    {"input": "meeting Zoom'da, hayır Teams'de", "output": "Meeting Teams'de."},

    # ── Backtrack + sentence-initial filler ──────────────────────────────
    {"input": "Yani, raporu aç, hayır o diğer raporu aç", "output": "O diğer raporu aç."},
    {"input": "Şey, şu branch'e geç, hayır master'a geç", "output": "Master'a geç."},
    {"input": "Yani, commit at, dur dur, önce test çalıştır", "output": "Önce test çalıştır."},
    {"input": "Tamam, saat 3'te çıkalım, hayır 4'te", "output": "Saat 4'te çıkalım."},
    {"input": "Ee, deploy yapalım, bekle bekle, önce review lazım", "output": "Önce review lazım."},
    {"input": "İşte, servisi başlat, dur, önce log'a bak", "output": "Önce log'a bak."},
    {"input": "Hani, bütçe 50K, yani 60K", "output": "Bütçe 60K."},
    {"input": "Şey, Ahmed'e yaz, yok Ali'ye yaz", "output": "Ali'ye yaz."},
    {"input": "Yani şey, meeting Zoom'da, hayır Teams'de", "output": "Meeting Teams'de."},
    {"input": "Tamam, production'a al, dur dur, staging'e al önce", "output": "Staging'e al önce."},
    {"input": "Ee, bu fonksiyonu refactor et, aslında sil", "output": "Bu fonksiyonu sil."},
    {"input": "Hani, Ahmed'i ara, yok e-posta at", "output": "Ahmed'e e-posta at."},
    {"input": "Yani, şu PR'ı kapat, bekle, önce review iste", "output": "Önce review iste."},
    {"input": "İşte, veritabanını temizle, hayır önce backup al", "output": "Önce backup al."},
    {"input": "Şey, toplantı cuma, ya da perşembe olsun", "output": "Toplantı perşembe olsun."},

    # ── Backtrack + mid-sentence filler ──────────────────────────────────
    {"input": "şu dosyayı, yani, sil, hayır taşı", "output": "Şu dosyayı taşı."},
    {"input": "bunu, şey, kaydet, dur önce test et", "output": "Bunu önce test et."},
    {"input": "API'yi, ee, güncelle, hayır rollback yap", "output": "API'yi rollback yap."},
    {"input": "commit'i, yani, gönder, bekle review bekliyor", "output": "Commit'i gönder, review bekliyor."},
    {"input": "şu kodu, şey, sil, aslında yorum satırına al", "output": "Şu kodu yorum satırına al."},
    {"input": "Ahmed'e, hani, yaz, yok Ali'ye yaz", "output": "Ali'ye yaz."},
    {"input": "meeting'i, ee, iptal et, hayır ertele", "output": "Meeting'i ertele."},
    {"input": "bütçeyi, yani, artır, dur önce onayla", "output": "Bütçeyi artırmadan önce onayla."},
    {"input": "deployment'ı, şey, durdur, hayır devam et", "output": "Deployment'a devam et."},
    {"input": "log'ları, ee, temizle, dur önce incele", "output": "Log'ları önce incele."},

    # ── Backtrack + both initial and mid fillers ──────────────────────────
    {"input": "Yani, şu branch'e, şey, geç, hayır master'a geç", "output": "Master'a geç."},
    {"input": "Tamam, bunu, yani, kaydet, dur önce kontrol et", "output": "Bunu önce kontrol et."},
    {"input": "Ee, API'yi, şey, güncelle, hayır rollback yap", "output": "API'yi rollback yap."},
    {"input": "İşte, Ahmed'e, hani, yaz, yok Ali'ye yaz", "output": "Ali'ye yaz."},
    {"input": "Hani, şu kodu, yani, sil, aslında taşı", "output": "Şu kodu taşı."},
    {"input": "Şey, meeting'i, ee, iptal et, hayır ertele", "output": "Meeting'i ertele."},
    {"input": "Yani şey, deployment'ı, ee, durdur, hayır devam et", "output": "Deployment'a devam et."},
    {"input": "Tamam, commit'i, şey, gönder, bekle review bekliyor", "output": "Commit'i gönder, review bekliyor."},
    {"input": "Ee, log'ları, yani, temizle, dur önce incele", "output": "Log'ları önce incele."},
    {"input": "Yani, şu PR'ı, şey, kapat, bekle önce review iste", "output": "Önce review iste."},

    # ── Course correction mid-sentence ───────────────────────────────────
    {"input": "şimdi veritabanına kaydedelim hayır yok yok önce validasyon yapalım", "output": "Önce validasyon yapalım."},
    {"input": "let's save to the database scratch that let's do validation first", "output": "Let's do validation first."},
    {"input": "X yapalım, ya da Y yapalım", "output": "Y yapalım."},
    {"input": "bunu merge et, hayır hayır, önce conflict'lere bak", "output": "Önce conflict'lere bak."},
    {"input": "o tabloyu drop et, dur dur, önce backup al", "output": "Önce backup al."},
    {"input": "paketi yükle, hayır önce requirements.txt güncelle", "output": "Önce requirements.txt güncelle."},
    {"input": "test environment'ı sıfırla, dur, önce log al", "output": "Önce log al."},
    {"input": "endpoint'i kaldır, hayır sadece devre dışı bırak", "output": "Endpoint'i sadece devre dışı bırak."},
    {"input": "bug'ı kapat, yok önce reproduce et", "output": "Önce bug'ı reproduce et."},
    {"input": "sprint'i bitir, dur önce retrospective yap", "output": "Önce retrospective yap."},

    # ── Self-correction with number/time ─────────────────────────────────
    {"input": "500 kişi katıldı, yani 450", "output": "450 kişi katıldı."},
    {"input": "saat 14'te başlayalım, hayır 15'te", "output": "Saat 15'te başlayalım."},
    {"input": "3 gün sürer, aslında 5 gün", "output": "5 gün sürer."},
    {"input": "10 bin satır kod, yani 8 bin", "output": "8 bin satır kod."},
    {"input": "toplantı 1 saatte biter, hayır 2 saatte", "output": "Toplantı 2 saatte biter."},
    {"input": "versiyon 1.2, hayır 1.3", "output": "Versiyon 1.3."},
    {"input": "10 bug kaldı, ee 7 bug", "output": "7 bug kaldı."},
    {"input": "pazartesi teslim et, hayır çarşamba", "output": "Çarşamba teslim et."},
    {"input": "yüzde 80 hazır, aslında 70", "output": "Yüzde 70 hazır."},
    {"input": "5 kişilik ekip, yani 6 kişi", "output": "6 kişilik ekip."},

    # ── English backtracking ──────────────────────────────────────────────
    {"input": "open the report, no wait, the other report", "output": "Open the other report."},
    {"input": "let's merge it, actually let's squash first", "output": "Let's squash first."},
    {"input": "delete the file, no wait, move it", "output": "Move the file."},
    {"input": "at 3pm, I mean 4pm", "output": "At 4pm."},
    {"input": "restart the service, hold on, check logs first", "output": "Check logs first."},
    {"input": "close the PR, actually get a review first", "output": "Get a review first."},
    {"input": "deploy to prod, no no, staging first", "output": "Deploy to staging first."},
    {"input": "rollback, actually let's just hotfix", "output": "Let's just hotfix."},
    {"input": "ping Ahmed, no Ali", "output": "Ping Ali."},
    {"input": "cancel the meeting, no postpone it", "output": "Postpone the meeting."},

    # ── Thinking aloud → final decision ──────────────────────────────────
    {"input": "Yani şey bir dakika, tamam, şu PR'a bakalım", "output": "Şu PR'a bakalım."},
    {"input": "Ee hm, tamam, database bağlantısını kontrol et", "output": "Database bağlantısını kontrol et."},
    {"input": "Şey yani, hm, önce testleri geçirelim", "output": "Önce testleri geçirelim."},
    {"input": "Hani ee, tamam tamam, şu servisi yeniden başlat", "output": "Şu servisi yeniden başlat."},
    {"input": "İşte yani, hm, migration'ı çalıştır", "output": "Migration'ı çalıştır."},
    {"input": "Ee yani, hm, bunu staging'e al", "output": "Bunu staging'e al."},
    {"input": "Şey hani, tamam, PR'ı onayla", "output": "PR'ı onayla."},
    {"input": "Yani, hm, ee, API key'i değiştir", "output": "API key'i değiştir."},
    {"input": "Hani işte, tamam, indexleri yeniden oluştur", "output": "Indexleri yeniden oluştur."},
    {"input": "Şey ee, yani, cache'i temizle", "output": "Cache'i temizle."},

    # ── Backtrack + thinking aloud ────────────────────────────────────────
    {"input": "Yani, şu branch'e geç, ee, dur dur, master'a geç", "output": "Master'a geç."},
    {"input": "Ee, bunu kaydet, hm, bekle önce test et", "output": "Bunu önce test et."},
    {"input": "Şey, API'yi güncelle, hm, hayır rollback yap", "output": "API'yi rollback yap."},
    {"input": "Yani, Ahmed'e yaz, ee, yok Ali'ye yaz", "output": "Ali'ye yaz."},
    {"input": "Hani, şu kodu sil, hm, aslında taşı", "output": "Şu kodu taşı."},
    {"input": "Tamam, deployment'ı durdur, ee, hayır devam et", "output": "Deployment'a devam et."},
    {"input": "İşte, log'ları temizle, hm, dur önce incele", "output": "Log'ları önce incele."},
    {"input": "Ee, merge et, yani, bekle conflict'leri çöz önce", "output": "Önce conflict'leri çöz."},
    {"input": "Yani şey, paketi yükle, hm, önce requirements güncelle", "output": "Önce requirements güncelle."},
    {"input": "Şey, sprint'i bitir, ee, dur önce retrospective yap", "output": "Önce retrospective yap."},

    # ── Complex multi-sentence with backtrack ─────────────────────────────
    {"input": "Yani, tamam, yani şuna bakalım, nasıl çalışacak? Görelim, bakalım. Yani. Tamam, şimdi bakalım, nasıl olacak? İşte şimdi, tamam.", "output": "Şuna bakalım, nasıl çalışacak? Görelim. Şimdi bakalım, nasıl olacak?"},
    {"input": "Ee, tamam, şu servisi başlatalım. Yani. Ee. Tamam tamam, aslında önce log'lara bakalım.", "output": "Önce log'lara bakalım."},
    {"input": "Yani şey, bunu deploy edelim. Hm. Bekle bekle. Şey, önce staging'i test edelim.", "output": "Önce staging'i test edelim."},
    {"input": "Tamam, hani, şu bug'ı kapat. Ee yani. Dur dur. İşte, önce reproduce edelim.", "output": "Önce bug'ı reproduce edelim."},
    {"input": "Şey, yani, migration çalıştır. Ee. Bekle. Hani, önce backup al.", "output": "Önce backup al."},
]


def main():
    out_path = pathlib.Path(__file__).parent.parent / "data" / "filler_backtrack.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for item in DATA:
            f.write(json.dumps({"input": item["input"], "output": item["output"]}, ensure_ascii=False) + "\n")
    print(f"filler_backtrack.jsonl — {len(DATA)} examples written to {out_path}")


if __name__ == "__main__":
    main()
