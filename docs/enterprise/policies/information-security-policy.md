# Bilgi Güvenliği Politikası (ISP)

**Belge No:** VF-POL-001  
**Versiyon:** 1.0  
**Tarih:** 2026-04-04  
**Onaylayan:** Talha Kösen (Kurucu)  
**Gözden Geçirme:** Yılda bir (her Nisan)

---

## 1. Amaç

Bu politika, VoiceFlow ürünü kapsamındaki tüm bilgi varlıklarının gizliliğini, bütünlüğünü ve erişilebilirliğini (CIA triad) korumak amacıyla hazırlanmıştır.

## 2. Kapsam

- Backend sunucu (Python/FastAPI)
- macOS istemci uygulaması (Swift)
- Müşteri ses kayıtları ve transkripsiyon verileri
- Kaynak kodu ve ML modelleri
- Üçüncü taraf servisler (RunPod, HuggingFace, Trello)

## 3. Bilgi Güvenliği İlkeleri

### 3.1 Gizlilik
- Müşteri ses verileri yalnızca yetkili personel tarafından erişilebilir
- Veriler şifrelenmiş ortamda saklanır (data at rest + in transit)
- API anahtarları ve şifreler asla kaynak koduna yazılmaz

### 3.2 Bütünlük
- Audit log append-only tutulur, değiştirilemez
- Veritabanı değişiklikleri kullanıcı ID'si ile loglanır
- Model dosyaları hash kontrolü ile doğrulanır

### 3.3 Erişilebilirlik
- Servis hedefi: %99 uptime (mesai saatleri içinde)
- Yedekleme: günlük SQLite backup
- Felaket kurtarma planı: `business-continuity-plan.md`

## 4. Sorumluluklar

| Rol | Sorumluluk |
|---|---|
| Kurucu / Geliştirici | Tüm teknik kontrollerin uygulanması |
| Müşteri (tenant) | Kendi kullanıcı erişim yönetimi |

## 5. Kural İhlali

Politika ihlali tespit edildiğinde `incident-response-plan.md` prosedürü uygulanır. İhlaller kayıt altına alınır.

## 6. Bağlantılı Dokümanlar

- `access-control-policy.md`
- `encryption-policy.md`
- `incident-response-plan.md`
- `risk-register.md`
