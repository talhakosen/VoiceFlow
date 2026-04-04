"""generate_filler_data.py — Türkçe filler/disfluency pair'lerini API'siz üretir.

Doğrudan gömülü veri + şablon kombinasyonu — ANTHROPIC_API_KEY gerekmez.

Usage:
  python generate_filler_data.py --output ../data/filler_pairs.jsonl
"""

import argparse
import json
import random
from pathlib import Path

random.seed(42)

# ---------------------------------------------------------------------------
# FILLER EASY — cümle başı/sonu tek filler
# ---------------------------------------------------------------------------

FILLER_EASY = [
    # (input, output)
    ("Şey, toplantı yarın saat üçte.", "Toplantı yarın saat üçte."),
    ("Yani, bu raporu bugün bitirmem gerekiyor.", "Bu raporu bugün bitirmem gerekiyor."),
    ("Hani, projeyi cuma gününe kadar teslim etmeliyiz.", "Projeyi cuma gününe kadar teslim etmeliyiz."),
    ("İşte, bütçe onaylandı.", "Bütçe onaylandı."),
    ("Ee, müşteri memnun kalmış.", "Müşteri memnun kalmış."),
    ("Aa, Ahmet bugün gelmeyecek.", "Ahmet bugün gelmeyecek."),
    ("Bugün markete gideceğim yani.", "Bugün markete gideceğim."),
    ("Raporu Mehmet'e gönderdim işte.", "Raporu Mehmet'e gönderdim."),
    ("Yarın İstanbul'a uçuyorum hani.", "Yarın İstanbul'a uçuyorum."),
    ("Şey, kodu push ettim.", "Kodu push ettim."),
    ("Ee, deploy başarılı oldu.", "Deploy başarılı oldu."),
    ("Yani, veritabanı bağlantısı çalışıyor.", "Veritabanı bağlantısı çalışıyor."),
    ("İşte, testler geçti.", "Testler geçti."),
    ("Hani, API endpoint'i güncellendi.", "API endpoint'i güncellendi."),
    ("Aa, bu bug düzeltildi.", "Bu bug düzeltildi."),
    ("Şey, müdürle görüşmem var.", "Müdürle görüşmem var."),
    ("Yani, sabah on birde ofise geleceğim.", "Sabah on birde ofise geleceğim."),
    ("Sunumu tamamladım işte.", "Sunumu tamamladım."),
    ("Hani, sözleşme imzalandı.", "Sözleşme imzalandı."),
    ("Ee, proje onaylandı.", "Proje onaylandı."),
    ("Şey, bu özelliği eklemem lazım.", "Bu özelliği eklemem lazım."),
    ("Yani, server yeniden başlatıldı.", "Server yeniden başlatıldı."),
    ("İşte, log dosyasını inceledim.", "Log dosyasını inceledim."),
    ("Hani, kullanıcı şikayeti geldi.", "Kullanıcı şikayeti geldi."),
    ("Aa, para transferi tamamlandı.", "Para transferi tamamlandı."),
    ("Şey, ofiste kimse yok.", "Ofiste kimse yok."),
    ("Ee, tatil onaylandı.", "Tatil onaylandı."),
    ("Bugün erken çıkacağım yani.", "Bugün erken çıkacağım."),
    ("Hani, sistem güncellemesi yapıldı.", "Sistem güncellemesi yapıldı."),
    ("Yani, ekip toplantısı iptal edildi.", "Ekip toplantısı iptal edildi."),
    ("Şey, bu branch'i merge etmem lazım.", "Bu branch'i merge etmem lazım."),
    ("İşte, code review tamamlandı.", "Code review tamamlandı."),
    ("Ee, uygulama çöktü.", "Uygulama çöktü."),
    ("Hani, backup alındı.", "Backup alındı."),
    ("Aa, yeni özellik canlıya alındı.", "Yeni özellik canlıya alındı."),
    ("Şey, müşteri toplantısı ertelendi.", "Müşteri toplantısı ertelendi."),
    ("Yani, haftalık özet gönderildi.", "Haftalık özet gönderildi."),
    ("Raporu revize ettim işte.", "Raporu revize ettim."),
    ("Hani, yeni çalışan işe başladı.", "Yeni çalışan işe başladı."),
    ("Ee, bütçe aşıldı.", "Bütçe aşıldı."),
    ("Şey, akşam yemeği rezervasyonu yaptım.", "Akşam yemeği rezervasyonu yaptım."),
    ("Yani, uçak bileti aldım.", "Uçak bileti aldım."),
    ("İşte, otel rezervasyonu tamam.", "Otel rezervasyonu tamam."),
    ("Hani, pasaportum doldu.", "Pasaportum doldu."),
    ("Aa, vize başvurusu onaylandı.", "Vize başvurusu onaylandı."),
    ("Şey, fatura ödendi.", "Fatura ödendi."),
    ("Ee, sigorta yenilendi.", "Sigorta yenilendi."),
    ("Yani, randevuyu iptal ettim.", "Randevuyu iptal ettim."),
    ("Arabayı servise verdim hani.", "Arabayı servise verdim."),
    ("İşte, doktor raporu hazır.", "Doktor raporu hazır."),
    ("Şey, bu haftaki strateji toplantısına hazırlanmam gerekiyor.", "Bu haftaki strateji toplantısına hazırlanmam gerekiyor."),
    ("Yani, yeni ofis düzenlemesi yapıldı.", "Yeni ofis düzenlemesi yapıldı."),
    ("Ee, takım lideri değişti.", "Takım lideri değişti."),
    ("Hani, performans değerlendirmeleri başladı.", "Performans değerlendirmeleri başladı."),
    ("Aa, şirket pikniği iptal oldu.", "Şirket pikniği iptal oldu."),
    ("Şey, migration script'ini çalıştırdım.", "Migration script'ini çalıştırdım."),
    ("Yani, cache temizlendi.", "Cache temizlendi."),
    ("İşte, monitoring alarmı kapandı.", "Monitoring alarmı kapandı."),
    ("Hani, SSL sertifikası yenilendi.", "SSL sertifikası yenilendi."),
    ("Ee, production'a deploy ettim.", "Production'a deploy ettim."),
    ("Şey, sprint retrospektifi yarın.", "Sprint retrospektifi yarın."),
    ("Yani, backlog grooming yapıldı.", "Backlog grooming yapıldı."),
    ("İşte, user story tamamlandı.", "User story tamamlandı."),
    ("Hani, acceptance criteria karşılandı.", "Acceptance criteria karşılandı."),
    ("Aa, QA testi geçti.", "QA testi geçti."),
    ("Şey, müşteriye demo yaptım.", "Müşteriye demo yaptım."),
    ("Ee, feedback olumlu geldi.", "Feedback olumlu geldi."),
    ("Yani, sözleşme uzatıldı.", "Sözleşme uzatıldı."),
    ("Hani, ödeme gecikti.", "Ödeme gecikti."),
    ("İşte, fiyat teklifi hazırlandı.", "Fiyat teklifi hazırlandı."),
    ("Şey, şifrem değişti.", "Şifrem değişti."),
    ("Yani, VPN bağlantısı kesildi.", "VPN bağlantısı kesildi."),
    ("Ee, izin başvurusu onaylandı.", "İzin başvurusu onaylandı."),
    ("Hani, toplantı odası rezervasyonu yaptım.", "Toplantı odası rezervasyonu yaptım."),
    ("Aa, ofis malzemeleri bitti.", "Ofis malzemeleri bitti."),
    ("Şey, bu tasarımı beğenmedim.", "Bu tasarımı beğenmedim."),
    ("Yani, renk paleti değiştirildi.", "Renk paleti değiştirildi."),
    ("İşte, mobil versiyon tamamlandı.", "Mobil versiyon tamamlandı."),
    ("Hani, dark mode eklendi.", "Dark mode eklendi."),
    ("Ee, animasyon düzeltildi.", "Animasyon düzeltildi."),
    ("Şey, font güncellendi.", "Font güncellendi."),
    ("Yani, ikonlar değiştirildi.", "İkonlar değiştirildi."),
    ("İşte, loading ekranı iyileştirildi.", "Loading ekranı iyileştirildi."),
    ("Hani, hata sayfası güncellendi.", "Hata sayfası güncellendi."),
    ("Aa, onboarding akışı yenilendi.", "Onboarding akışı yenilendi."),
    ("Şey, bu PR'ı merge edebilirsin.", "Bu PR'ı merge edebilirsin."),
    ("Yani, conflict çözüldü.", "Conflict çözüldü."),
    ("Ee, rebase tamamlandı.", "Rebase tamamlandı."),
    ("Hani, tag oluşturuldu.", "Tag oluşturuldu."),
    ("İşte, release notları hazır.", "Release notları hazır."),
    ("Şey, CHANGELOG güncellendi.", "CHANGELOG güncellendi."),
    ("Yani, versiyon yükseltildi.", "Versiyon yükseltildi."),
    ("Ee, hotfix deploy edildi.", "Hotfix deploy edildi."),
    ("Hani, incident kapandı.", "Incident kapandı."),
    ("Aa, postmortem raporu yazıldı.", "Postmortem raporu yazıldı."),
    ("Şey, dokümanlar güncellendi.", "Dokümanlar güncellendi."),
    ("Yani, wiki sayfası oluşturuldu.", "Wiki sayfası oluşturuldu."),
    ("İşte, eğitim materyali hazırlandı.", "Eğitim materyali hazırlandı."),
    ("Hani, onboarding dokümanı tamamlandı.", "Onboarding dokümanı tamamlandı."),
    ("Ee, teknik borç listesi güncellendi.", "Teknik borç listesi güncellendi."),
]

# ---------------------------------------------------------------------------
# FILLER MEDIUM — cümle ortası veya çoklu filler
# ---------------------------------------------------------------------------

FILLER_MEDIUM = [
    ("Bu projeyi, şey, önümüzdeki haftaya kadar teslim etmem gerekiyor.", "Bu projeyi önümüzdeki haftaya kadar teslim etmem gerekiyor."),
    ("Müdüre, ee, mail attım ama cevap gelmedi.", "Müdüre mail attım ama cevap gelmedi."),
    ("Yani şey, bu sistemi düzeltmemiz lazım.", "Bu sistemi düzeltmemiz lazım."),
    ("Toplantıda, hani, yeni strateji açıklandı.", "Toplantıda yeni strateji açıklandı."),
    ("Bu kodu, şey, refactor etmemiz gerekiyor.", "Bu kodu refactor etmemiz gerekiyor."),
    ("Raporun, yani, ikinci bölümünü yazmadım.", "Raporun ikinci bölümünü yazmadım."),
    ("Sunumu, ee, beş dakikada hazırladım.", "Sunumu beş dakikada hazırladım."),
    ("Müşteriyle, şey, görüşmemiz iyi geçti.", "Müşteriyle görüşmemiz iyi geçti."),
    ("Şey yani, bu özelliği eklemek zaman alacak.", "Bu özelliği eklemek zaman alacak."),
    ("Hani ee, sunucu yanıt vermiyor.", "Sunucu yanıt vermiyor."),
    ("Bu database, şey, çok yavaş çalışıyor.", "Bu database çok yavaş çalışıyor."),
    ("API'yi, yani, güncellememiz lazım.", "API'yi güncellememiz lazım."),
    ("Testi, ee, geçemedik.", "Testi geçemedik."),
    ("Performans, hani, düşmüş.", "Performans düşmüş."),
    ("Deployment, şey, başarısız oldu.", "Deployment başarısız oldu."),
    ("Kod incelemesinde, yani, iki sorun bulduk.", "Kod incelemesinde iki sorun bulduk."),
    ("Yani şey ee, bu mimari karar doğru değil.", "Bu mimari karar doğru değil."),
    ("Hani, şey, müşteri şikayeti var.", "Müşteri şikayeti var."),
    ("Bütçe, ee, yetmeyebilir.", "Bütçe yetmeyebilir."),
    ("Proje, yani, geride kaldı.", "Proje geride kaldı."),
    ("İş gereksinimi, şey, değişti.", "İş gereksinimi değişti."),
    ("Ekip toplantısı, ee, uzadı.", "Ekip toplantısı uzadı."),
    ("Yeni çalışan, hani, adapte olmakta zorlanıyor.", "Yeni çalışan adapte olmakta zorlanıyor."),
    ("Sprint hedefi, şey, tamamlanamadı.", "Sprint hedefi tamamlanamadı."),
    ("Yani, bug production'da, şey, ortaya çıktı.", "Bug production'da ortaya çıktı."),
    ("Ee şey, kullanıcı arayüzü, hani, kafa karıştırıcı.", "Kullanıcı arayüzü kafa karıştırıcı."),
    ("Bu değişiklik, yani, geri alınmalı.", "Bu değişiklik geri alınmalı."),
    ("Hata mesajı, şey, anlaşılmaz.", "Hata mesajı anlaşılmaz."),
    ("Dokümantasyon, ee, eksik.", "Dokümantasyon eksik."),
    ("Güvenlik açığı, hani, kapatıldı.", "Güvenlik açığı kapatıldı."),
    ("Yani şey, bu toplantıya gitmen gerekiyor.", "Bu toplantıya gitmen gerekiyor."),
    ("Müşteriyle, ee, anlaşma sağlandı.", "Müşteriyle anlaşma sağlandı."),
    ("Fatura, şey, hala ödenmedi.", "Fatura hala ödenmedi."),
    ("Teklif, yani, kabul edildi.", "Teklif kabul edildi."),
    ("Projeye, ee, ek kaynak aktarıldı.", "Projeye ek kaynak aktarıldı."),
    ("Bu özelliği, şey, kullanıcılar seviyor.", "Bu özelliği kullanıcılar seviyor."),
    ("Hani yani, mobil uygulama çok yavaş.", "Mobil uygulama çok yavaş."),
    ("Server, ee, fazla bellek kullanıyor.", "Server fazla bellek kullanıyor."),
    ("Sorgu, şey, optimize edilmeli.", "Sorgu optimize edilmeli."),
    ("Index, yani, eksik.", "Index eksik."),
    ("Cache, ee, süresi dolmuş.", "Cache süresi dolmuş."),
    ("Hani şey, bu endpoint çok yavaş.", "Bu endpoint çok yavaş."),
    ("Timeout, yani, çok kısa ayarlanmış.", "Timeout çok kısa ayarlanmış."),
    ("Rate limit, ee, aşıldı.", "Rate limit aşıldı."),
    ("Token, şey, geçersiz.", "Token geçersiz."),
    ("Yani hani, oturum açma sorunu var.", "Oturum açma sorunu var."),
    ("Şifre, ee, sıfırlandı.", "Şifre sıfırlandı."),
    ("İki faktörlü doğrulama, şey, etkinleştirildi.", "İki faktörlü doğrulama etkinleştirildi."),
    ("Yetki, yani, düzenlendi.", "Yetki düzenlendi."),
    ("Kullanıcı rolü, ee, güncellendi.", "Kullanıcı rolü güncellendi."),
    ("Veri tabanı, şey hani, yedeklendi.", "Veri tabanı yedeklendi."),
    ("Sunucu, yani şey, yeniden başlatıldı.", "Sunucu yeniden başlatıldı."),
    ("Disk alanı, ee, dolmuş.", "Disk alanı dolmuş."),
    ("Bellek kullanımı, şey, yüksek.", "Bellek kullanımı yüksek."),
    ("İşlemci, hani, aşırı yüklendi.", "İşlemci aşırı yüklendi."),
    ("Ağ gecikmesi, ee yani, artmış.", "Ağ gecikmesi artmış."),
    ("Paket kaybı, şey, tespit edildi.", "Paket kaybı tespit edildi."),
    ("Güvenlik duvarı, yani, güncellendi.", "Güvenlik duvarı güncellendi."),
    ("VPN, ee, bağlantı kesiliyor.", "VPN bağlantı kesiliyor."),
    ("DNS, hani şey, yanlış çözümlüyor.", "DNS yanlış çözümlüyor."),
    ("SSL sertifikası, yani, yakında dolacak.", "SSL sertifikası yakında dolacak."),
    ("Load balancer, ee, yanlış yönlendiriyor.", "Load balancer yanlış yönlendiriyor."),
    ("Yani şey hani, bu mimariyi yeniden tasarlamamız lazım.", "Bu mimariyi yeniden tasarlamamız lazım."),
    ("Microservice, ee, birbirleriyle konuşmuyor.", "Microservice'ler birbirleriyle konuşmuyor."),
    ("Message queue, şey, tıkandı.", "Message queue tıkandı."),
    ("Event stream, yani, işlenemiyor.", "Event stream işlenemiyor."),
    ("Retry mekanizması, ee, düzgün çalışmıyor.", "Retry mekanizması düzgün çalışmıyor."),
    ("Circuit breaker, hani, açık kalmış.", "Circuit breaker açık kalmış."),
    ("Fallback, şey yani, devreye girmiyor.", "Fallback devreye girmiyor."),
    ("Health check, ee, başarısız.", "Health check başarısız."),
    ("Metrik, hani, toplanmıyor.", "Metrik toplanmıyor."),
    ("Log, şey, yazılmıyor.", "Log yazılmıyor."),
    ("Alert, yani, yanlış tetiklendi.", "Alert yanlış tetiklendi."),
    ("Dashboard, ee şey, güncel değil.", "Dashboard güncel değil."),
    ("Rapor, hani, eksik veri içeriyor.", "Rapor eksik veri içeriyor."),
    ("Analiz, yani, tamamlanmadı.", "Analiz tamamlanmadı."),
    ("Proje planı, ee, güncellendi.", "Proje planı güncellendi."),
    ("Kaynak tahsisi, şey, değişti.", "Kaynak tahsisi değişti."),
    ("Risk değerlendirmesi, hani yani, yapıldı.", "Risk değerlendirmesi yapıldı."),
    ("Paydaş görüşmesi, ee, tamamlandı.", "Paydaş görüşmesi tamamlandı."),
    ("Gereksinim belgesi, şey, onaylandı.", "Gereksinim belgesi onaylandı."),
    ("Test planı, yani, hazırlandı.", "Test planı hazırlandı."),
    ("Kabul kriterleri, ee, belirlendi.", "Kabul kriterleri belirlendi."),
    ("Çıktı, şey hani, beklenenden farklı.", "Çıktı beklenenden farklı."),
    ("Regresyon testi, yani, geçti.", "Regresyon testi geçti."),
    ("Performans testi, ee, başarısız.", "Performans testi başarısız."),
    ("Yük testi, hani, yapıldı.", "Yük testi yapıldı."),
    ("Güvenlik taraması, şey, tamamlandı.", "Güvenlik taraması tamamlandı."),
    ("Kod kalitesi, yani ee, düşük.", "Kod kalitesi düşük."),
    ("Teknik borç, hani, artıyor.", "Teknik borç artıyor."),
    ("Refactoring, şey, planlandı.", "Refactoring planlandı."),
    ("Versiyon güncellemesi, yani, gerekiyor.", "Versiyon güncellemesi gerekiyor."),
    ("Kütüphane, ee şey, eskimiş.", "Kütüphane eskimiş."),
    ("Bağımlılık, hani, çakışıyor.", "Bağımlılık çakışıyor."),
    ("Build, yani, hata veriyor.", "Build hata veriyor."),
    ("CI/CD, ee, konfigüre edildi.", "CI/CD konfigüre edildi."),
    ("Pipeline, şey hani, optimize edildi.", "Pipeline optimize edildi."),
]

# ---------------------------------------------------------------------------
# FILLER HARD — yapı bozucu filler'lar, yeniden düzenleme gerekiyor
# ---------------------------------------------------------------------------

FILLER_HARD = [
    ("Yani şey hani bu kodu şey ee refactor etmemiz yani çok önemli aslında.", "Bu kodu refactor etmemiz çok önemli."),
    ("Ee şey yani toplantıda şey dediler ki hani bütçe şey kesilecekmiş yani.", "Toplantıda bütçenin kesileceğini söylediler."),
    ("Şey şey şey nasıl desem yani bu kişiyle çalışmak hani zor oluyor işte.", "Bu kişiyle çalışmak zor oluyor."),
    ("Yani hani şey bu fonksiyon şey çalışmıyor ee düzeltmem lazım işte.", "Bu fonksiyon çalışmıyor, düzeltmem lazım."),
    ("Şey ee yani proje hani bitti mi bitmedi mi şey anlayamadım.", "Projenin bitip bitmediğini anlayamadım."),
    ("Hani yani şey müşteriyle ee konuştum şey ama anlaşamadık işte yani.", "Müşteriyle konuştum ama anlaşamadık."),
    ("Ee şey yani bu raporu hani şey kim yazacak yani bilmiyorum işte.", "Bu raporu kimin yazacağını bilmiyorum."),
    ("Yani yani şey hani toplantı ee ertelendi mi iptal mi oldu şey anlayamadım.", "Toplantının ertelenip ertelenmediğini anlayamadım."),
    ("Şey hani ee bu değişiklik yani sistemi şey etkiledi mi etkilemedi mi.", "Bu değişikliğin sistemi etkileyip etkilemediği belli değil."),
    ("Hani şey yani server şey ee down oldu mu yoksa şey performans mı düştü.", "Server'ın down olup olmadığı yoksa performansın mı düştüğü belli değil."),
    ("Yani şey ee bu özelliği hani ekleyecektik şey ama yetişmedi işte.", "Bu özelliği ekleyecektik ama yetişmedi."),
    ("Şey ee hani kullanıcılar yani şu şey hatayı alıyorlar ama yani ne zaman bilmiyorum.", "Kullanıcılar bu hatayı alıyorlar ama ne zaman bilmiyorum."),
    ("Hani yani ee şey bu dokümana şey bakmam lazım yani ama zamanım yok işte.", "Bu dokümana bakmam lazım ama zamanım yok."),
    ("Şey yani hani ee bu sprint'te şey ne yaptık tam olarak şey bilmiyorum.", "Bu sprint'te tam olarak ne yaptığımızı bilmiyorum."),
    ("Ee hani şey yani deadline şey geçti mi geçmedi mi yani kontrol etmedim.", "Deadline'ın geçip geçmediğini kontrol etmedim."),
    ("Yani şey şey hani ee bu API şey dokümante edildi mi şey bilmiyorum işte.", "Bu API'nin dokümante edilip edilmediğini bilmiyorum."),
    ("Şey hani ee yani deployment şey başarılı mı oldu şey kontrol ettim mi etmedim mi.", "Deployment'ın başarılı olup olmadığını kontrol etmedim."),
    ("Hani şey yani ee bu test senaryosu şey kapsıyor mu kapsamıyor mu yani bilmiyorum.", "Bu test senaryosunun yeterli kapsamı olup olmadığını bilmiyorum."),
    ("Ee yani şey hani kullanıcı arayüzü şey beğenildi mi beğenilmedi mi yani.", "Kullanıcı arayüzünün beğenilip beğenilmediği belli değil."),
    ("Şey ee yani hani bu değişikliği yapmak şey ne kadar sürer yani bilmiyorum işte.", "Bu değişikliği yapmanın ne kadar süreceğini bilmiyorum."),
    ("Yani şey hani ee bütçe şey yetecek mi yetmeyecek mi şey hesaplamadım.", "Bütçenin yetip yetmeyeceğini hesaplamadım."),
    ("Şey hani ee yani ekip şey bu kadar işi yapabilir mi yapamaz mı bilmiyorum.", "Ekibin bu kadar işi yapıp yapamayacağını bilmiyorum."),
    ("Hani şey yani ee yeni sistem şey eski sistemle uyumlu mu değil mi şey test etmedik.", "Yeni sistemin eski sistemle uyumlu olup olmadığını test etmedik."),
    ("Ee şey hani yani müşteri şey onayladı mı onaylamadı mı şey sormadım.", "Müşterinin onaylayıp onaylamadığını sormadım."),
    ("Şey yani hani ee bu özellik şey kullanıcılara gösterildi mi şey bilmiyorum yani.", "Bu özelliğin kullanıcılara gösterilip gösterilmediğini bilmiyorum."),
    ("Yani ee şey hani kod şey review'dan geçti mi geçmedi mi şey kontrol etmem lazım.", "Kodun review'dan geçip geçmediğini kontrol etmem lazım."),
    ("Şey şey hani yani ee bu ticket şey kapatıldı mı açık mı yani bakamadım.", "Bu ticket'ın kapatılıp kapatılmadığına bakamadım."),
    ("Hani ee yani şey bu konfigürasyon şey doğru mu yanlış mı yani anlamadım.", "Bu konfigürasyonun doğru olup olmadığını anlamadım."),
    ("Ee yani şey hani proje şey zamanında bitecek mi bitmeyecek mi şey belli değil.", "Projenin zamanında bitip bitmeyeceği belli değil."),
    ("Yani hani şey ee bu öneri şey kabul edildi mi reddedildi mi şey sormadım işte.", "Bu önerinin kabul edilip edilmediğini sormadım."),
    ("Şey ee hani yani sistem şey bu yükü kaldırabilir mi kaldıramaz mı bilmiyorum.", "Sistemin bu yükü kaldırıp kaldıramayacağını bilmiyorum."),
    ("Hani şey yani ee eski kod şey hala çalışıyor mu çalışmıyor mu şey test etmedik.", "Eski kodun hala çalışıp çalışmadığını test etmedik."),
    ("Ee yani şey hani bu özelliği şey kaldırabilir miyiz kaldıramaz mıyız tartışmamız lazım.", "Bu özelliği kaldırıp kaldıramayacağımızı tartışmamız lazım."),
    ("Şey hani ee yani loglarda şey herhangi bir hata var mı yok mu şey bakmadım.", "Loglarda herhangi bir hata olup olmadığına bakmadım."),
    ("Yani şey ee hani bu endpoint şey rate limit'e takılıyor mu takılmıyor mu şey bilmiyorum.", "Bu endpoint'in rate limit'e takılıp takılmadığını bilmiyorum."),
    ("Hani ee şey yani kullanıcı verisi şey doğru işleniyor mu işlenmiyor mu test etmedik.", "Kullanıcı verisinin doğru işlenip işlenmediğini test etmedik."),
    ("Şey yani hani ee yetkilendirme şey düzgün çalışıyor mu çalışmıyor mu şey anlamadım.", "Yetkilendirmenin düzgün çalışıp çalışmadığını anlamadım."),
    ("Ee hani şey yani bu yazı şey doğru anlaşılıyor mu anlaşılmıyor mu şey göstermedik.", "Bu yazının doğru anlaşılıp anlaşılmadığını test etmedik."),
    ("Yani ee hani şey mobil uygulama şey yavaş mı değil mi şey ölçmedik.", "Mobil uygulamanın yavaş olup olmadığını ölçmedik."),
    ("Şey şey yani hani ee bu önbellek şey ne kadar süre geçerli olmalı yani bilmiyorum.", "Bu önbelleğin ne kadar süre geçerli olması gerektiğini bilmiyorum."),
    ("Hani ee yani şey hangi kütüphane şey daha iyi olur yani araştırmadım.", "Hangi kütüphanenin daha iyi olacağını araştırmadım."),
    ("Ee şey hani yani dosya boyutu şey çok büyük mü değil mi şey kontrol etmedim.", "Dosya boyutunun çok büyük olup olmadığını kontrol etmedim."),
    ("Şey yani hani ee bu entegrasyon şey ne zaman hazır olur yani söyleyemem.", "Bu entegrasyonun ne zaman hazır olacağını söyleyemem."),
    ("Yani şey ee hani proje gereksinimleri şey net mi değil mi şey tartışmamız lazım.", "Proje gereksinimlerinin net olup olmadığını tartışmamız lazım."),
    ("Hani şey ee yani bu kod şey okunabilir mi okunabilir değil mi şey incelememiz lazım.", "Bu kodun okunabilir olup olmadığını incelememiz lazım."),
    ("Ee yani hani şey bu toplantı şey verimli miydi verimsiz miydi yani sormadım.", "Bu toplantının verimli olup olmadığını sormadım."),
    ("Şey ee şey hani yani dokümantasyon şey güncel mi değil mi şey bilmiyorum.", "Dokümantasyonun güncel olup olmadığını bilmiyorum."),
    ("Yani hani ee şey bu sorun şey tekrar oluşur mu oluşmaz mı yani izliyoruz.", "Bu sorunun tekrar oluşup oluşmayacağını izliyoruz."),
    ("Hani şey yani ee değişiklik şey geri alındı mı alınmadı mı şey kontrol etmem lazım.", "Değişikliğin geri alınıp alınmadığını kontrol etmem lazım."),
    ("Ee şey hani yani bu süreç şey iyileştirilebilir mi iyileştirilemez mi tartışabiliriz.", "Bu sürecin iyileştirilip iyileştirilemeyeceğini tartışabiliriz."),
    ("Şey yani hani ee teknik borç şey ne zaman azalacak yani planlamadık.", "Teknik borcun ne zaman azalacağını planlamadık."),
    ("Yani ee şey hani bu sistem şey ölçeklenebilir mi değil mi şey test etmedik.", "Bu sistemin ölçeklenebilir olup olmadığını test etmedik."),
    ("Hani yani ee şey ekip şey bu değişime hazır mı değil mi şey bilmiyorum.", "Ekibin bu değişime hazır olup olmadığını bilmiyorum."),
    ("Ee şey yani hani kullanıcılar şey bu özelliği kullanıyor mu kullanmıyor mu analitik baktım.", "Kullanıcıların bu özelliği kullanıp kullanmadığına analitikten baktım."),
    ("Şey hani yani ee sonuç şey beklentileri karşıladı mı karşılamadı mı değerlendirmedik.", "Sonucun beklentileri karşılayıp karşılamadığını değerlendirmedik."),
]

# ---------------------------------------------------------------------------
# SEMANTIC YANI — anlam taşıyan yani korunur
# ---------------------------------------------------------------------------

SEMANTIC_YANI = [
    # yani = dolgu → kaldır
    ("Toplantıya gidemeyeceğim, yani, hastalandım.", "Toplantıya gidemeyeceğim; hastalandım."),
    ("Şey yani, bunu yapamam.", "Bunu yapamam."),
    ("Hani yani, saat altıda çıkalım.", "Saat altıda çıkalım."),
    ("Ee yani, bitirdim.", "Bitirdim."),
    ("Yani şey, anlattım sana.", "Anlattım sana."),

    # yani = "demek ki / şu anlama geliyor" → koru
    ("Proje bitti, yani artık deploy edebiliriz.", "Proje bitti, yani artık deploy edebiliriz."),
    ("Test geçti, yani kod doğru çalışıyor.", "Test geçti, yani kod doğru çalışıyor."),
    ("Bütçe tükendi, yani proje durdu.", "Bütçe tükendi, yani proje durdu."),
    ("Müşteri onayladı, yani üretim başlayabilir.", "Müşteri onayladı, yani üretim başlayabilir."),
    ("Sertifika doldu, yani site erişilemez.", "Sertifika doldu, yani site erişilemez."),
    ("Sunucu doldu, yani yeni dosya yükleyemiyoruz.", "Sunucu doldu, yani yeni dosya yükleyemiyoruz."),
    ("Güvenlik açığı bulundu, yani acil yama gerekiyor.", "Güvenlik açığı bulundu, yani acil yama gerekiyor."),
    ("Performans düştü, yani kullanıcılar şikayet ediyor.", "Performans düştü, yani kullanıcılar şikayet ediyor."),
    ("Deadline geçti, yani ceza uygulanacak.", "Deadline geçti, yani ceza uygulanacak."),
    ("Kod merge edildi, yani özellik artık canlıda.", "Kod merge edildi, yani özellik artık canlıda."),

    # karışık: ilk yani dolgu, ikinci anlamlı
    ("Yani bu karar yanlış, yani gerçekten düşünmeliyiz.", "Bu karar yanlış, yani gerçekten düşünmeliyiz."),
    ("Şey yani hatalı, yani geri almalıyız.", "Hatalı, yani geri almalıyız."),
    ("Yani şey bu özellik çalışmıyor, yani kullanıcıya gösterme.", "Bu özellik çalışmıyor, yani kullanıcıya gösterme."),
    ("Ee yani bütçe bitti, yani ek kaynak istememiz lazım.", "Bütçe bitti, yani ek kaynak istememiz lazım."),
    ("Hani yani ekip hazır değil, yani tarihi ertelememiz lazım.", "Ekip hazır değil, yani tarihi ertelememiz lazım."),

    # işte dolgu → kaldır
    ("İşte, bu kadar.", "Bu kadar."),
    ("Sorunu çözdüm işte.", "Sorunu çözdüm."),
    ("İşte böyle yapılır.", "Böyle yapılır."),

    # işte = "bakın / işte bu" → koru
    ("İşte bu hatayı düzeltmemiz lazım.", "İşte bu hatayı düzeltmemiz lazım."),
    ("İşte bu yüzden test önemli.", "İşte bu yüzden test önemli."),
    ("İşte sorun burada.", "İşte sorun burada."),
    ("İşte asıl mesele bu.", "İşte asıl mesele bu."),

    # hani dolgu → kaldır
    ("Hani, biliyorsun.", "Biliyorsun."),
    ("Hani şey, dün konuşmuştuk.", "Dün konuşmuştuk."),
    ("Hani ee, toplantıda söyledi.", "Toplantıda söyledi."),

    # hani = "hatırladın mı / o bildiğin" → koru
    ("Hani o kütüphane vardı ya, onu kullanalım.", "Hani o kütüphane vardı ya, onu kullanalım."),
    ("Hani geçen hafta konuştuğumuz sorun, onu çözdüm.", "Hani geçen hafta konuştuğumuz sorun, onu çözdüm."),
    ("Hani o bug vardı ya, kapandı.", "Hani o bug vardı ya, kapandı."),

    # yani complex
    ("Yani şey yani bu çok karmaşık, yani basitleştirmemiz lazım.", "Bu çok karmaşık, yani basitleştirmemiz lazım."),
    ("Hani şey yani ekip yorgun, yani sprint'i hafifletelim.", "Ekip yorgun, yani sprint'i hafifletelim."),
    ("Ee yani şey hani sistem yavaş, yani optimizasyon şart.", "Sistem yavaş, yani optimizasyon şart."),
    ("Yani yani şey bu yaklaşım yanlış, yani baştan düşünelim.", "Bu yaklaşım yanlış, yani baştan düşünelim."),
    ("Şey yani hani ee sonuç beklenenden iyi, yani devam edelim.", "Sonuç beklenenden iyi, yani devam edelim."),
    ("Hani yani ee test başarısız, yani release'i erteleyelim.", "Test başarısız, yani release'i erteleyelim."),
    ("Ee şey yani hani müşteri memnun, yani sözleşme uzatılacak.", "Müşteri memnun, yani sözleşme uzatılacak."),
    ("Yani hani ee şey kaynak yetersiz, yani önceliklendirme yapalım.", "Kaynak yetersiz, yani önceliklendirme yapalım."),
    ("Şey hani yani ee veriler uyuşmuyor, yani veri kalitesi sorunlu.", "Veriler uyuşmuyor, yani veri kalitesi sorunlu."),
    ("Hani ee yani şey plan tutmadı, yani revizyona ihtiyaç var.", "Plan tutmadı, yani revizyona ihtiyaç var."),
    ("Yani şey ee hani eski yöntem işe yaramıyor, yani yeni yaklaşım deneyelim.", "Eski yöntem işe yaramıyor, yani yeni yaklaşım deneyelim."),
    ("Ee hani yani şey takım iyi çalışıyor, yani bu yapıyı koruyalım.", "Takım iyi çalışıyor, yani bu yapıyı koruyalım."),
    ("Şey yani hani ee kod okunabilir değil, yani refactoring lazım.", "Kod okunabilir değil, yani refactoring lazım."),
    ("Hani şey ee yani güvenlik açığı kritik, yani hemen yamalamalıyız.", "Güvenlik açığı kritik, yani hemen yamalamalıyız."),
    ("Yani ee şey hani veri kaybı oldu, yani yedekten geri dönmeliyiz.", "Veri kaybı oldu, yani yedekten geri dönmeliyiz."),
]

# ---------------------------------------------------------------------------
# BACKTRACK — geri alma / kendini düzeltme
# ---------------------------------------------------------------------------

BACKTRACK = [
    ("Toplantı salı günü, hayır dur, çarşamba günü saat ikide.", "Toplantı çarşamba günü saat ikide."),
    ("Bütçe iki yüz bin, pardon, iki yüz elli bin lira olarak belirlendi.", "Bütçe iki yüz elli bin lira olarak belirlendi."),
    ("Ali'ye mail at, yok yok, Mehmet'e at.", "Mehmet'e mail at."),
    ("Bu fonksiyonu sil, dur bir saniye, şöyle diyeyim: bu fonksiyonu refactor et.", "Bu fonksiyonu refactor et."),
    ("Raporu Ayşe yazacak, hayır, Fatma yazacak.", "Raporu Fatma yazacak."),
    ("Sunucu üç gün önce, aslında dört gün önce çöktü.", "Sunucu dört gün önce çöktü."),
    ("Proje yüzde seksen, yok yok, yüzde altmış tamamlandı.", "Proje yüzde altmış tamamlandı."),
    ("Toplantı saat onda, dur, saat on birde başlıyor.", "Toplantı saat on birde başlıyor."),
    ("Kodu Ahmet commit etti, hayır dur, Burak commit etti.", "Kodu Burak commit etti."),
    ("Versiyon iki nokta sıfır, pardon, iki nokta bir yayınlandı.", "Versiyon iki nokta bir yayınlandı."),
    ("Müşteri yarın geliyor, aslında öbür gün geliyor.", "Müşteri öbür gün geliyor."),
    ("Server İstanbul'da, hayır, Ankara'da konumlanıyor.", "Server Ankara'da konumlanıyor."),
    ("Beş kişilik ekip, dur bir dakika, altı kişilik ekip çalışacak.", "Altı kişilik ekip çalışacak."),
    ("Aylık maliyet bin lira, yok yok, iki bin lira.", "Aylık maliyet iki bin lira."),
    ("Proje bitti, hayır dur, test aşamasında.", "Proje test aşamasında."),
    ("Şifreyi sıfırla, dur şöyle diyeyim, şifreyi değiştir ve kullanıcıyı bilgilendir.", "Şifreyi değiştir ve kullanıcıyı bilgilendir."),
    ("On beş gün içinde, aslında yirmi gün içinde teslim ederiz.", "Yirmi gün içinde teslim ederiz."),
    ("Hata frontend'de, pardon, backend'de ortaya çıkıyor.", "Hata backend'de ortaya çıkıyor."),
    ("Üç sprint daha, hayır, iki sprint daha yeter.", "İki sprint daha yeter."),
    ("Kullanıcı sayısı bin, yok yok, iki bin kişiyi geçti.", "Kullanıcı sayısı iki bin kişiyi geçti."),
    ("Bütçeyi Kemal onayladı, dur bir saniye, Kemal değil Hüseyin onayladı.", "Bütçeyi Hüseyin onayladı."),
    ("Test ortamında, hayır dur, production'da hata aldık.", "Production'da hata aldık."),
    ("Python üçle yaz, aslında şöyle diyeyim, Python üç on dörtle yaz.", "Python 3.14 ile yaz."),
    ("Sabah toplantısı, pardon, öğleden sonra toplantısı var.", "Öğleden sonra toplantısı var."),
    ("Dört saat sürdü, hayır, altı saat sürdü.", "Altı saat sürdü."),
    ("Müşteri memnun değil, dur dur, aslında memnun.", "Müşteri memnun."),
    ("Kodu sil, yok yok, şöyle diyeyim, kodu yorum satırına al.", "Kodu yorum satırına al."),
    ("Slack'te yaz, hayır, email at.", "Email at."),
    ("Yarın çalışmıyorum, aslında yarın çalışıyorum.", "Yarın çalışıyorum."),
    ("Üçüncü öncelik, dur bir saniye, birinci öncelik olarak işaretle.", "Birinci öncelik olarak işaretle."),
    ("Sunumda elli slayt var, pardon, otuz slayt var.", "Sunumda otuz slayt var."),
    ("Tüm kullanıcılar etkilendi, hayır dur, sadece premium kullanıcılar etkilendi.", "Sadece premium kullanıcılar etkilendi."),
    ("Kodu main branch'e push et, yok yok, develop branch'e push et.", "Kodu develop branch'e push et."),
    ("Teknik ekip sorumlu, aslında ürün ekibi sorumlu.", "Ürün ekibi sorumlu."),
    ("İki hafta daha, dur şöyle söyleyeyim, bir ay daha zaman lazım.", "Bir ay daha zaman lazım."),
    ("Performans sorununu Mehmet çözecek, hayır, ekibin tamamı çalışacak.", "Performans sorununu ekibin tamamı çalışacak."),
    ("Dış servis çöktü, pardon, dış servis yavaşladı.", "Dış servis yavaşladı."),
    ("Sözleşme iptal edildi, dur dur, sözleşme askıya alındı.", "Sözleşme askıya alındı."),
    ("Veri silindi, hayır dur, veri arşivlendi.", "Veri arşivlendi."),
    ("Güvenlik açığı kritik, aslında orta seviye risk.", "Güvenlik açığı orta seviye risk."),
    ("Toplantıyı iptal et, yok yok, toplantıyı bir saat ertele.", "Toplantıyı bir saat ertele."),
    ("Sistemi kapat, dur bir saniye, sistemi bakım moduna al.", "Sistemi bakım moduna al."),
    ("Müşteriye hayır de, hayır dur, müşteriye alternatif sun.", "Müşteriye alternatif sun."),
    ("Hizmeti durdur, pardon, hizmeti yeniden başlat.", "Hizmeti yeniden başlat."),
    ("Veritabanını sil, yok yok şöyle diyeyim, veritabanını yedekle ve sıfırla.", "Veritabanını yedekle ve sıfırla."),
    ("Kullanıcıyı engelle, hayır, kullanıcının iznini kısıtla.", "Kullanıcının iznini kısıtla."),
    ("Raporu sil, dur, raporu güncelle.", "Raporu güncelle."),
    ("Featureı kapat, aslında öyle demek istemedim, feature'ı gizle.", "Feature'ı gizle."),
    ("Ekibe söyle, hayır dur, sadece takım liderlerine söyle.", "Sadece takım liderlerine söyle."),
    ("Şikayet geldi, pardon, öneri geldi.", "Öneri geldi."),
    ("Proje bütçesi beş milyon, hayır yanlış, iki buçuk milyon.", "Proje bütçesi iki buçuk milyon."),
    ("Ekipte beş kişi var, dur, dört kişi var.", "Ekipte dört kişi var."),
    ("Ürün hazır, aslında hayır, beta aşamasında.", "Ürün beta aşamasında."),
    ("İstanbul ofisinde, dur dur, Ankara ofisinde toplantı var.", "Ankara ofisinde toplantı var."),
    ("Bu hafta bitecek, yok yok, gelecek hafta bitecek.", "Gelecek hafta bitecek."),
    ("On dakika içinde, pardon, yarım saat içinde gelebilirim.", "Yarım saat içinde gelebilirim."),
    ("Versiyon üç yayınlandı, hayır dur, versiyon iki nokta beş yayınlandı.", "Versiyon iki nokta beş yayınlandı."),
    ("Canlıya alındı, dur bir saniye, test ortamına alındı.", "Test ortamına alındı."),
    ("Kullanıcı verileri korunuyor, aslında şöyle diyeyim, kullanıcı verileri şifreleniyor.", "Kullanıcı verileri şifreleniyor."),
    ("Mobil app güncellendi, hayır, web app güncellendi.", "Web app güncellendi."),
    ("Ticket açıldı, pardon, ticket kapatıldı.", "Ticket kapatıldı."),
    ("Hata log'da görünüyor, dur dur, hata uyarı seviyesinde.", "Hata uyarı seviyesinde görünüyor."),
]

# ---------------------------------------------------------------------------
# STUTTER — tekrar ve kekeme
# ---------------------------------------------------------------------------

STUTTER = [
    ("Bu bu fonksiyonu düzeltmem lazım.", "Bu fonksiyonu düzeltmem lazım."),
    ("Top toplantı saat üçte başlıyor.", "Toplantı saat üçte başlıyor."),
    ("Gi-gidecek misin yarın?", "Gidecek misin yarın?"),
    ("Şey şey şey nasıl açıklasam.", "Nasıl açıklasam."),
    ("Bu bu bu raporu yazmam lazım.", "Bu raporu yazmam lazım."),
    ("Pro proje bitti mi?", "Proje bitti mi?"),
    ("Kod kod kodu commit ettim.", "Kodu commit ettim."),
    ("Sunu sunuyu hazırladım.", "Sunuyu hazırladım."),
    ("Mü-müşteri geldi.", "Müşteri geldi."),
    ("Bü-bütçe onaylandı.", "Bütçe onaylandı."),
    ("Sistem sistem sistemi güncelledim.", "Sistemi güncelledim."),
    ("De-deployment başarılı.", "Deployment başarılı."),
    ("Ha-hata düzeltildi.", "Hata düzeltildi."),
    ("Top-toplantıyı erteleyelim.", "Toplantıyı erteleyelim."),
    ("Pro-proje geride kalıyor.", "Proje geride kalıyor."),
    ("Ser-sunucu yeniden başlatıldı.", "Sunucu yeniden başlatıldı."),
    ("API API API cevap vermiyor.", "API cevap vermiyor."),
    ("Veri veri veritabanı bağlantısı kesildi.", "Veritabanı bağlantısı kesildi."),
    ("Bu bu iş bu hafta bitirilmeli.", "Bu iş bu hafta bitirilmeli."),
    ("Test test testler geçti.", "Testler geçti."),
    ("Do-dokümantasyon güncellendi.", "Dokümantasyon güncellendi."),
    ("Kul-kullanıcı şikayeti geldi.", "Kullanıcı şikayeti geldi."),
    ("Pa-paket yüklendi.", "Paket yüklendi."),
    ("İzin izin izni onaylandı.", "İzin onaylandı."),
    ("Bi-bildirim gönderildi.", "Bildirim gönderildi."),
    ("Rapor rapor raporu gönderdim.", "Raporu gönderdim."),
    ("Lo-loglara baktım.", "Loglara baktım."),
    ("Şi-şifre sıfırlandı.", "Şifre sıfırlandı."),
    ("Gü-güvenlik taraması yapıldı.", "Güvenlik taraması yapıldı."),
    ("Bağ-bağlantı kesildi.", "Bağlantı kesildi."),
    ("Ve-veriler yedeklendi.", "Veriler yedeklendi."),
    ("Ka-kaynak tükendi.", "Kaynak tükendi."),
    ("İç-içerik güncellendi.", "İçerik güncellendi."),
    ("Mi-migration tamamlandı.", "Migration tamamlandı."),
    ("Ser-servis durduruldu.", "Servis durduruldu."),
    ("Mo-mobil uygulama çöktü.", "Mobil uygulama çöktü."),
    ("Ha-hafıza sızıntısı tespit edildi.", "Hafıza sızıntısı tespit edildi."),
    ("Ya-yama uygulandı.", "Yama uygulandı."),
    ("Kod kod kodu incele.", "Kodu incele."),
    ("Ca-canlıya aldım.", "Canlıya aldım."),
    ("Bu özelliği bu özelliği kaldıralım.", "Bu özelliği kaldıralım."),
    ("Su-sunumda hata var.", "Sunumda hata var."),
    ("Ta-takım toplantısı ertelendi.", "Takım toplantısı ertelendi."),
    ("Sö-sözleşme imzalandı.", "Sözleşme imzalandı."),
    ("İş iş iş isteği onaylandı.", "İş isteği onaylandı."),
    ("Fe-feature flag açıldı.", "Feature flag açıldı."),
    ("Con-conflict çözüldü.", "Conflict çözüldü."),
    ("Al-alert kapandı.", "Alert kapandı."),
    ("Me-metrik toplanıyor.", "Metrik toplanıyor."),
    ("Da-dashboard güncellendi.", "Dashboard güncellendi."),
    ("Pa-pipeline çalıştı.", "Pipeline çalıştı."),
    ("Bu bu branch silinebilir.", "Bu branch silinebilir."),
    ("Re-release hazır.", "Release hazır."),
    ("Ha-hotfix deploy edildi.", "Hotfix deploy edildi."),
    ("Rol-rollback yapıldı.", "Rollback yapıldı."),
    ("En-endpoint eklendi.", "Endpoint eklendi."),
    ("Par-parametre eksik.", "Parametre eksik."),
    ("Re-response yanlış.", "Response yanlış."),
    ("İs-istek zaman aşımına uğradı.", "İstek zaman aşımına uğradı."),
    ("Kuy-kuyruk doldu.", "Kuyruk doldu."),
    ("Bu bu bu bağımlılık güncellenmeli.", "Bu bağımlılık güncellenmeli."),
]

# ---------------------------------------------------------------------------
# NUMBER — sayı normalizasyonu
# ---------------------------------------------------------------------------

NUMBER = [
    ("İki bin yirmi altı yılında başladı.", "2026 yılında başladı."),
    ("Yüzde seksen beş başarı oranına ulaştık.", "%85 başarı oranına ulaştık."),
    ("Saat on beşte toplantı var.", "Saat 15:00'te toplantı var."),
    ("Üç yüz elli milyon lira bütçe ayrıldı.", "350 milyon lira bütçe ayrıldı."),
    ("Birinci çeyrek sonuçları açıklandı.", "1. çeyrek sonuçları açıklandı."),
    ("İki bin kullanıcıya ulaştık.", "2.000 kullanıcıya ulaştık."),
    ("On iki Mart toplantımız var.", "12 Mart toplantımız var."),
    ("Yüzde doksan beş uptime sağlandı.", "%95 uptime sağlandı."),
    ("Beş yüz milisaniye gecikme var.", "500 ms gecikme var."),
    ("Sabah sekizde başlayalım.", "Sabah 8:00'de başlayalım."),
    ("Dört yüz bin satır kod.", "400.000 satır kod."),
    ("İkinci sürüm yayınlandı.", "2. sürüm yayınlandı."),
    ("On dört Mayıs itibarıyla.", "14 Mayıs itibarıyla."),
    ("Yüzde yirmi performans artışı.", "%20 performans artışı."),
    ("Üç buçuk saat sürdü.", "3,5 saat sürdü."),
    ("Beş bin beş yüz kayıt işlendi.", "5.500 kayıt işlendi."),
    ("Saat yirmide kapanıyor.", "Saat 20:00'de kapanıyor."),
    ("Yirmi yedinci versiyonu çıktı.", "27. versiyonu çıktı."),
    ("Bir milyon aktif kullanıcı.", "1.000.000 aktif kullanıcı."),
    ("Yüzde kırk beş indirimi var.", "%45 indirimi var."),
    ("Altı yüz megabayt dosya.", "600 MB dosya."),
    ("On beş Ocak son tarih.", "15 Ocak son tarih."),
    ("Yüzde yetmiş iki dolu.", "%72 dolu."),
    ("Dört çekirdek işlemci.", "4 çekirdek işlemci."),
    ("Saat on dörtte dönüş.", "Saat 14:00'te dönüş."),
    ("İki gigabayt bellek.", "2 GB bellek."),
    ("Beş yüz istek per saniye.", "500 istek/saniye."),
    ("Otuzuncu gün bildirimi.", "30. gün bildirimi."),
    ("Yüzde elli altı başarı.", "%56 başarı."),
    ("On bir Nisan yarın.", "11 Nisan yarın."),
    ("Bin beş yüz dolar maliyet.", "1.500 dolar maliyet."),
    ("Saat dokuzda standup.", "Saat 9:00'da standup."),
    ("Yüzde doksan güven skoru.", "%90 güven skoru."),
    ("Üçüncü dönem raporu.", "3. dönem raporu."),
    ("Elli gigabayt log dosyası.", "50 GB log dosyası."),
    ("Yüz elli milisaniye timeout.", "150 ms timeout."),
    ("İkinci ayın sonunda.", "2. ayın sonunda."),
    ("Yüzde yirmi beş büyüme.", "%25 büyüme."),
    ("Beş bin satır değişiklik.", "5.000 satır değişiklik."),
    ("Saat altıda uçuş.", "Saat 6:00'da uçuş."),
    ("Dört yüz seksen dört hata.", "484 hata."),
    ("On yedinci güncellemesi.", "17. güncellemesi."),
    ("Yüzde seksen doluluk oranı.", "%80 doluluk oranı."),
    ("Bir terabayt depolama.", "1 TB depolama."),
    ("Saat on yedide sunum.", "Saat 17:00'de sunum."),
    ("Elli bin kayıt.", "50.000 kayıt."),
    ("Yüzde otuz beş daha hızlı.", "%35 daha hızlı."),
    ("On dört Temmuz başlangıç.", "14 Temmuz başlangıç."),
    ("Beşinci iterasyon.", "5. iterasyon."),
    ("Yüz megabayt limit.", "100 MB limit."),
    ("İki yüz elli istek.", "250 istek."),
    ("Yüzde doksan iki kapsam.", "%92 kapsam."),
    ("Saat on ikide öğle.", "Saat 12:00'de öğle."),
    ("Altı ay garanti.", "6 ay garanti."),
    ("Bin altı yüz kayıt.", "1.600 kayıt."),
    ("Yüzde altmış beş tamamlandı.", "%65 tamamlandı."),
    ("Beş dakika timeout süresi.", "5 dakika timeout süresi."),
    ("On beş megabayt upload limiti.", "15 MB upload limiti."),
    ("Üçüncü çeyrekte hedef.", "3. çeyrekte hedef."),
    ("Yüz elli bin kullanıcı.", "150.000 kullanıcı."),
    ("Saat sekizde sabah koşusu.", "Saat 8:00'de sabah koşusu."),
    ("İki bin yirmi beşin sonuna kadar.", "2025 sonuna kadar."),
    ("Yüzde yetmiş yedi CPU kullanımı.", "%77 CPU kullanımı."),
    ("Dört yüz gigabayt disk.", "400 GB disk."),
    ("On beşinci sprint.", "15. sprint."),
    ("Yüzde otuz iki daha az hata.", "%32 daha az hata."),
    ("İki dakika on saniye işlem süresi.", "2 dakika 10 saniye işlem süresi."),
    ("Beş yüz seksen kullanıcı aktif.", "580 kullanıcı aktif."),
    ("Saat yirmi birde kapandı.", "Saat 21:00'de kapandı."),
    ("Yüzde dört büyüme.", "%4 büyüme."),
    ("On altı paralel işlem.", "16 paralel işlem."),
    ("Üç yüz satır dokümantasyon.", "300 satır dokümantasyon."),
    ("Yirmi iki Aralık son gün.", "22 Aralık son gün."),
]

# ---------------------------------------------------------------------------
# Veriyi birleştir, karıştır, yaz
# ---------------------------------------------------------------------------

def build_dataset() -> list[dict]:
    all_pairs = []

    for inp, out in FILLER_EASY:
        all_pairs.append({"input": inp, "output": out, "type": "filler", "difficulty": "easy"})

    for inp, out in FILLER_MEDIUM:
        all_pairs.append({"input": inp, "output": out, "type": "filler", "difficulty": "medium"})

    for inp, out in FILLER_HARD:
        all_pairs.append({"input": inp, "output": out, "type": "filler", "difficulty": "hard"})

    for inp, out in SEMANTIC_YANI:
        all_pairs.append({"input": inp, "output": out, "type": "semantic", "difficulty": "hard"})

    for inp, out in BACKTRACK:
        all_pairs.append({"input": inp, "output": out, "type": "backtrack", "difficulty": "medium"})

    for inp, out in STUTTER:
        all_pairs.append({"input": inp, "output": out, "type": "stutter", "difficulty": "easy"})

    for inp, out in NUMBER:
        all_pairs.append({"input": inp, "output": out, "type": "number", "difficulty": "medium"})

    random.shuffle(all_pairs)
    return all_pairs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Türkçe filler/disfluency pair'lerini API'siz üret."
    )
    parser.add_argument("--output", type=Path, default=Path("../data/filler_pairs.jsonl"))
    args = parser.parse_args()

    pairs = build_dataset()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    counts: dict[str, int] = {}
    for p in pairs:
        k = f"{p['type']}:{p['difficulty']}"
        counts[k] = counts.get(k, 0) + 1

    print(f"Toplam: {len(pairs)} pair → {args.output}")
    for k, n in sorted(counts.items()):
        print(f"  {k}: {n}")


if __name__ == "__main__":
    main()
