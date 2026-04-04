"""gen_filler_semantic.py — Türkçe SEMANTIC vs FILLER DISAMBIGUATION training data.

Produces 400+ hardcoded (input, output) pairs for the four hardest filler words:
  - YANI   : 100 pairs
  - İŞTE   : 100 pairs
  - TAMAM  : 100 pairs
  - HANİ   : 100 pairs

Each word has ~50 REMOVE examples and ~50 KEEP examples to force the model to
learn the decision boundary, not a blanket removal rule.

Usage:
  python gen_filler_semantic.py
  python gen_filler_semantic.py --output path/to/output.jsonl
"""

import argparse
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# YANI — ~50 remove + ~50 keep = 100 pairs
# ---------------------------------------------------------------------------

YANI_REMOVE = [
    # sentence-initial transition filler
    ("Yani, toplantıyı erteliyoruz.", "Toplantıyı erteliyoruz."),
    ("Yani, kod review yarına kaldı.", "Kod review yarına kaldı."),
    ("Yani, sunucu şu an kapalı.", "Sunucu şu an kapalı."),
    ("Yani, bu özelliği iptal ettik.", "Bu özelliği iptal ettik."),
    ("Yani, müşteri memnun değildi.", "Müşteri memnun değildi."),
    ("Yani, sprint bitti.", "Sprint bitti."),
    ("Yani, raporu dün gönderdim.", "Raporu dün gönderdim."),
    ("Yani, bütçe onaylandı.", "Bütçe onaylandı."),
    ("Yani, ekip yarın ofise geliyor.", "Ekip yarın ofise geliyor."),
    ("Yani, sistem güncellendi.", "Sistem güncellendi."),
    ("Yani, bu haftaki demo iptal.", "Bu haftaki demo iptal."),
    ("Yani, tasarım değişti.", "Tasarım değişti."),
    ("Yani, sözleşme imzalandı.", "Sözleşme imzalandı."),
    ("Yani, veritabanı migrate edildi.", "Veritabanı migrate edildi."),
    ("Yani, login sayfası hazır.", "Login sayfası hazır."),
    # sentence-final empty emphasis
    ("Proje gecikti yani.", "Proje gecikti."),
    ("Bunu yapamayız yani.", "Bunu yapamayız."),
    ("Çok yoruldum yani.", "Çok yoruldum."),
    ("Anlamadım yani.", "Anlamadım."),
    ("Çalışmıyor yani.", "Çalışmıyor."),
    ("Geç kaldım yani.", "Geç kaldım."),
    ("Düzeldi yani.", "Düzeldi."),
    ("Beğenmedim yani.", "Beğenmedim."),
    ("Kabul etmiyorum yani.", "Kabul etmiyorum."),
    ("Bitirdim yani.", "Bitirdim."),
    ("Sorun çözüldü yani.", "Sorun çözüldü."),
    ("Fatura ödendi yani.", "Fatura ödendi."),
    ("Test geçti yani.", "Test geçti."),
    ("Bağlantı kesildi yani.", "Bağlantı kesildi."),
    ("Görüşme iptal yani.", "Görüşme iptal."),
    # yani yani reduplication
    ("Yani yani, ne yapalım?", "Ne yapalım?"),
    ("Yani yani, projeyi durduralım.", "Projeyi durduralım."),
    ("Yani yani, biraz bekleyelim.", "Biraz bekleyelim."),
    ("Yani yani, sormak istedim.", "Sormak istedim."),
    ("Yani yani, fark etmez.", "Fark etmez."),
    # yani şey combo
    ("Yani şey, nasıl desem.", "Nasıl desem."),
    ("Yani şey, o dosyayı sil.", "O dosyayı sil."),
    ("Yani şey, konuyu değiştirelim.", "Konuyu değiştirelim."),
    ("Yani şey, bunu düşüneceğim.", "Bunu düşüneceğim."),
    ("Yani şey, haberdar ederim.", "Haberdar ederim."),
    # mid-sentence filler with no semantic role
    ("Proje, yani, yarın teslim.", "Proje yarın teslim."),
    ("Rapor, yani, hazır değil.", "Rapor hazır değil."),
    ("Sunum, yani, iptal edildi.", "Sunum iptal edildi."),
    ("Ekip, yani, çok yorgun.", "Ekip çok yorgun."),
    ("Bütçe, yani, yetersiz.", "Bütçe yetersiz."),
    # phrased as verbal tic at end of thought
    ("Bir şey yapalım yani, toplantıyı erteleyelim.", "Bir şey yapalım, toplantıyı erteleyelim."),
    ("Değiştirmemiz lazım yani, bu yaklaşım işe yaramıyor.", "Değiştirmemiz lazım, bu yaklaşım işe yaramıyor."),
    ("Farklı bir yol deneyelim yani, bu çalışmadı.", "Farklı bir yol deneyelim, bu çalışmadı."),
    ("Düşünmem lazım yani, karar vereceğim.", "Düşünmem lazım, karar vereceğim."),
    ("İptal edelim yani, kimse hazır değil.", "İptal edelim, kimse hazır değil."),
]

YANI_KEEP = [
    # yani = "that is / i.e." — clarification
    ("Proje iki haftada biter, yani Cuma teslim edebiliriz.", "Proje iki haftada biter, yani Cuma teslim edebiliriz."),
    ("Sistem yüzde doksanlık uptime tutuyor, yani çok sağlam.", "Sistem yüzde doksanlık uptime tutuyor, yani çok sağlam."),
    ("500 kullanıcı var, yani sunucu kapasitesini artırmak lazım.", "500 kullanıcı var, yani sunucu kapasitesini artırmak lazım."),
    ("API key gerekiyor, yani önce kayıt olman lazım.", "API key gerekiyor, yani önce kayıt olman lazım."),
    ("Türkiye'deki ofisimiz, yani Ankara ekibi bu konuyu yönetiyor.", "Türkiye'deki ofisimiz, yani Ankara ekibi bu konuyu yönetiyor."),
    ("Test ortamı çöktü, yani deploy yapamıyoruz.", "Test ortamı çöktü, yani deploy yapamıyoruz."),
    ("Kullanıcı girişi zorunlu, yani anonim erişim kapalı.", "Kullanıcı girişi zorunlu, yani anonim erişim kapalı."),
    ("Deadline bugün, yani sabaha kadar bitirmem lazım.", "Deadline bugün, yani sabaha kadar bitirmem lazım."),
    ("Yetki yok, yani o sayfaya giremezsin.", "Yetki yok, yani o sayfaya giremezsin."),
    ("Fiyat arttı, yani bütçeyi gözden geçirmemiz gerekiyor.", "Fiyat arttı, yani bütçeyi gözden geçirmemiz gerekiyor."),
    ("Cache temizlenmedi, yani eski veri görünüyor.", "Cache temizlenmedi, yani eski veri görünüyor."),
    ("Model 7B minimum, yani daha küçükleri deneyelim bile.", "Model 7B minimum, yani daha küçükleri deneyelim bile."),
    ("Lisans bir yıllık, yani Ocak'ta yenilememiz lazım.", "Lisans bir yıllık, yani Ocak'ta yenilememiz lazım."),
    ("Branch korunuyor, yani direkt push yapamazsın.", "Branch korunuyor, yani direkt push yapamazsın."),
    ("Ortam değişkeni eksik, yani uygulama başlamıyor.", "Ortam değişkeni eksik, yani uygulama başlamıyor."),
    # yani = "so then / therefore"
    ("O zaman yani iyi, devam edelim.", "O zaman yani iyi, devam edelim."),
    ("Onayladıysan yani başlayabiliriz.", "Onayladıysan yani başlayabiliriz."),
    ("Hazır değilse yani bekleyeceğiz.", "Hazır değilse yani bekleyeceğiz."),
    ("Bütçe yoksa yani iptal etmek zorundayız.", "Bütçe yoksa yani iptal etmek zorundayız."),
    ("Sorun giderdiysen yani deploy edebiliriz.", "Sorun giderdiysen yani deploy edebiliriz."),
    # "demek ki" pair — yani as part of semantic phrase
    ("Bu yani demek ki işe yarıyor.", "Bu yani demek ki işe yarıyor."),
    ("Hata aldıysan yani demek ki config yanlış.", "Hata aldıysan yani demek ki config yanlış."),
    ("Bağlantı olmadıysa yani demek ki VPN açık değil.", "Bağlantı olmadıysa yani demek ki VPN açık değil."),
    ("Performans düştüyse yani demek ki bellek sızıntısı var.", "Performans düştüyse yani demek ki bellek sızıntısı var."),
    ("Test geçtiyse yani demek ki PR merge edilebilir.", "Test geçtiyse yani demek ki PR merge edilebilir."),
    # Named entity clarification (i.e. / that is)
    ("İstanbul ofisimiz, yani Levent'teki bina, restore ediliyor.", "İstanbul ofisimiz, yani Levent'teki bina, restore ediliyor."),
    ("Backend servisi, yani Node.js tarafı, güncellendi.", "Backend servisi, yani Node.js tarafı, güncellendi."),
    ("Birinci sprint, yani ilk iki hafta, planlama aşamasıydı.", "Birinci sprint, yani ilk iki hafta, planlama aşamasıydı."),
    ("Ana ürün, yani mobil uygulama, öncelikli.", "Ana ürün, yani mobil uygulama, öncelikli."),
    ("Lider, yani takım kaptanı, toplantıya katılamayacak.", "Lider, yani takım kaptanı, toplantıya katılamayacak."),
    # numerical clarification
    ("Üç yüz istek var, yani kapasiteyi iki katına çıkarmak lazım.", "Üç yüz istek var, yani kapasiteyi iki katına çıkarmak lazım."),
    ("On beş gün kaldı, yani takvimi sıkıştırmamız gerekiyor.", "On beş gün kaldı, yani takvimi sıkıştırmamız gerekiyor."),
    ("Dört farklı modül var, yani dört ayrı test paketi lazım.", "Dört farklı modül var, yani dört ayrı test paketi lazım."),
    ("İki bin satır kod, yani review uzun sürecek.", "İki bin satır kod, yani review uzun sürecek."),
    ("Beş müşteri şikayet etti, yani bu kritik bir hata.", "Beş müşteri şikayet etti, yani bu kritik bir hata."),
    # contrast / consequence
    ("Veri yok, yani rapor boş gelecek.", "Veri yok, yani rapor boş gelecek."),
    ("Şifre hatalıysa yani oturum açamazsın.", "Şifre hatalıysa yani oturum açamazsın."),
    ("Onay gelmezse yani bekleyeceğiz.", "Onay gelmezse yani bekleyeceğiz."),
    ("Token süresi dolmuş, yani tekrar giriş yapman lazım.", "Token süresi dolmuş, yani tekrar giriş yapman lazım."),
    ("Dosya bulunamadı, yani path yanlış.", "Dosya bulunamadı, yani path yanlış."),
    # rhetorical yani (speaker clarifying their own meaning)
    ("Ben şunu söylüyorum yani, bu yaklaşım sürdürülebilir değil.", "Ben şunu söylüyorum yani, bu yaklaşım sürdürülebilir değil."),
    ("Kastım şu yani, daha az kod daha iyi.", "Kastım şu yani, daha az kod daha iyi."),
    ("Şöyle düşün yani, her kullanıcının ayrı bir tenant'ı var.", "Şöyle düşün yani, her kullanıcının ayrı bir tenant'ı var."),
    ("Mesele şu yani, ölçeklendirme maliyetli.", "Mesele şu yani, ölçeklendirme maliyetli."),
    ("Sorunum şu yani, bu kod test edilemiyor.", "Sorunum şu yani, bu kod test edilemiyor."),
    # yani at end with semantic weight (= "in short / the point is")
    ("Bu kadar karmaşık olmak zorunda değil yani.", "Bu kadar karmaşık olmak zorunda değil yani."),
    ("Daha iyi bir yol var yani.", "Daha iyi bir yol var yani."),
    ("Çözüm bu değil yani.", "Çözüm bu değil yani."),
    ("İşe yaramıyor yani demek ki.", "İşe yaramıyor yani demek ki."),
    ("Mantıklı bir karar değil yani.", "Mantıklı bir karar değil yani."),
]

# ---------------------------------------------------------------------------
# İŞTE — ~50 remove + ~50 keep = 100 pairs
# ---------------------------------------------------------------------------

ISTE_REMOVE = [
    # sentence-initial filler
    ("İşte, toplantı başlıyor.", "Toplantı başlıyor."),
    ("İşte, raporu gönderdim.", "Raporu gönderdim."),
    ("İşte, sunucu çöktü.", "Sunucu çöktü."),
    ("İşte, sprint planı hazır.", "Sprint planı hazır."),
    ("İşte, yeni versiyon yayınlandı.", "Yeni versiyon yayınlandı."),
    ("İşte, müşteri aradı.", "Müşteri aradı."),
    ("İşte, kod merge edildi.", "Kod merge edildi."),
    ("İşte, bütçe onaylandı.", "Bütçe onaylandı."),
    ("İşte, ekip hazır.", "Ekip hazır."),
    ("İşte, sözleşme imzalandı.", "Sözleşme imzalandı."),
    ("İşte, tasarım değişti.", "Tasarım değişti."),
    ("İşte, test tamamlandı.", "Test tamamlandı."),
    ("İşte, hata bulundu.", "Hata bulundu."),
    ("İşte, PR açıldı.", "PR açıldı."),
    ("İşte, deployment tamamlandı.", "Deployment tamamlandı."),
    # işte işte reduplication
    ("İşte işte, şimdi anladım.", "Şimdi anladım."),
    ("İşte işte, doğru yoldasın.", "Doğru yoldasın."),
    ("İşte işte, bu oldu.", "Bu oldu."),
    ("İşte işte, bunu söylemeye çalışıyordum.", "Bunu söylemeye çalışıyordum."),
    ("İşte işte, devam et.", "Devam et."),
    # işte yani combo
    ("İşte yani, yapamam.", "Yapamam."),
    ("İşte yani, zor bir durum.", "Zor bir durum."),
    ("İşte yani, karar vermeliyiz.", "Karar vermeliyiz."),
    ("İşte yani, değişiklik lazım.", "Değişiklik lazım."),
    ("İşte yani, başka bir yol yok.", "Başka bir yol yok."),
    # mid-sentence filler version
    ("Proje işte tamamlandı.", "Proje tamamlandı."),
    ("Dosya işte kayboldu.", "Dosya kayboldu."),
    ("Ekip işte ayrıldı.", "Ekip ayrıldı."),
    ("Bütçe işte yetersiz.", "Bütçe yetersiz."),
    ("Sistem işte çalışıyor.", "Sistem çalışıyor."),
    # işte + şey combo
    ("İşte şey, nasıl anlatsam.", "Nasıl anlatsam."),
    ("İşte şey, biraz bekle.", "Biraz bekle."),
    ("İşte şey, düşünmem lazım.", "Düşünmem lazım."),
    ("İşte şey, söylemesi zor.", "Söylemesi zor."),
    ("İşte şey, farklı bir yaklaşım deneyelim.", "Farklı bir yaklaşım deneyelim."),
    # verbal tic versions
    ("Ee işte, bilmiyorum.", "Bilmiyorum."),
    ("Ee işte, şimdi ne yapalım?", "Şimdi ne yapalım?"),
    ("Aa işte, fark etmez.", "Fark etmez."),
    ("Aa işte, devam edebiliriz.", "Devam edebiliriz."),
    ("Hmm işte, bakalım.", "Bakalım."),
    # işte with hani
    ("Hani işte o toplantı, ertelendi.", "O toplantı ertelendi."),
    ("Hani işte o rapor, kayboldu.", "O rapor kayboldu."),
    ("Hani işte dedim ya, yapamam.", "Dedim ya, yapamam."),
    ("Hani işte bilirsin, o konu.", "Bilirsin, o konu."),
    ("Hani işte şey, çok zor.", "Çok zor."),
    # tepid sentence-final emphasis (no semantic weight)
    ("Toplantı ertelendi işte.", "Toplantı ertelendi."),
    ("Bitti işte.", "Bitti."),
    ("Sildim işte.", "Sildim."),
    ("Gönderdim işte.", "Gönderdim."),
    ("Anladım işte.", "Anladım."),
]

ISTE_KEEP = [
    # işte = "exactly / that's the one"
    ("İşte tam olarak bunu istiyordum.", "İşte tam olarak bunu istiyordum."),
    ("İşte bu özellik eksikti.", "İşte bu özellik eksikti."),
    ("İşte bunu kastediyordum.", "İşte bunu kastediyordum."),
    ("İşte doğru cevap bu.", "İşte doğru cevap bu."),
    ("İşte aradığım çözüm.", "İşte aradığım çözüm."),
    ("İşte bu hatayı buldum.", "İşte bu hatayı buldum."),
    ("İşte merak ettiğim şey bu.", "İşte merak ettiğim şey bu."),
    ("İşte gerçek sorun bu.", "İşte gerçek sorun bu."),
    ("İşte istediğim yaklaşım bu.", "İşte istediğim yaklaşım bu."),
    ("İşte bunu bekledim.", "İşte bunu bekledim."),
    # işte = "that's why / that's the reason"
    ("İşte bu yüzden test yazmak önemli.", "İşte bu yüzden test yazmak önemli."),
    ("İşte bu nedenle deploy başarısız oldu.", "İşte bu nedenle deploy başarısız oldu."),
    ("İşte bu yüzden monorepo kullanıyoruz.", "İşte bu yüzden monorepo kullanıyoruz."),
    ("İşte bu sebeple cache'i temizlemek gerekiyor.", "İşte bu sebeple cache'i temizlemek gerekiyor."),
    ("İşte bu yüzden rate limiting şart.", "İşte bu yüzden rate limiting şart."),
    ("İşte bu yüzden code review süreci var.", "İşte bu yüzden code review süreci var."),
    ("İşte bu nedenle migration öncesi yedek alınıyor.", "İşte bu nedenle migration öncesi yedek alınıyor."),
    ("İşte bu yüzden dokümantasyon şart.", "İşte bu yüzden dokümantasyon şart."),
    ("İşte bu nedenle staging ortamı kullanıyoruz.", "İşte bu nedenle staging ortamı kullanıyoruz."),
    ("İşte bu yüzden takvimi kaçırdık.", "İşte bu yüzden takvimi kaçırdık."),
    # işte = "the issue is right here / there it is"
    ("İşte sorun burada.", "İşte sorun burada."),
    ("İşte hata bu satırda.", "İşte hata bu satırda."),
    ("İşte çakışma buradan kaynaklanıyor.", "İşte çakışma buradan kaynaklanıyor."),
    ("İşte kayıp veri bu tabloda.", "İşte kayıp veri bu tabloda."),
    ("İşte yavaşlık bu fonksiyondan.", "İşte yavaşlık bu fonksiyondan."),
    ("İşte bug tam burada.", "İşte bug tam burada."),
    ("İşte performans sorunu bu query'den.", "İşte performans sorunu bu query'den."),
    ("İşte log burada kesiyor.", "İşte log burada kesiyor."),
    ("İşte bağlantı burada kopuyor.", "İşte bağlantı burada kopuyor."),
    ("İşte memory leak tam burada.", "İşte memory leak tam burada."),
    # işte = "there you go / see?"
    ("İşte, gördün mü nasıl çalışıyor?", "İşte, gördün mü nasıl çalışıyor?"),
    ("İşte, dediğim gibi hata verdi.", "İşte, dediğim gibi hata verdi."),
    ("İşte, söyledim olmayacak diye.", "İşte, söyledim olmayacak diye."),
    ("İşte, test başarısız oldu işte.", "İşte, test başarısız oldu."),
    ("İşte, şimdi anladın mı sebebini?", "İşte, şimdi anladın mı sebebini?"),
    # işte + bu/şu/o (demonstrative — semantic anchor)
    ("İşte bu konfigürasyonu kullan.", "İşte bu konfigürasyonu kullan."),
    ("İşte şu endpoint'i test et.", "İşte şu endpoint'i test et."),
    ("İşte o model daha iyi.", "İşte o model daha iyi."),
    ("İşte bu pattern'i uygulayın.", "İşte bu pattern'i uygulayın."),
    ("İşte şu branch'i merge et.", "İşte şu branch'i merge et."),
    # işte in response to a question / problem statement
    ("- Neden çalışmıyor? - İşte onu bulmaya çalışıyorum.", "- Neden çalışmıyor? - İşte onu bulmaya çalışıyorum."),
    ("- Nasıl düzelteceksiniz? - İşte bu toplantının konusu.", "- Nasıl düzelteceksiniz? - İşte bu toplantının konusu."),
    ("- Kimin sorumluluğu? - İşte orada anlaşamıyoruz.", "- Kimin sorumluluğu? - İşte orada anlaşamıyoruz."),
    ("- Sorun ne? - İşte tam onu anlamaya çalışıyorum.", "- Sorun ne? - İşte tam onu anlamaya çalışıyorum."),
    ("- Neden bu kadar sürdü? - İşte bu soruyu sormak istedim.", "- Neden bu kadar sürdü? - İşte bu soruyu sormak istedim."),
    # complex semantic işte
    ("İşte şimdi anlıyorum neden bu şekilde yapılmış.", "İşte şimdi anlıyorum neden bu şekilde yapılmış."),
    ("İşte asıl mesele bu tasarım kararı.", "İşte asıl mesele bu tasarım kararı."),
    ("İşte fark burada ortaya çıkıyor.", "İşte fark burada ortaya çıkıyor."),
    ("İşte kritik nokta bu.", "İşte kritik nokta bu."),
    ("İşte önemli olan kısım şu.", "İşte önemli olan kısım şu."),
]

# ---------------------------------------------------------------------------
# TAMAM — ~50 remove + ~50 keep = 100 pairs
# ---------------------------------------------------------------------------

TAMAM_REMOVE = [
    # tamam as mere topic-change starter (no agreement meaning)
    ("Tamam, şimdi bakalım.", "Şimdi bakalım."),
    ("Tamam, kodun ne durumda?", "Kodun ne durumda?"),
    ("Tamam, toplantıya geçelim.", "Toplantıya geçelim."),
    ("Tamam, listeye bakalım.", "Listeye bakalım."),
    ("Tamam, raporu inceleyelim.", "Raporu inceleyelim."),
    ("Tamam, bir sonraki madde.", "Bir sonraki madde."),
    ("Tamam, devam edelim.", "Devam edelim."),
    ("Tamam, nerede kalmıştık?", "Nerede kalmıştık?"),
    ("Tamam, başlayalım.", "Başlayalım."),
    ("Tamam, şimdi ne yapacağız?", "Şimdi ne yapacağız?"),
    ("Tamam, bir şey soracağım.", "Bir şey soracağım."),
    ("Tamam, sıradaki konuya geçelim.", "Sıradaki konuya geçelim."),
    ("Tamam, özet geçeyim.", "Özet geçeyim."),
    ("Tamam, ilerleyelim.", "İlerleyelim."),
    ("Tamam, ekleyecek bir şey var mı?", "Ekleyecek bir şey var mı?"),
    # tamam tamam reduplication
    ("Tamam tamam, anladım.", "Anladım."),
    ("Tamam tamam, yapacağım.", "Yapacağım."),
    ("Tamam tamam, devam et.", "Devam et."),
    ("Tamam tamam, duruyorum.", "Duruyorum."),
    ("Tamam tamam, söyle.", "Söyle."),
    ("Tamam tamam, bakıyorum.", "Bakıyorum."),
    ("Tamam tamam, biliyorum.", "Biliyorum."),
    # tamam + yani combo
    ("Tamam tamam yani, ne yapalım?", "Ne yapalım?"),
    ("Tamam yani, farklı deneyelim.", "Farklı deneyelim."),
    ("Tamam yani, kabul ettim.", "Kabul ettim."),
    # ee tamam combo
    ("Ee tamam, şey X", "X"),
    ("Ee tamam, neyse.", "Neyse."),
    ("Ee tamam, geçelim.", "Geçelim."),
    ("Ee tamam, bir bak.", "Bir bak."),
    ("Ee tamam, anlıyorum.", "Anlıyorum."),
    # tamam + hani combo
    ("Tamam, hani şöyle bir şey var, bütçe sorunumuz var.", "Şöyle bir şey var, bütçe sorunumuz var."),
    ("Tamam, hani o toplantı vardı ya, onu iptal ettik.", "O toplantı vardı ya, onu iptal ettik."),
    ("Tamam, hani şey yani, düşünmem lazım.", "Düşünmem lazım."),
    # tamam as verbal pause before giving information
    ("Tamam, şöyle ki, veritabanı migrate edildi.", "Şöyle ki, veritabanı migrate edildi."),
    ("Tamam, yani şu an durum şu.", "Yani şu an durum şu."),
    ("Tamam, mesele şu.", "Mesele şu."),
    # tamam mid-sentence (filler pause)
    ("Bunu, tamam, sonra halledeceğiz.", "Bunu sonra halledeceğiz."),
    ("Proje, tamam, yolunda gidiyor.", "Proje yolunda gidiyor."),
    ("Ekip, tamam, hazır.", "Ekip hazır."),
    # tepid sentence-final without agreement meaning
    ("Bitti tamam.", "Bitti."),
    ("Sildim tamam.", "Sildim."),
    ("Gönderdim tamam.", "Gönderdim."),
    ("Yaptım tamam.", "Yaptım."),
    ("Kapattım tamam.", "Kapattım."),
    # tamam as empty acknowledgment that carries no info
    ("Tamam, biliyorum bunu.", "Biliyorum bunu."),
    ("Tamam, duydum.", "Duydum."),
    ("Tamam, fark ettim.", "Fark ettim."),
    ("Tamam, gördüm.", "Gördüm."),
    ("Tamam, okudum.", "Okudum."),
    # extra remove to reach 50
    ("Tamam, şimdi ne bekliyoruz?", "Şimdi ne bekliyoruz?"),
]

TAMAM_KEEP = [
    # tamam = agreement / ok (response to a request or proposal)
    ("Tamam, yarın görüşürüz.", "Tamam, yarın görüşürüz."),
    ("Tamam, o saatte olacağım.", "Tamam, o saatte olacağım."),
    ("Tamam, dosyayı göndereceğim.", "Tamam, dosyayı göndereceğim."),
    ("Tamam, yapacağım.", "Tamam, yapacağım."),
    ("Tamam, katılacağım toplantıya.", "Tamam, katılacağım toplantıya."),
    ("Tamam, PR'ı inceleyeceğim.", "Tamam, PR'ı inceleyeceğim."),
    ("Tamam, bu yaklaşımı deneyeceğim.", "Tamam, bu yaklaşımı deneyeceğim."),
    ("Tamam, kodu refactor edeceğim.", "Tamam, kodu refactor edeceğim."),
    ("Tamam, raporla ilgileneceğim.", "Tamam, raporla ilgileneceğim."),
    ("Tamam, deploy i takip edeceğim.", "Tamam, deploy'i takip edeceğim."),
    # tamam = question / seeking confirmation
    ("Tamam mı, anlaştık mı?", "Tamam mı, anlaştık mı?"),
    ("Tamam mı bu plan?", "Tamam mı bu plan?"),
    ("Bu yaklaşım tamam mı?", "Bu yaklaşım tamam mı?"),
    ("Toplantı saati tamam mı?", "Toplantı saati tamam mı?"),
    ("Rapor hazır, tamam mı?", "Rapor hazır, tamam mı?"),
    ("PR merge edildi, tamam mı?", "PR merge edildi, tamam mı?"),
    ("Sistem ayarlandı, tamam mı?", "Sistem ayarlandı, tamam mı?"),
    ("Kod tamamlandı, tamam mı?", "Kod tamamlandı, tamam mı?"),
    # tamam o zaman = "alright then / settled"
    ("Tamam o zaman toplantı iptal.", "Tamam o zaman toplantı iptal."),
    ("Tamam o zaman yarın konuşuruz.", "Tamam o zaman yarın konuşuruz."),
    ("Tamam o zaman bekleriz.", "Tamam o zaman bekleriz."),
    ("Tamam o zaman sen halledersin.", "Tamam o zaman sen halledersin."),
    ("Tamam o zaman planı değiştirelim.", "Tamam o zaman planı değiştirelim."),
    # dialogue tamam (responding "ok" to someone)
    ("- PR'ı gönderir misin? - Tamam.", "- PR'ı gönderir misin? - Tamam."),
    ("- Yarın gelecek misin? - Tamam.", "- Yarın gelecek misin? - Tamam."),
    ("- Bunu düzeltir misin? - Tamam.", "- Bunu düzeltir misin? - Tamam."),
    ("- Raporları paylaşır mısın? - Tamam.", "- Raporları paylaşır mısın? - Tamam."),
    ("- Toplantıya katılır mısın? - Tamam.", "- Toplantıya katılır mısın? - Tamam."),
    # tamam = "fine / I accept this state" (resolution meaning)
    ("Tamam, bu versiyonla devam edebiliriz.", "Tamam, bu versiyonla devam edebiliriz."),
    ("Tamam, bu hatayı şimdilik kabul ediyoruz.", "Tamam, bu hatayı şimdilik kabul ediyoruz."),
    ("Tamam, bu planı onaylıyorum.", "Tamam, bu planı onaylıyorum."),
    ("Tamam, tasarımı beğendim.", "Tamam, tasarımı beğendim."),
    ("Tamam, bu çözüm yeterli.", "Tamam, bu çözüm yeterli."),
    # tamam embedded in sentence with semantic meaning
    ("Her şey tamam göründü.", "Her şey tamam göründü."),
    ("Sistem tamam çalışıyor.", "Sistem tamam çalışıyor."),
    ("Kod tamam ama test eksik.", "Kod tamam ama test eksik."),
    ("Tasarım tamam, içerik bekleniyor.", "Tasarım tamam, içerik bekleniyor."),
    ("Altyapı tamam, uygulama hazır değil.", "Altyapı tamam, uygulama hazır değil."),
    # tamam as part of compound expression
    ("Her şey yolunda ve tamam.", "Her şey yolunda ve tamam."),
    ("Durum tamam değil, hata var.", "Durum tamam değil, hata var."),
    ("Bağlantı tamam ama veri gelmiyor.", "Bağlantı tamam ama veri gelmiyor."),
    ("Lisans tamam, aktivasyon bekliyor.", "Lisans tamam, aktivasyon bekliyor."),
    ("Ödeme tamam, teslim bekleniyor.", "Ödeme tamam, teslim bekleniyor."),
    # tamam = "good / done" status in a tech context
    ("Build tamam, testler çalışıyor.", "Build tamam, testler çalışıyor."),
    ("Migration tamam, veri doğrulandı.", "Migration tamam, veri doğrulandı."),
    ("Deploy tamam, monitoring izliyor.", "Deploy tamam, monitoring izliyor."),
    ("Setup tamam, uygulama ayağa kalktı.", "Setup tamam, uygulama ayağa kalktı."),
    ("Config tamam, restart gerekiyor.", "Config tamam, restart gerekiyor."),
    # extra keep to reach 50
    ("Tamam, bu kararı onaylıyorum.", "Tamam, bu kararı onaylıyorum."),
    ("Tamam, sana güveniyorum bu konuda.", "Tamam, sana güveniyorum bu konuda."),
]

# ---------------------------------------------------------------------------
# HANİ — ~50 remove + ~50 keep = 100 pairs
# ---------------------------------------------------------------------------

HANI_REMOVE = [
    # sentence-initial filler
    ("Hani, toplantı vardı ya.", "Toplantı vardı ya."),
    ("Hani, şimdi ne yapacağız?", "Şimdi ne yapacağız?"),
    ("Hani, bunu düşünüyordum.", "Bunu düşünüyordum."),
    ("Hani, kod review bitsin.", "Kod review bitsin."),
    ("Hani, raporu yazmam lazım.", "Raporu yazmam lazım."),
    ("Hani, bir fikrim vardı.", "Bir fikrim vardı."),
    ("Hani, müşteri bekliyordu.", "Müşteri bekliyordu."),
    ("Hani, şey dediler ya.", "Şey dediler ya."),
    ("Hani, sprint bitmek üzere.", "Sprint bitmek üzere."),
    ("Hani, yeni özellik ekliyoruz.", "Yeni özellik ekliyoruz."),
    ("Hani, bütçe sorunu var.", "Bütçe sorunu var."),
    ("Hani, ekip değişiyor.", "Ekip değişiyor."),
    ("Hani, sunum yarın.", "Sunum yarın."),
    ("Hani, sözleşme bitti.", "Sözleşme bitti."),
    ("Hani, test sonuçları geldi.", "Test sonuçları geldi."),
    # hani yani combo
    ("Hani yani, ne diyeyim.", "Ne diyeyim."),
    ("Hani yani, zor bir durum.", "Zor bir durum."),
    ("Hani yani, bilmiyorum.", "Bilmiyorum."),
    ("Hani yani, değişmez artık.", "Değişmez artık."),
    ("Hani yani, fark etmez.", "Fark etmez."),
    ("Hani yani, düşünmem lazım.", "Düşünmem lazım."),
    # hani şey combo
    ("Hani şey, nasıl desem.", "Nasıl desem."),
    ("Hani şey, o dosya.", "O dosya."),
    ("Hani şey, söylemesi güç.", "Söylemesi güç."),
    ("Hani şey, bilirsin.", "Bilirsin."),
    ("Hani şey, şöyle bir durum var.", "Şöyle bir durum var."),
    # hani işte combo
    ("Hani işte, ne yapacağız?", "Ne yapacağız?"),
    ("Hani işte, sorun bu.", "Sorun bu."),
    ("Hani işte, bilirsin nasıl oluyor.", "Bilirsin nasıl oluyor."),
    # tepid "hani" mid-sentence without reference meaning
    ("Bunu, hani, yapabiliriz.", "Bunu yapabiliriz."),
    ("Proje, hani, gecikmedi.", "Proje gecikmedi."),
    ("Sistem, hani, çalışıyor.", "Sistem çalışıyor."),
    ("Ekip, hani, hazır.", "Ekip hazır."),
    ("Rapor, hani, tamamlandı.", "Rapor tamamlandı."),
    # sentence-final filler hani
    ("Yapamam hani.", "Yapamam."),
    ("Bilmiyorum hani.", "Bilmiyorum."),
    ("Anlamadım hani.", "Anlamadım."),
    ("Yoruldum hani.", "Yoruldum."),
    ("Hazır değilim hani.", "Hazır değilim."),
    # hani as empty "you know what I mean" without actual referent
    ("Hani, nasıl desem, zor.", "Zor."),
    ("Hani, şöyle bir şey, zaten biliyorsun.", "Zaten biliyorsun."),
    ("Hani, ne bileyim, fark etmez.", "Fark etmez."),
    ("Hani, bilmiyorum, bakacağım.", "Bakacağım."),
    ("Hani, nasıl anlatayım, karmaşık.", "Karmaşık."),
    # stacked fillers with hani
    ("Ee hani, toplantı.", "Toplantı."),
    ("Aa hani, fark ettim.", "Fark ettim."),
    ("Yani hani, ne yapalım?", "Ne yapalım?"),
    ("İşte hani, sorun var.", "Sorun var."),
    ("Tamam hani, geçelim.", "Geçelim."),
    # extra remove to reach 50
    ("Hani, ne zaman bitecek bu?", "Ne zaman bitecek bu?"),
]

HANI_KEEP = [
    # hani = referencing shared knowledge / "you know the one"
    ("Hani o toplantı vardı ya, onu erteledik.", "Hani o toplantı vardı ya, onu erteledik."),
    ("Hani o bug vardı ya, düzeldi.", "Hani o bug vardı ya, düzeldi."),
    ("Hani o müşteri vardı ya, geri döndü.", "Hani o müşteri vardı ya, geri döndü."),
    ("Hani o özellik vardı ya, şimdi aktif.", "Hani o özellik vardı ya, şimdi aktif."),
    ("Hani o sözleşme vardı ya, imzalandı.", "Hani o sözleşme vardı ya, imzalandı."),
    ("Hani o rapordu ya, kayboldu.", "Hani o rapordu ya, kayboldu."),
    ("Hani o sunum vardı ya, iptal edildi.", "Hani o sunum vardı ya, iptal edildi."),
    ("Hani o API vardı ya, değişti.", "Hani o API vardı ya, değişti."),
    ("Hani o veritabanı vardı ya, migrate edildi.", "Hani o veritabanı vardı ya, migrate edildi."),
    ("Hani o model vardı ya, güncelledik.", "Hani o model vardı ya, güncelledik."),
    # hani = referencing prior statement ("remember when I said")
    ("Hani dün söylediğim şey, haklıymışım.", "Hani dün söylediğim şey, haklıymışım."),
    ("Hani geçen hafta konuştuğumuz sorun, çözüldü.", "Hani geçen hafta konuştuğumuz sorun, çözüldü."),
    ("Hani toplantıda anlattığım plan, onaylandı.", "Hani toplantıda anlattığım plan, onaylandı."),
    ("Hani sabah bahsettiğim hata, tekrar çıktı.", "Hani sabah bahsettiğim hata, tekrar çıktı."),
    ("Hani daha önce denediğimiz yöntem, işe yarıyor.", "Hani daha önce denediğimiz yöntem, işe yarıyor."),
    ("Hani geçen ay iptal ettiğimiz feature, geri geliyor.", "Hani geçen ay iptal ettiğimiz feature, geri geliyor."),
    ("Hani o zaman konuştuğumuz mimari, şimdi anlıyorum.", "Hani o zaman konuştuğumuz mimari, şimdi anlıyorum."),
    ("Hani sana söylediğim o araç, burada da işe yarar.", "Hani sana söylediğim o araç, burada da işe yarar."),
    ("Hani ilk sprintte aldığımız karar, değişmesi lazım.", "Hani ilk sprintte aldığımız karar, değişmesi lazım."),
    ("Hani benim önerdiğim çözüm, onu dene.", "Hani benim önerdiğim çözüm, onu dene."),
    # hani = "you know / I mean" as epistemic hedge with real content
    ("Hani, şöyle bir durum var, proje beklenmedik gecikti.", "Hani, şöyle bir durum var, proje beklenmedik gecikti."),
    ("Hani, bunu söylemek zor ama, bütçe yetmeyecek.", "Hani, bunu söylemek zor ama, bütçe yetmeyecek."),
    ("Hani, aramızda kalsın, ekipte ciddi bir sorun var.", "Hani, aramızda kalsın, ekipte ciddi bir sorun var."),
    ("Hani, bilesin diye söylüyorum, deadline değişti.", "Hani, bilesin diye söylüyorum, deadline değişti."),
    ("Hani, kendi aramızda, o yaklaşım yanlış.", "Hani, kendi aramızda, o yaklaşım yanlış."),
    # hani in a question — "do you remember / don't you know"
    ("Hani o dosyayı nereye koydun?", "Hani o dosyayı nereye koydun?"),
    ("Hani o linki paylaşmıştın, hâlâ var mı?", "Hani o linki paylaşmıştın, hâlâ var mı?"),
    ("Hani o toplantı notları, bulabilir misin?", "Hani o toplantı notları, bulabilir misin?"),
    ("Hani o PR'ı açmıştın, merge edildi mi?", "Hani o PR'ı açmıştın, merge edildi mi?"),
    ("Hani o rakibi analiz etmiştik, rapor nerede?", "Hani o rakibi analiz etmiştik, rapor nerede?"),
    # hani with "ya" — confirming shared knowledge
    ("Hani o zor müşteri ya, sonunda ikna oldu.", "Hani o zor müşteri ya, sonunda ikna oldu."),
    ("Hani o yavaş query ya, index ekleyince düzeldi.", "Hani o yavaş query ya, index ekleyince düzeldi."),
    ("Hani o büyük release ya, beklenenden iyi gitti.", "Hani o büyük release ya, beklenenden iyi gitti."),
    ("Hani o kritik hata ya, hiç kimseyi etkilemedi.", "Hani o kritik hata ya, hiç kimseyi etkilemedi."),
    ("Hani o uzun sprint ya, sonunda bitti.", "Hani o uzun sprint ya, sonunda bitti."),
    # hani = "like" (approximation or illustrative meaning)
    ("Hani şöyle bir şey, bir tür middleware gibi.", "Hani şöyle bir şey, bir tür middleware gibi."),
    ("Hani proxy gibi bir şey, ama daha akıllı.", "Hani proxy gibi bir şey, ama daha akıllı."),
    ("Hani cache ama gerçek zamanlı, öyle bir şey.", "Hani cache ama gerçek zamanlı, öyle bir şey."),
    ("Hani event-driven ama senkron, anladın mı?", "Hani event-driven ama senkron, anladın mı?"),
    ("Hani microservice ama monorepo içinde, öyle.", "Hani microservice ama monorepo içinde, öyle."),
    # hani as implicit reminder
    ("Hani biz anlaşmıştık bunu yapmamak için.", "Hani biz anlaşmıştık bunu yapmamak için."),
    ("Hani sen de biliyorsun bu işin nasıl döndüğünü.", "Hani sen de biliyorsun bu işin nasıl döndüğünü."),
    ("Hani o kuralı koymuştuk, unuttun mu?", "Hani o kuralı koymuştuk, unuttun mu?"),
    ("Hani geçen toplantıda karar aldık, uygulayalım.", "Hani geçen toplantıda karar aldık, uygulayalım."),
    ("Hani sana göstermiştim nasıl yapıldığını.", "Hani sana göstermiştim nasıl yapıldığını."),
    # hani in story context (narrative reference)
    ("Hani geçen yıl çöken o sistem, şimdi yeniden yazdık.", "Hani geçen yıl çöken o sistem, şimdi yeniden yazdık."),
    ("Hani o eski mimari, artık kullanmıyoruz.", "Hani o eski mimari, artık kullanmıyoruz."),
    ("Hani ilk versiyonda olan o sorun, şimdi yok.", "Hani ilk versiyonda olan o sorun, şimdi yok."),
    ("Hani o kötü şöhretli modül, yeniden yazıldı.", "Hani o kötü şöhretli modül, yeniden yazıldı."),
    ("Hani o eski provider, artık desteklenmiyor.", "Hani o eski provider, artık desteklenmiyor."),
]

# ---------------------------------------------------------------------------
# Assemble & write
# ---------------------------------------------------------------------------

def build_pairs():
    all_pairs = []

    # YANI
    for inp, out in YANI_REMOVE:
        all_pairs.append({"input": inp, "output": out})
    for inp, out in YANI_KEEP:
        all_pairs.append({"input": inp, "output": out})

    # İŞTE
    for inp, out in ISTE_REMOVE:
        all_pairs.append({"input": inp, "output": out})
    for inp, out in ISTE_KEEP:
        all_pairs.append({"input": inp, "output": out})

    # TAMAM
    for inp, out in TAMAM_REMOVE:
        all_pairs.append({"input": inp, "output": out})
    for inp, out in TAMAM_KEEP:
        all_pairs.append({"input": inp, "output": out})

    # HANİ
    for inp, out in HANI_REMOVE:
        all_pairs.append({"input": inp, "output": out})
    for inp, out in HANI_KEEP:
        all_pairs.append({"input": inp, "output": out})

    return all_pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[1] / "data" / "filler_semantic.jsonl"),
    )
    args = parser.parse_args()

    pairs = build_pairs()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    # Count categories
    yani_total = len(YANI_REMOVE) + len(YANI_KEEP)
    iste_total = len(ISTE_REMOVE) + len(ISTE_KEEP)
    tamam_total = len(TAMAM_REMOVE) + len(TAMAM_KEEP)
    hani_total = len(HANI_REMOVE) + len(HANI_KEEP)

    print(f"Written {len(pairs)} pairs to {out_path}")
    print(f"  YANI  : {len(YANI_REMOVE)} remove + {len(YANI_KEEP)} keep = {yani_total}")
    print(f"  ISTE  : {len(ISTE_REMOVE)} remove + {len(ISTE_KEEP)} keep = {iste_total}")
    print(f"  TAMAM : {len(TAMAM_REMOVE)} remove + {len(TAMAM_KEEP)} keep = {tamam_total}")
    print(f"  HANI  : {len(HANI_REMOVE)} remove + {len(HANI_KEEP)} keep = {hani_total}")


if __name__ == "__main__":
    main()
