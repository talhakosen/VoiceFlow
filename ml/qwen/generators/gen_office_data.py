"""
gen_office_data.py — Ofis/kurumsal konuşma düzeltme çiftleri.

Teknik terim YOK — o kısım Whisper + regex dictionary hallediyor.
Odak: filler temizleme, devrik cümle düzeltme, tekrar silme,
      kurumsal mail dili, toplantı konuşması, Slack/Teams mesajları.

Zero API calls. Hardcoded.
Output: ../data/office_*.jsonl
"""

import json
import random
import pathlib

random.seed(42)

OUT_DIR = pathlib.Path(__file__).parent.parent / "data"

# ══════════════════════════════════════════════════════════════════════════════
# 1. FILLER + TEKRAR + DEVRIK CÜMLE → Düzgün cümle
# ══════════════════════════════════════════════════════════════════════════════

FILLER_CLEANUP = [
    # ── Yoğun filler temizleme ────────────────────────────────────────────
    ("yani şey ben toplantıya katılamayacağım yani", "Toplantıya katılamayacağım."),
    ("şey şimdi şey raporu gönderdim yani hani mail attım", "Raporu gönderdim, mail attım."),
    ("ee yani şimdi şöyle bir durum var hani biz bunu konuşmuştuk yani", "Şöyle bir durum var, biz bunu konuşmuştuk."),
    ("hani şey dün de söylemiştim yani bu konu hakkında yani", "Dün de söylemiştim, bu konu hakkında."),
    ("tamam şimdi yani şöyle yapalım şey herkes kendi bölümünü hazırlasın yani", "Şöyle yapalım, herkes kendi bölümünü hazırlasın."),
    ("işte şimdi şey müdür bey de onayladı yani devam edebiliriz", "Müdür bey de onayladı, devam edebiliriz."),
    ("yani ben şey şöyle düşünüyorum hani bu projeyi ertelemeyelim yani", "Şöyle düşünüyorum, bu projeyi ertelemeyelim."),
    ("ee tamam yani anladım şey yarın sabah ilk iş hallederim", "Anladım, yarın sabah ilk iş hallederim."),
    ("şey hani şimdi yani bütçe konusu var ya hani onu konuşalım", "Bütçe konusunu konuşalım."),
    ("yani şey bir dakika düşüneyim yani tamam olabilir", "Bir dakika düşüneyim, tamam olabilir."),
    ("hani yani şimdi şey patron ne dedi biliyor musun yani", "Patron ne dedi biliyor musun?"),
    ("ee şey nasıl desem yani biraz zor bir durum yani", "Biraz zor bir durum."),
    ("tamam tamam yani anlaştık şey yarın konuşuruz", "Anlaştık, yarın konuşuruz."),
    ("yani aslında şey ben bunu önceden söylemiştim hani", "Aslında ben bunu önceden söylemiştim."),
    ("şey yani hani toplantı saati değişti yani üçe aldılar", "Toplantı saati değişti, üçe aldılar."),

    # ── Kem küm / düşünerek konuşma ──────────────────────────────────────
    ("eee şimdi nasıl diyeyim eee bu işi bitiremeyeceğiz galiba", "Bu işi bitiremeyeceğiz galiba."),
    ("ıı şey ben şimdi ıı nerede kalmıştık", "Nerede kalmıştık?"),
    ("hmm yani şöyle söyleyeyim hmm bu biraz karmaşık", "Şöyle söyleyeyim, bu biraz karmaşık."),
    ("aa evet evet şey onu da yapacaktım unuttum", "Evet, onu da yapacaktım, unuttum."),
    ("eee bir saniye eee tamam buldum şey dosyayı gönderdim", "Tamam, buldum, dosyayı gönderdim."),
    ("ıı nasıl desem ıı yani şirket politikası böyle", "Şirket politikası böyle."),
    ("hmm hmm tamam hmm anladım sen devam et", "Tamam, anladım, sen devam et."),
    ("aa şey unuttum söylemeyi yarın toplantımız var", "Unuttum söylemeyi, yarın toplantımız var."),

    # ── Tekrar / yineleme ─────────────────────────────────────────────────
    ("yarın yarın toplantı var yarın sabah", "Yarın sabah toplantı var."),
    ("raporu raporu gönderdim raporu mail attım", "Raporu gönderdim, mail attım."),
    ("tamam tamam tamam anladım", "Tamam, anladım."),
    ("evet evet evet doğru söylüyorsun", "Evet, doğru söylüyorsun."),
    ("şimdi şimdi şöyle yapalım", "Şöyle yapalım."),
    ("bence bence bunu ertelemeyelim", "Bence bunu ertelemeyelim."),
    ("müşteri müşteri memnun kalmamış", "Müşteri memnun kalmamış."),
    ("toplantı toplantıyı ertelediler", "Toplantıyı ertelediler."),
    ("bugün bugün teslim etmemiz lazım bugün", "Bugün teslim etmemiz lazım."),
    ("ben ben de aynı şeyi düşünüyorum ben de", "Ben de aynı şeyi düşünüyorum."),

    # ── Devrik cümle düzeltme ─────────────────────────────────────────────
    ("gönderdim raporu dün", "Dün raporu gönderdim."),
    ("gelecek yarın müşteri", "Yarın müşteri gelecek."),
    ("konuşalım bunu bir", "Bunu bir konuşalım."),
    ("bitti proje sonunda", "Sonunda proje bitti."),
    ("lazım bize daha fazla zaman", "Bize daha fazla zaman lazım."),
    ("söyledim ben ona çoktan", "Ben ona çoktan söyledim."),
    ("var mı soru başka", "Başka soru var mı?"),
    ("olur mu yarına kadar", "Yarına kadar olur mu?"),
    ("geldim ben de toplantıya", "Ben de toplantıya geldim."),
    ("bekliyor onay müdürden", "Müdürden onay bekliyor."),
    ("hallederiz bunu bir şekilde", "Bunu bir şekilde hallederiz."),
    ("attım maili az önce", "Az önce maili attım."),
    ("çıktı sorun yine", "Yine sorun çıktı."),
    ("bakalım ne olacak görelim", "Görelim bakalım ne olacak."),
    ("gerekiyor bize iki gün daha", "Bize iki gün daha gerekiyor."),
]

# ══════════════════════════════════════════════════════════════════════════════
# 2. KURUMSAL MAİL DİKTESİ → Düzgün yazı
# ══════════════════════════════════════════════════════════════════════════════

CORPORATE_MAIL = [
    ("sayın mehmet bey toplantı saati değişti yeni saat üç olarak belirlendi bilginize", "Sayın Mehmet Bey, toplantı saati değişti. Yeni saat 3 olarak belirlendi, bilginize."),
    ("merhaba ekip yarınki toplantıya katılım zorunludur lütfen takvimlerinizi kontrol edin", "Merhaba ekip, yarınki toplantıya katılım zorunludur. Lütfen takvimlerinizi kontrol edin."),
    ("iyi günler raporu ekte gönderiyorum incelemenizi rica ederim", "İyi günler, raporu ekte gönderiyorum. İncelemenizi rica ederim."),
    ("selamlar bugünkü toplantı iptal edilmiştir yeni tarih için bilgi vereceğim", "Selamlar, bugünkü toplantı iptal edilmiştir. Yeni tarih için bilgi vereceğim."),
    ("sayın yetkili başvurumuz hakkında bilgi almak istiyoruz en kısa sürede dönüş yaparsanız seviniriz", "Sayın yetkili, başvurumuz hakkında bilgi almak istiyoruz. En kısa sürede dönüş yaparsanız seviniriz."),
    ("herkese iyi akşamlar bu hafta yapılacaklar listesini paylaşıyorum lütfen kontrol edin", "Herkese iyi akşamlar, bu hafta yapılacaklar listesini paylaşıyorum. Lütfen kontrol edin."),
    ("merhaba ayşe hanım görüşmemizle ilgili notu paylaşıyorum onayınıza sunarım", "Merhaba Ayşe Hanım, görüşmemizle ilgili notu paylaşıyorum. Onayınıza sunarım."),
    ("takım arkadaşları bu ay hedeflerimizi gözden geçirelim performans değerlendirmesi yaklaşıyor", "Takım arkadaşları, bu ay hedeflerimizi gözden geçirelim. Performans değerlendirmesi yaklaşıyor."),
    ("sayın müdürüm izin talebimi onayınıza sunuyorum tarihler ekte belirtilmiştir", "Sayın müdürüm, izin talebimi onayınıza sunuyorum. Tarihler ekte belirtilmiştir."),
    ("merhaba proje durumu hakkında güncelleme yapmak istiyorum ilerleme yüzde seksen", "Merhaba, proje durumu hakkında güncelleme yapmak istiyorum. İlerleme yüzde seksen."),
    ("değerli müşterimiz talebiniz alınmıştır en kısa sürede size dönüş yapacağız", "Değerli müşterimiz, talebiniz alınmıştır. En kısa sürede size dönüş yapacağız."),
    ("iyi çalışmalar haftalık raporu ekte bulabilirsiniz sorularınız için müsaitim", "İyi çalışmalar, haftalık raporu ekte bulabilirsiniz. Sorularınız için müsaitim."),
    ("sayın genel müdür yönetim kurulu toplantısı için gündem maddelerini sunuyorum", "Sayın Genel Müdür, yönetim kurulu toplantısı için gündem maddelerini sunuyorum."),
    ("merhaba finans departmanı bu ayki bütçe raporunu onayınıza sunarım", "Merhaba Finans Departmanı, bu ayki bütçe raporunu onayınıza sunarım."),
    ("ekip arkadaşları müşteri ziyareti yarın saat onda lütfen hazırlıklı olun", "Ekip arkadaşları, müşteri ziyareti yarın saat onda. Lütfen hazırlıklı olun."),
    ("sayın insan kaynakları yeni işe alım süreciyle ilgili görüşlerimi paylaşmak istiyorum", "Sayın İnsan Kaynakları, yeni işe alım süreciyle ilgili görüşlerimi paylaşmak istiyorum."),
    ("herkese günaydın bugün saat ikide acil toplantı var katılımınızı bekliyorum", "Herkese günaydın, bugün saat ikide acil toplantı var. Katılımınızı bekliyorum."),
    ("merhaba satış ekibi bu çeyrek hedeflerimizi aştık tebrikler", "Merhaba Satış Ekibi, bu çeyrek hedeflerimizi aştık. Tebrikler!"),
    ("sayın tedarikçimiz sipariş durumunu sormak istiyoruz teslimat tarihi yaklaşıyor", "Sayın tedarikçimiz, sipariş durumunu sormak istiyoruz. Teslimat tarihi yaklaşıyor."),
    ("iyi günler staj başvurusu hakkında bilgi almak istiyorum müsait olduğunuz bir zaman dilimi var mı", "İyi günler, staj başvurusu hakkında bilgi almak istiyorum. Müsait olduğunuz bir zaman dilimi var mı?"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 3. TOPLANTI KONUŞMASI → Düzgün metin
# ══════════════════════════════════════════════════════════════════════════════

MEETING_TALK = [
    ("şimdi yani geçen haftaki aksiyonlara bakalım hani nerede kalmıştık", "Geçen haftaki aksiyonlara bakalım, nerede kalmıştık?"),
    ("ee ben söyleyeyim yani müşteriden geri dönüş geldi olumlu yani", "Müşteriden olumlu geri dönüş geldi."),
    ("tamam şimdi yani bütçe konusuna geçelim hani ne kadar kaldı", "Bütçe konusuna geçelim, ne kadar kaldı?"),
    ("hani şey geçen sefer konuşmuştuk ya bunu yani o konu ne oldu", "Geçen sefer konuşmuştuk, o konu ne oldu?"),
    ("yani ben şöyle öneriyorum hani ikiye bölelim işi yani yarı yarıya", "Şöyle öneriyorum, işi ikiye bölelim, yarı yarıya."),
    ("ee şimdi yani herkes hemfikir mi tamam mı devam edelim mi", "Herkes hemfikir mi? Devam edelim mi?"),
    ("şey ben bir ekleme yapayım hani şu konuyu da unutmayalım yani", "Bir ekleme yapayım, şu konuyu da unutmayalım."),
    ("tamam tamam anladım yani sen şunu mu diyorsun hani değiştirelim mi", "Anladım, sen değiştirelim mi diyorsun?"),
    ("hani yani bir risk var burada bence dikkatli olmalıyız yani şey temkinli", "Bir risk var burada, bence dikkatli olmalıyız."),
    ("ee neyse konuyu toparlamak gerekirse yani üç ana madde var", "Konuyu toparlamak gerekirse, üç ana madde var."),
    ("şimdi yani bu çeyrek hedeflerimizi konuşalım neredeyiz yani", "Bu çeyrek hedeflerimizi konuşalım, neredeyiz?"),
    ("yani şey müşteri memnuniyeti düşmüş biraz yani buna bakmamız lazım", "Müşteri memnuniyeti biraz düşmüş, buna bakmamız lazım."),
    ("tamam yani şöyle yapalım herkes kendi alanıyla ilgili rapor hazırlasın", "Şöyle yapalım, herkes kendi alanıyla ilgili rapor hazırlasın."),
    ("hani şey geçen ay da aynı sorunu yaşamıştık yani çözemedik", "Geçen ay da aynı sorunu yaşamıştık, çözemedik."),
    ("ee yani toplantıyı uzatmayalım son bir konu var sadece", "Toplantıyı uzatmayalım, son bir konu var sadece."),
    ("şey yani ben katılmıyorum bu fikre hani biraz riskli bence", "Bu fikre katılmıyorum, biraz riskli bence."),
    ("yani tamam herkes görevini biliyordur umarım hani aksiyon maddeleri net", "Herkes görevini biliyordur umarım, aksiyon maddeleri net."),
    ("ee şey bir şey daha vardı aa evet müşteri ziyareti ne oldu", "Bir şey daha vardı, evet müşteri ziyareti ne oldu?"),
    ("tamam yani bugünlük bu kadar hani haftaya tekrar toplanırız yani", "Bugünlük bu kadar, haftaya tekrar toplanırız."),
    ("şimdi yani şey sonuç olarak bütçeyi artırmamız gerekiyor yani açıkça söyleyeyim", "Sonuç olarak, bütçeyi artırmamız gerekiyor, açıkça söyleyeyim."),
]

# ══════════════════════════════════════════════════════════════════════════════
# 4. SLACK / TEAMS MESAJLARI → Düzgün metin
# ══════════════════════════════════════════════════════════════════════════════

CHAT_MESSAGES = [
    ("toplantı ertelendi haberin olsun", "Toplantı ertelendi, haberin olsun."),
    ("raporu gönderir misin acil lazım", "Raporu gönderir misin? Acil lazım."),
    ("ben bugün uzaktan çalışacağım", "Ben bugün uzaktan çalışacağım."),
    ("dosyayı paylaştım bak istersen", "Dosyayı paylaştım, bak istersen."),
    ("müşteri aradı seni sordu", "Müşteri aradı, seni sordu."),
    ("bugün erken çıkacağım doktorum var", "Bugün erken çıkacağım, doktorum var."),
    ("sunum hazır mı yarına", "Sunum yarına hazır mı?"),
    ("tamam hallederim bir saate kadar", "Tamam, bir saate kadar hallederim."),
    ("toplantı odasını ayırdım saat iki için", "Toplantı odasını saat iki için ayırdım."),
    ("şifre ne wifi şifresi", "Wi-Fi şifresi ne?"),
    ("ben de geliyorum beş dakika bekle", "Ben de geliyorum, beş dakika bekle."),
    ("mail attım kontrol eder misin", "Mail attım, kontrol eder misin?"),
    ("proje teslim tarihi ne zamandı", "Proje teslim tarihi ne zamandı?"),
    ("izin aldım yarın gelmeyeceğim", "İzin aldım, yarın gelmeyeceğim."),
    ("bütçe onaylandı devam edebilirsiniz", "Bütçe onaylandı, devam edebilirsiniz."),
    ("toplantı notlarını paylaşır mısın", "Toplantı notlarını paylaşır mısın?"),
    ("müşteriye geri dönüş yaptın mı", "Müşteriye geri dönüş yaptın mı?"),
    ("yarın saat kaçta buluşuyoruz", "Yarın saat kaçta buluşuyoruz?"),
    ("stajyer geldi yönlendirir misin", "Stajyer geldi, yönlendirir misin?"),
    ("ben öğleden sonra müsaitim konuşalım", "Ben öğleden sonra müsaitim, konuşalım."),
    ("şu dosyayı bulamıyorum nerede", "Şu dosyayı bulamıyorum, nerede?"),
    ("herkes hazır mı başlayalım mı", "Herkes hazır mı? Başlayalım mı?"),
    ("geçmiş olsun duydum haberi", "Geçmiş olsun, duydum haberi."),
    ("tebrikler çok güzel olmuş", "Tebrikler, çok güzel olmuş!"),
    ("bu hafta cuma tatil mi", "Bu hafta cuma tatil mi?"),
]

# ══════════════════════════════════════════════════════════════════════════════
# 5. GÜNLÜK OFİS KONUŞMALARI → Düzgün metin
# ══════════════════════════════════════════════════════════════════════════════

DAILY_OFFICE = [
    # ── Filler + devrik + tekrar karışık ──────────────────────────────────
    ("yani şimdi şey ben yarın izinliyim hani söylemiştim ya yani", "Yarın izinliyim, söylemiştim."),
    ("ee kahve içelim mi şey aşağı inelim biraz yani mola verelim", "Kahve içelim mi? Aşağı inelim, mola verelim."),
    ("bozulmuş yine klima çok sıcak yani dayanılmıyor", "Klima yine bozulmuş, çok sıcak, dayanılmıyor."),
    ("geldi mi kargo hani sipariş etmiştik ya şey o", "Kargo geldi mi? Sipariş etmiştik."),
    ("yani ben şey öğle yemeğinde dışarı çıkacağım hani gelmek isteyen var mı", "Öğle yemeğinde dışarı çıkacağım, gelmek isteyen var mı?"),
    ("tamam tamam ben hallederim yani merak etmeyin", "Tamam, ben hallederim, merak etmeyin."),
    ("şey hani dün konuştuğumuz konu var ya yani onu bir çözelim", "Dün konuştuğumuz konuyu bir çözelim."),
    ("geç kaldım yani trafik vardı çok kötüydü şey özür dilerim", "Geç kaldım, trafik çok kötüydü, özür dilerim."),
    ("ee neyse boş ver şimdi yani başka konuya geçelim", "Neyse, başka konuya geçelim."),
    ("çok yoruldum yani bugün çok yoğundu şey hani nefes alamadım", "Çok yoruldum, bugün çok yoğundu, nefes alamadım."),
    ("şey yani hava güzel bugün dışarıda yiyelim mi yemeği", "Hava güzel bugün, dışarıda yemek yiyelim mi?"),
    ("ee tamam ben çıkıyorum yani görüşürüz yarın", "Tamam, ben çıkıyorum, yarın görüşürüz."),
    ("yani şey asansör yine bozuk merdivenden inelim hani", "Asansör yine bozuk, merdivenden inelim."),
    ("aa evet unuttum söylemeyi yani yeni bi kafe açılmış yanımıza", "Evet, unuttum söylemeyi, yanımıza yeni bir kafe açılmış."),
    ("hani şey geçen de söyledim yani su sebili bozuk", "Geçen de söyledim, su sebili bozuk."),

    # ── Backtrack + düzeltme ──────────────────────────────────────────────
    ("toplantı saat ikide hayır üçte pardon üçte", "Toplantı saat üçte."),
    ("raporu ali beye gönder hayır mehmet beye gönder", "Raporu Mehmet Bey'e gönder."),
    ("yarın gel hayır öbür gün gel daha iyi olur", "Öbür gün gel, daha iyi olur."),
    ("bunu sil dur dur silme kalsın", "Bunu silme, kalsın."),
    ("müşteriye yaz hayır önce müdüre danış", "Önce müdüre danış."),

    # ── Noktalama + büyük harf eksik (Whisper raw) ────────────────────────
    ("merhaba nasılsınız bugün toplantımız var saat ikide bekliyorum", "Merhaba, nasılsınız? Bugün toplantımız var, saat ikide bekliyorum."),
    ("teşekkürler çok yardımcı oldunuz bir sorun olursa yazarım", "Teşekkürler, çok yardımcı oldunuz. Bir sorun olursa yazarım."),
    ("günaydın herkes bugün yoğun bir gün olacak hazır olun", "Günaydın herkes, bugün yoğun bir gün olacak. Hazır olun."),
    ("iyi akşamlar yarın görüşmek üzere iyi geceler", "İyi akşamlar, yarın görüşmek üzere. İyi geceler."),
    ("tamamdır ben de onaylıyorum devam edebilirsiniz teşekkürler", "Tamamdır, ben de onaylıyorum. Devam edebilirsiniz, teşekkürler."),
]

# ══════════════════════════════════════════════════════════════════════════════
# 6. UZUN KONUŞMA → ÖZ VE NET METİN
# ══════════════════════════════════════════════════════════════════════════════

VERBOSE_TO_CONCISE = [
    ("yani şimdi şey ben şöyle düşünüyorum hani bu konuda yani aslında bence şey toplantıyı ertelesek daha iyi olur yani ne dersiniz", "Bence toplantıyı ertelesek daha iyi olur, ne dersiniz?"),
    ("ee şimdi yani nasıl söylesem hani müşteri biraz şey memnun değil yani bazı konularda sıkıntılar var şey hani geri bildirim geldi", "Müşteri bazı konularda memnun değil, geri bildirim geldi."),
    ("tamam şimdi yani şöyle bir şey var hani ben baktım yani rakamlara falan hani bütçe biraz aşılmış yani yüzde on beş falan", "Rakamlara baktım, bütçe yüzde on beş aşılmış."),
    ("yani şey hani dün akşam ben bi baktım yani şu dosyalara hani eksikler var yani tamamlamamız lazım hani acil", "Dün akşam dosyalara baktım, eksikler var, acil tamamlamamız lazım."),
    ("ee ben şey bir öneri sunmak istiyorum yani hani şöyle yapalım yani herkes kendi bölümünü tamamlasın cuma gününe kadar yani", "Bir önerim var: herkes kendi bölümünü cuma gününe kadar tamamlasın."),
    ("şimdi yani şey ben konuşayım biraz hani geçen hafta ne yaptık yani pazartesi toplantı yaptık salı rapor yazdık çarşamba müşteriye sunduk", "Geçen hafta pazartesi toplantı yaptık, salı rapor yazdık, çarşamba müşteriye sunduk."),
    ("yani tamam şey kabul ediyorum hani sen haklısın yani ben de aynı şeyi düşünüyordum zaten yani hemfikiriz", "Kabul ediyorum, haklısın, hemfikiriz."),
    ("ee şey bir dakika yani ben şunu sorayım hani bu ne zaman bitecek yani tarih var mı kesin bir", "Şunu sorayım, bu ne zaman bitecek? Kesin bir tarih var mı?"),
    ("hani yani şimdi şey şöyle bir problem var yani personel yetersiz yani iki kişi daha lazım en az hani", "Şöyle bir problem var, personel yetersiz, en az iki kişi daha lazım."),
    ("yani ben şey gidip gelmekten yoruldum yani her gün toplantı var hani biraz azaltalım yani haftada iki yeterli", "Toplantılardan yoruldum, biraz azaltalım, haftada iki yeterli."),
]

# ══════════════════════════════════════════════════════════════════════════════
# ANLAMSAL KORUMA — Silinmemesi gereken örnekler (input == output)
# ══════════════════════════════════════════════════════════════════════════════

KEEP_SEMANTIC = [
    ("500 kişi, yani şirketin yarısı toplantıya katıldı.", "500 kişi, yani şirketin yarısı toplantıya katıldı."),
    ("İşte bu yüzden erken başlamamız gerekiyor.", "İşte bu yüzden erken başlamamız gerekiyor."),
    ("Hani geçen ay konuşmuştuk ya, o proje iptal oldu.", "Hani geçen ay konuşmuştuk ya, o proje iptal oldu."),
    ("Tamam, anlaştık, yarın saat onda buluşuyoruz.", "Tamam, anlaştık, yarın saat onda buluşuyoruz."),
    ("Bir şey sormak istiyorum, izin var mı?", "Bir şey sormak istiyorum, izin var mı?"),
    ("Her şey yolunda, endişelenmeyin.", "Her şey yolunda, endişelenmeyin."),
    ("İşte tam olarak bunu kastediyorum.", "İşte tam olarak bunu kastediyorum."),
    ("Yani demek istediğim, bütçe yeterli değil.", "Yani demek istediğim, bütçe yeterli değil."),
    ("Hani şu eski projeden bahsediyorum, hatırlıyor musun?", "Hani şu eski projeden bahsediyorum, hatırlıyor musun?"),
    ("Tamam o zaman, bu planla devam edelim.", "Tamam o zaman, bu planla devam edelim."),
]

# ══════════════════════════════════════════════════════════════════════════════

ALL_CATEGORIES = {
    "office_fillers": FILLER_CLEANUP,
    "office_mail": CORPORATE_MAIL,
    "office_meeting": MEETING_TALK,
    "office_chat": CHAT_MESSAGES,
    "office_daily": DAILY_OFFICE,
    "office_verbose": VERBOSE_TO_CONCISE,
    "office_keep": KEEP_SEMANTIC,
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0

    for name, pairs in ALL_CATEGORIES.items():
        out_path = OUT_DIR / f"{name}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for inp, out in pairs:
                f.write(json.dumps({"input": inp, "output": out}, ensure_ascii=False) + "\n")
        total += len(pairs)
        print(f"  {name}.jsonl — {len(pairs)} pairs")

    print(f"\nTotal: {total} office pairs written to {OUT_DIR}")


if __name__ == "__main__":
    main()
