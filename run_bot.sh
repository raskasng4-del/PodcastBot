#!/bin/bash
# ============================================================
# 🚀 PODCAST BOT - سكريبت التشغيل المستمر
# ============================================================
# ينفذ البوت كل X دقيقة ويبحث عن روابط جديدة

set -e

# الإعدادات
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$BOT_DIR/logs"
URLS_FILE="$BOT_DIR/urls.txt"
PROCESSED_FILE="$BOT_DIR/processed.txt"
PID_FILE="$BOT_DIR/bot.pid"

mkdir -p "$LOG_DIR"
touch "$URLS_FILE" "$PROCESSED_FILE"

# الألوان
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_DIR/bot.log"; }

# ============================================================
# 1️⃣  تشغيل البوت لمرة واحدة
# ============================================================
run_bot() {
    log "${YELLOW}🔄 تشغيل البوت...${NC}"
    cd "$BOT_DIR"
    
    # قراءة الروابط غير المعالجة
    while IFS= read -r url; do
        [ -z "$url" ] && continue
        if grep -q "^$url$" "$PROCESSED_FILE" 2>/dev/null; then
            continue
        fi
        
        log "${GREEN}📥 معالجة: $url${NC}"
        
        # تشغيل البوت لهذا الرابط فقط
        python podcast_bot.py --url "$url" 2>&1 | tee -a "$LOG_DIR/run.log"
        
        if [ $? -eq 0 ]; then
            echo "$url" >> "$PROCESSED_FILE"
            log "${GREEN}✅ تم بنجاح${NC}"
        else
            log "${RED}❌ فشل${NC}"
        fi
    done < "$URLS_FILE"
}

# ============================================================
# 2️⃣  تشغيل مستمر (loop)
# ============================================================
watch_loop() {
    log "${GREEN}🚀 بدء المراقبة المستمرة (كل 5 دقائق)${NC}"
    while true; do
        run_bot
        sleep 300  # 5 دقائق
    done
}

# ============================================================
# 3️⃣  تشغيل كـ systemd service
# ============================================================
install_service() {
    echo "📦 تثبيت كـ systemd service..."
    
    sudo tee /etc/systemd/system/podcast-bot.service > /dev/null <<EOF
[Unit]
Description=Podcast Abdo Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
ExecStart=/usr/bin/bash $BOT_DIR/run_bot.sh watch
Restart=always
RestartSec=30
StandardOutput=append:$LOG_DIR/service.log
StandardError=append:$LOG_DIR/service.log

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable podcast-bot
    sudo systemctl start podcast-bot
    log "${GREEN}✅ service مثبت ومشتغل!${NC}"
    echo "   تحقق: sudo systemctl status podcast-bot"
    echo "   إيقاف: sudo systemctl stop podcast-bot"
    echo "   سجل: journalctl -u podcast-bot -f"
}

# ============================================================
# 4️⃣  إضافة روابط جديدة
# ============================================================
add_url() {
    echo "$1" >> "$URLS_FILE"
    log "${GREEN}✅ تم إضافة الرابط: $1${NC}"
}

# ============================================================
# 5️⃣  إحصائيات
# ============================================================
stats() {
    total=$(wc -l < "$URLS_FILE" 2>/dev/null || echo 0)
    done_count=$(wc -l < "$PROCESSED_FILE" 2>/dev/null || echo 0)
    pending=$((total - done_count))
    
    echo ""
    echo "📊 إحصائيات البوت:"
    echo "   📥 إجمالي الروابط: $total"
    echo "   ✅ تم المعالجة: $done_count"
    echo "   ⏳ في الانتظار: $pending"
    echo ""
    echo "   📂 السجلات: $LOG_DIR/"
    echo "   📄 ملف الروابط: $URLS_FILE"
    echo ""
}

# ============================================================
case "${1:-}" in
    watch)
        watch_loop
        ;;
    run)
        run_bot
        ;;
    install)
        install_service
        ;;
    add)
        shift; add_url "$*"
        ;;
    stats)
        stats
        ;;
    *)
        echo ""
        echo "🚀 Podcast Abdo Bot - Continuous Runner"
        echo ""
        echo "الاستخدام:"
        echo "   bash run_bot.sh run       🔄 تشغيل لمرة واحدة"
        echo "   bash run_bot.sh watch     👁️ تشغيل مستمر (loop)"
        echo "   bash run_bot.sh install   📦 تثبيت كـ systemd service"
        echo "   bash run_bot.sh add URL   ➕ إضافة رابط جديد"
        echo "   bash run_bot.sh stats     📊 الإحصائيات"
        echo ""
        ;;
esac
