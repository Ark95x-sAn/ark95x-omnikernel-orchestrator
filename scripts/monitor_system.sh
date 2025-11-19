#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# ARK95X CONTINUOUS SYSTEM MONITOR
# ═══════════════════════════════════════════════════════════════
# Monitors system health and auto-restarts services if needed
# ═══════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROD_DIR="$HOME/ark95x-production"
LOG_DIR="$HOME/ark95x-complete/logs"
MONITOR_LOG="$LOG_DIR/monitor_$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MONITOR_LOG"
}

check_ollama() {
    if ! pgrep -x ollama > /dev/null; then
        log_message "${YELLOW}⚠ Ollama not running, attempting restart...${NC}"
        nohup ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
        sleep 5

        if pgrep -x ollama > /dev/null; then
            log_message "${GREEN}✓ Ollama restarted successfully${NC}"
            return 0
        else
            log_message "${RED}✗ Failed to restart Ollama${NC}"
            return 1
        fi
    else
        log_message "${GREEN}✓ Ollama is running${NC}"
        return 0
    fi
}

check_disk_space() {
    local usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

    if [ "$usage" -gt 90 ]; then
        log_message "${RED}✗ Disk usage critical: ${usage}%${NC}"
        return 1
    elif [ "$usage" -gt 80 ]; then
        log_message "${YELLOW}⚠ Disk usage high: ${usage}%${NC}"
        return 0
    else
        log_message "${GREEN}✓ Disk usage normal: ${usage}%${NC}"
        return 0
    fi
}

check_memory() {
    local mem_available=$(free -m | awk 'NR==2 {print $7}')

    if [ "$mem_available" -lt 500 ]; then
        log_message "${YELLOW}⚠ Low memory: ${mem_available}MB available${NC}"
        return 0
    else
        log_message "${GREEN}✓ Memory available: ${mem_available}MB${NC}"
        return 0
    fi
}

run_health_check() {
    log_message "${CYAN}═══ Health Check Starting ═══${NC}"

    check_ollama
    check_disk_space
    check_memory

    # Run Python health monitor if available
    if [ -f "$PROD_DIR/backend/health_monitor.py" ]; then
        python3 "$PROD_DIR/backend/health_monitor.py" >> "$MONITOR_LOG" 2>&1
    fi

    log_message "${CYAN}═══ Health Check Complete ═══${NC}"
    echo ""
}

# Main monitoring loop
INTERVAL=${1:-300}  # Default: check every 5 minutes

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         ARK95X SYSTEM MONITOR STARTED                  ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Check interval: ${INTERVAL} seconds${NC}"
echo -e "${YELLOW}Log file: $MONITOR_LOG${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

while true; do
    run_health_check
    sleep "$INTERVAL"
done
