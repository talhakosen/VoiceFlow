# Olay Yönetimi Prosedürü (Incident Response Plan)

**Belge No:** VF-POL-004  
**Versiyon:** 1.0  
**Tarih:** 2026-04-04

---

## 1. Olay Sınıflandırması

| Seviye | Tanım | Örnek | Yanıt Süresi |
|---|---|---|---|
| **P1 — Kritik** | Veri ihlali veya servis tamamen çökmüş | Müşteri ses verisi sızıntısı | 1 saat |
| **P2 — Yüksek** | Yetkisiz erişim girişimi | API brute force, SQL injection | 4 saat |
| **P3 — Orta** | Servis bozukluğu | Backend crash, model yüklenemedi | 24 saat |
| **P4 — Düşük** | Güvenlik konfigürasyon uyarısı | Log anomalisi, expired token spike | 72 saat |

---

## 2. Yanıt Prosedürü

### 2.1 Tespit
- Kaynak: Audit log anomalisi, kullanıcı bildirimi, monitoring alert
- İlk tespiti yapan kişi olayı kayıt altına alır (tarih, saat, bulgu)

### 2.2 Sınırlama (Containment)
**P1/P2 için hemen:**
```bash
# Backend'i durdur
./voiceflow.sh stop

# Etkilenen kullanıcıyı devre dışı bırak
# API: POST /api/admin/users/{id}/deactivate

# API key'leri rotate et
# .env → yeni API_KEYS değeri → servis restart
```

### 2.3 Analiz
- Audit log incelemesi: `~/.voiceflow/voiceflow.log`
- Etkilenen tenant/kullanıcı tespiti
- Saldırı vektörünün belirlenmesi

### 2.4 Bildirim

**Müşteri bildirimi:**
- P1: İhlal tespitinden itibaren 72 saat içinde (KVKK madde 12 zorunluluğu)
- Bildirim içeriği: Ne oldu, hangi veriler etkilendi, alınan önlemler

**KVKK bildirimi:**
- Kişisel veri ihlali → Kişisel Verileri Koruma Kurumu'na 72 saat içinde bildirim
- Form: kvkk.gov.tr → İhlal Bildirimi

### 2.5 Kurtarma
- Yedeğe geri dön (SQLite backup)
- Güvenlik açığı kapat (patch/config değişikliği)
- Servis yeniden başlat ve doğrula

### 2.6 Raporlama
- Olay kaydına son durum yazılır
- Root cause analizi yapılır
- Kontrol iyileştirmesi planlanır (düzeltici faaliyet)

---

## 3. Senaryo: Ses Verisi İhlali

**Senaryo:** Müşteriye ait ses kayıtları yetkisiz kişi tarafından erişildi.

1. Backend durdur → veritabanını offline al
2. Etkilenen tenant'ı tespit et (audit log)
3. Müşteriye P1 bildirimi gönder (1 saat içinde)
4. KVKK'ya 72 saat içinde bildirim
5. SQLCipher şifreleme uygula (henüz yapılmadıysa)
6. Forensics için log arşivi sakla (en az 1 yıl)

---

## 4. Olay Kayıt Şablonu

```
Olay No: INC-YYYY-NNN
Tarih/Saat: 
Tespit Eden: 
Seviye: P1/P2/P3/P4
Özet: 
Etkilenen sistemler: 
Etkilenen kullanıcı/tenant sayısı: 
Alınan önlemler: 
Çözüm tarihi: 
Root cause: 
Düzeltici faaliyet: 
```
