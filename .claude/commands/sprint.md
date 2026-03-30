---
description: Sprint başlat — PO agent Trello'dan kart seçer, developer'a atar, DoD takip eder
---

# Sprint: $ARGUMENTS

`$ARGUMENTS` boşsa → Katman 1 backlog'undan en öncelikli kartı al ve başlat.
`$ARGUMENTS` bir kart adı veya ID'si ise → direkt o kartı başlat.

## PO Agent'ı Çağır

```
GÖREV: Sprint başlat

1. Trello Backlog'dan Katman 1 kartlarını listele (label=green)
2. Öncelik sırasına göre ilk kartı seç:
   - Menu sadeleştirme
   - Settings 2-panel
   - Recording overlay pill
   - Dictionary
   - Snippets
   - RAG tam test

3. Seçilen kart için:
   a. Acceptance Criteria yaz ve karta comment olarak ekle
   b. Kartı In Progress'e taşı
   c. Architect gerekiyor mu karar ver
   d. Developer agent'ı çağır

4. Developer agent'a şunu söyle:
   KART: [ad]
   KART ID: [id]
   KATMAN: 1

   Trello kartındaki checklist'leri oku.
   Her adımı uygula, tamamlayınca checklist item'ını kapat.
   Blocker varsa karta comment yaz ve PO'ya bildir.
   Bitince reviewer'a bildir.

5. Developer bitirince → reviewer agent'ı çağır:
   KART ID: [id]
   DEĞİŞEN DOSYALAR: [liste]

6. Review sonucu:
   - CRITICAL yok → Done'a taşı + /commit
   - CRITICAL var → developer'a geri gönder

TRELLO BOARD: Omhc3R8e
```

## Manuel Kart Başlatmak İçin

```
/sprint menu sadeleştirme
/sprint 69cab07dc3764c331a61f7ff
```

## Paralel İş

In Progress'te max 3 kart olabilir. PO agent bunu kontrol eder.
Birden fazla bağımsız kart varsa developer agent'ları paralel başlat.
