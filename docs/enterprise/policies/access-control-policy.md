# Erişim Kontrol Politikası

**Belge No:** VF-POL-002  
**Versiyon:** 1.0  
**Tarih:** 2026-04-04

---

## 1. Kullanıcı Rolleri

| Rol | Yetkiler |
|---|---|
| `superadmin` | Tüm tenant verilerine erişim, sistem konfigürasyonu |
| `admin` | Kendi tenant kullanıcı yönetimi, history, config |
| `member` | Sadece kendi kayıtları (kayıt başlat/durdur, history görüntüle) |

## 2. Kimlik Doğrulama

- **Algoritma:** JWT (HS256), bcrypt şifre hash (min. round 12)
- **Token ömrü:** Access token 60 dakika, Refresh token 7 gün
- **Minimum şifre:** 8 karakter, büyük/küçük harf + rakam
- **Production'da:** X-Api-Key fallback kapalı, sadece JWT

## 3. Erişim Prensipleri

- **Least privilege:** Kullanıcılar minimum gerekli yetkiye sahip olur
- **Tenant izolasyonu:** Bir tenant'ın verisi başka tenant'a erişilemez
- **Audit trail:** Her API çağrısı user_id + timestamp ile loglanır

## 4. Ayrıcalıklı Erişim

- Superadmin hesapları sayısı minimum tutulur
- Superadmin işlemleri audit log'a yazılır
- Üretim veritabanına doğrudan erişim (CLI) loglanır

## 5. Erişim İptali

- Kullanıcı devre dışı bırakıldığında (`is_active=0`) tüm token'lar geçersizdir
- Çalışan ayrılığında: API key rotation + token revocation
- 90 gün aktif olmayan hesaplar otomatik devre dışı bırakılır

## 6. Üçüncü Taraf Erişimi

- RunPod, HuggingFace vb. servislere erişim API key ile
- API key'ler 90 günde bir rotate edilir
- Kullanılmayan API key'ler derhal iptal edilir
