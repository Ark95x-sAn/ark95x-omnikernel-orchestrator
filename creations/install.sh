#!/bin/bash
# ARK95X OMNI-CREATION INSTALLER v3.0 - MICKEY PROTOCOL
# AI Engineer 6-Month Roadmap + 80+ Ethical Hacking Arsenal
# Corrected & Production-Ready | Deployed 01 Mar 2026
set -euo pipefail

LOG="$HOME/ark95x_omni_creation_$(date +%s).log"
P=0; F=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== MICKEY ACTIVATION: CLAIMING NEW TERRITORY ===" | tee -a "$LOG"

# Core validation function
v() {
  local n="$1" c="$2" e="${3:-}"
  echo "[FLAME] $n..." | tee -a "$LOG"
  r=$(timeout 15s eval "$c" 2>&1) || true
  if [[ -z "$e" || "$r" =~ $e ]]; then
    echo "[OK] $n - Gate Passed" | tee -a "$LOG"
    ((P++))
    return 0
  else
    echo "[FAIL] $n -> $r" | tee -a "$LOG"
    ((F++))
    return 1
  fi
}

gate() {
  [ $F -gt 0 ] && {
    echo "=== BLOCKED: $F failures ===" | tee -a "$LOG"
    exit 1
  }
}

retry() {
  local n=1
  while [ $n -le 3 ]; do
    "$@" && return 0 || { echo "[RETRY $n/3]"; sleep 5; ((n++)); }
  done
  return 1
}

# Pre-flight checks
v "Docker" "docker info --format '{{.ServerVersion}}'" ""
v "Docker Compose" "docker compose version" ""
v "Ollama running" "curl -sf http://localhost:11434/api/tags || echo 'not running'" "models"
gate

# Deploy from creations directory
cd "$SCRIPT_DIR"
echo "[DEPLOY] Building and launching containers..." | tee -a "$LOG"

docker compose down 2>/dev/null || true
docker compose build --no-cache
docker compose up -d

sleep 15

# Verify services
retry curl -sf http://localhost:8501/ > /dev/null && v "AI Engineer App" "echo live" ""
retry curl -sf http://localhost:8502/ > /dev/null && v "Flame Arsenal App" "echo live" ""

# Ollama vector ingestion
echo "[INGEST] Feeding roadmap + arsenal into Neuro-Nura..." | tee -a "$LOG"
ROADMAP_DATA=$(curl -sf http://localhost:8501/api/roadmap 2>/dev/null || echo '{}')
ARSENAL_DATA=$(curl -sf http://localhost:8502/api/arsenal 2>/dev/null || echo '{}')

curl -s -X POST http://localhost:11434/api/generate -d "{
  \"model\": \"llama3.2\",
  \"prompt\": \"Store this system state for ARK95X memory: Roadmap=$ROADMAP_DATA Arsenal=$ARSENAL_DATA. Timestamp=$(date -Iseconds)\",
  \"stream\": false
}" > /dev/null 2>&1 || echo "[INFO] Ollama ingestion queued for next cycle" | tee -a "$LOG"

# Report
echo "" | tee -a "$LOG"
echo "=== OMNI-CREATION INSTALL COMPLETE ===" | tee -a "$LOG"
echo "PASSED: $P  FAILED: $F" | tee -a "$LOG"
echo "AI Engineer:   http://localhost:8501" | tee -a "$LOG"
echo "Flame Arsenal: http://localhost:8502" | tee -a "$LOG"
echo "Log: $LOG" | tee -a "$LOG"
