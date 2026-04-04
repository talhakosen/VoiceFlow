# Şifreleme Politikası

**Belge No:** VF-POL-003  
**Versiyon:** 1.0  
**Tarih:** 2026-04-04

---

## 1. Data at Rest (Dinlenmedeki Veri)

| Varlık | Yöntem | Durum |
|---|---|---|
| SQLite veritabanı (ses kayıtları, history) | SQLCipher AES-256 | 🔴 TODO |
| ML model dosyaları | Dosya sistemi izinleri (600) | ✅ |
| `.env` secrets | Dosya sistemi izinleri (600) | ✅ |
| Ses kayıt buffer (RAM) | İşlem bitince temizlenir | ✅ |

## 2. Data in Transit (İletimde Veri)

| Bağlantı | Yöntem | Durum |
|---|---|---|
| Client ↔ Backend (local) | 127.0.0.1 loopback, TLS gerekmez | ✅ |
| Client ↔ Backend (server mode) | HTTPS/TLS 1.2+ zorunlu | ⬜ Nginx config |
| Backend ↔ RunPod Ollama | HTTPS | ✅ |
| Backend ↔ HuggingFace | HTTPS | ✅ |

## 3. Anahtar Yönetimi

- SQLCipher key: `DB_ENCRYPTION_KEY` env var (min 32 byte random)
- JWT secret: `JWT_SECRET` env var (min 32 byte random)
- API key'ler: `.env` dosyasında, izin 600
- Key rotation: 90 günde bir (API key'ler), 1 yılda bir (DB encryption key)
- Key yedekleme: Güvenli şifreli backup (KeePass veya 1Password)

## 4. Yasaklı Uygulamalar

- MD5, SHA1, DES, RC4 kullanımı yasak
- Şifreleme anahtarlarının kaynak koduna yazılması yasak
- Self-signed sertifika production'da kullanımı yasak (Let's Encrypt zorunlu)

## 5. Kabul Edilen Algoritmalar

| Kullanım | Algoritma |
|---|---|
| Simetrik şifreleme | AES-256-GCM |
| Asimetrik şifreleme | RSA-2048+, ECDSA |
| Hash | SHA-256, SHA-512, bcrypt, argon2 |
| TLS | 1.2 minimum, 1.3 tercih |
| JWT | HS256 (local), RS256 (multi-tenant server) |
