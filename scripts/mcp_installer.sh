#!/usr/bin/env bash
# ARK95X MCP ONE-CLICK INSTALLER v1.2
# Fixes: Git URL, extras key, error handling, npx check
# Added: ARM detection, smoke test, ARK95X config
set -euo pipefail

WORKSPACE="$HOME/ark95x-workspace/mcp-core"
LOG="$HOME/mcp_install_$(date +%s).log"
P=0; F=0

v() {
  local n="$1" c="$2" e="$3" r
  r=$(eval "$c" 2>&1) || true
  if echo "$r" | grep -Eqi "$e"; then
    echo "[OK] $n" | tee -a "$LOG"; ((P++))
  else
    echo "[FAIL] $n -> $r" | tee -a "$LOG"; ((F++))
  fi
}

gate() {
  if [ "$F" -gt 0 ]; then
    echo "=== GATE FAILED: $F checks ==="
    exit 1
  fi
}

echo "=== STAGE 1: PREFLIGHT ===" | tee -a "$LOG"
v "Python 3.10+" "python3 --version" "Python 3.1[0-9]"
v "Git" "git --version" "git version"
v "Node/npx" "npx --version" "^[0-9]"
gate

echo "" | tee -a "$LOG"
echo "=== ARM DETECTION ===" | tee -a "$LOG"
ARCH=$(uname -m)
case "$ARCH" in
  aarch64|arm64) echo "Detected: ARM64" | tee -a "$LOG" ;;
  x86_64|amd64) echo "Detected: x86_64" | tee -a "$LOG" ;;
  *) echo "Unknown: $ARCH" | tee -a "$LOG" ;;
esac

echo "" | tee -a "$LOG"
echo "=== STAGE 2: SETUP ===" | tee -a "$LOG"
mkdir -p "$WORKSPACE" && cd "$WORKSPACE"

if [ ! -d ".git" ]; then
  git clone https://github.com/modelcontextprotocol/python-sdk.git . 2>&1 | tee -a "$LOG"
else
  git pull origin main 2>&1 | tee -a "$LOG"
fi

python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip 2>&1 | tee -a "$LOG"

if pip install -q -e ".[cli]" aiohttp 2>&1 | tee -a "$LOG"; then
  echo "SDK installed from repo" | tee -a "$LOG"
elif pip install -q mcp aiohttp 2>&1 | tee -a "$LOG"; then
  echo "SDK installed from PyPI" | tee -a "$LOG"
else
  echo "FAIL: MCP SDK install failed" | tee -a "$LOG"
  ((F++))
fi

v "MCP SDK" "python3 -c 'import mcp; print(mcp.__version__)'" "[0-9]"
gate

echo "" | tee -a "$LOG"
echo "=== STAGE 3: CONFIG ===" | tee -a "$LOG"
cat > mcp_config.json << 'EOF'
{
  "mcpServers": {
    "everything": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-everything"]
    },
    "ark95x-local": {
      "command": "python3",
      "args": ["-m", "mcp.server"],
      "env": {"OLLAMA_URL": "http://localhost:11434"}
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
    }
  }
}
EOF

v "Config" "cat mcp_config.json" "mcpServers"
gate

echo "" | tee -a "$LOG"
echo "=== STAGE 4: SMOKE TEST ===" | tee -a "$LOG"
python3 -c 'import mcp; print(f"MCP {mcp.__version__}: OK")'
v "Smoke test" "python3 -c 'import mcp; print(\"OK\")'" "OK"
gate

echo "" | tee -a "$LOG"
echo "=== MCP INSTALL COMPLETE v1.2 ===" | tee -a "$LOG"
echo "Passed: $P  Failed: $F" | tee -a "$LOG"
echo "Arch: $ARCH" | tee -a "$LOG"
echo "Workspace: $WORKSPACE" | tee -a "$LOG"
echo "Log: $LOG" | tee -a "$LOG"
echo "NEXT: source $WORKSPACE/venv/bin/activate" | tee -a "$LOG"
