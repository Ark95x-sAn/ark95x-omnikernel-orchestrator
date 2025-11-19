#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# ARK95X DEPLOYMENT TEST SCRIPT
# ═══════════════════════════════════════════════════════════════
# Tests all components after deployment
# ═══════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROD_DIR="$HOME/ark95x-production"
BASE_DIR="$HOME/ark95x-complete"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         ARK95X DEPLOYMENT VALIDATION TESTS             ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

test_component() {
    local name="$1"
    local command="$2"

    echo -ne "${YELLOW}Testing${NC} $name... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 1: Directory Structure
test_component "Directory structure" "test -d '$BASE_DIR' && test -d '$PROD_DIR'"

# Test 2: Ollama Installation
test_component "Ollama installation" "command -v ollama"

# Test 3: Ollama Service
test_component "Ollama service" "pgrep -x ollama"

# Test 4: Python Installation
test_component "Python 3" "command -v python3"

# Test 5: Python Scripts Exist
test_component "API Key Manager" "test -f '$PROD_DIR/backend/api_key_manager.py'"
test_component "Unified Gateway" "test -f '$PROD_DIR/backend/unified_api_gateway.py'"
test_component "Health Monitor" "test -f '$PROD_DIR/backend/health_monitor.py'"

# Test 6: Shell Scripts Exist
test_component "Start script" "test -x '$BASE_DIR/scripts/start_ark95x.sh'"
test_component "Stop script" "test -x '$BASE_DIR/scripts/stop_ark95x.sh'"
test_component "Backup script" "test -x '$BASE_DIR/scripts/backup_ark95x.sh'"

# Test 7: Models Installed
test_component "Llama 3.2 model" "ollama list | grep -q 'llama3.2:3b'"
test_component "DeepSeek R1 model" "ollama list | grep -q 'deepseek-r1:7b'"
test_component "Qwen Coder model" "ollama list | grep -q 'qwen2.5-coder:7b'"

# Test 8: Python Script Syntax
test_component "API Manager syntax" "python3 -m py_compile '$PROD_DIR/backend/api_key_manager.py'"
test_component "Gateway syntax" "python3 -m py_compile '$PROD_DIR/backend/unified_api_gateway.py'"
test_component "Health Monitor syntax" "python3 -m py_compile '$PROD_DIR/backend/health_monitor.py'"

# Test 9: Configuration Files
test_component "API Keys config" "test -f '$PROD_DIR/configs/api_keys.json'"
test_component "Environment template" "test -f '$BASE_DIR/configs/environment.template'"

# Test 10: Documentation
test_component "README" "test -f '$BASE_DIR/README.md'"
test_component "Quick Start guide" "test -f '$HOME/ARK95X_QUICK_START.txt'"

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo -e "${CYAN}System is ready to use. Start with:${NC}"
    echo -e "${YELLOW}  ~/ark95x-complete/scripts/start_ark95x.sh${NC}"
    exit 0
else
    echo -e "${RED}⚠ SOME TESTS FAILED${NC}"
    echo -e "${YELLOW}Please review the deployment logs and re-run deployment if needed.${NC}"
    exit 1
fi
