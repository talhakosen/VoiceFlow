#!/bin/bash
# VoiceFlow Overnight Training Monitor
# Cron: */3 * * * * /path/to/monitor_training.sh

BOT_TOKEN="8739980423:AAGiZD0ZFu7BwEK9XSSixFlvHnE5Ql8XPXY"
CHAT_ID="1410531590"
LOG="/tmp/voiceflow_overnight.log"
STATE="/tmp/voiceflow_monitor_state"

send() {
  curl -s "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d chat_id="$CHAT_ID" \
    -d text="$1" \
    -d parse_mode=Markdown > /dev/null 2>&1
}

# Log yoksa training başlamamış
[ ! -f "$LOG" ] && exit 0

# Process hâlâ çalışıyor mu?
RUNNING=$(pgrep -f "overnight_train.py" 2>/dev/null)

# Son bilgileri al
LAST_ROUND=$(grep "ROUND" "$LOG" 2>/dev/null | grep -v "==" | tail -1)
LAST_ITER=$(grep "Iter [0-9]" "$LOG" 2>/dev/null | grep -v "Calculating" | tail -1)
BEST_LINE=$(grep "IMPROVED\|NO IMPROVEMENT\|FAILED" "$LOG" 2>/dev/null | tail -1)
MEMORY=$(grep "Memory:" "$LOG" 2>/dev/null | tail -1)
COMPLETE=$(grep "OVERNIGHT TRAINING COMPLETE" "$LOG" 2>/dev/null)

# Memory kullanımı
MEM_USED=$(vm_stat 2>/dev/null | awk '/Pages active/ {active=$3} /Pages free/ {free=$3} /Pages inactive/ {inactive=$3} END {printf "%.1f", (active*16384)/(1024^3)}')
MEM_FREE=$(vm_stat 2>/dev/null | awk '/Pages free/ {free=$3} /Pages inactive/ {inactive=$3} END {printf "%.1f", (free+inactive)*16384/(1024^3)}')

# Mevcut durumu hash'le — değişmediyse mesaj atma
CURRENT_HASH=$(echo "${LAST_ROUND}|${LAST_ITER}|${BEST_LINE}|${COMPLETE}|${RUNNING}" | md5 -q 2>/dev/null || md5sum | cut -d' ' -f1)
PREV_HASH=$(cat "$STATE" 2>/dev/null)

[ "$CURRENT_HASH" = "$PREV_HASH" ] && exit 0
echo "$CURRENT_HASH" > "$STATE"

# Eğitim bittiyse final rapor
if [ -n "$COMPLETE" ]; then
  RESULTS=$(grep "Round\|Best val\|Best adapter\|Total time" "$LOG" | tail -15)
  send "🏁 *Overnight Training BİTTİ*

${RESULTS}"
  crontab -l 2>/dev/null | grep -v "monitor_training" | crontab -
  exit 0
fi

# Process ölmüşse uyar
if [ -z "$RUNNING" ]; then
  ERROR=$(tail -5 "$LOG" 2>/dev/null)
  send "💀 *Training DURDU* — process yok!

Son log:
\`\`\`
${ERROR}
\`\`\`
🧠 RAM: ${MEM_USED}GB used / ${MEM_FREE}GB free"
  exit 0
fi

# Progress mesajı
MSG="🔄 *Training Devam Ediyor*
${LAST_ROUND:-Başlıyor...}
\`${LAST_ITER:-bekliyor}\`
${BEST_LINE:-—}
🧠 RAM: ${MEM_USED}GB used / ${MEM_FREE}GB free"

send "$MSG"
