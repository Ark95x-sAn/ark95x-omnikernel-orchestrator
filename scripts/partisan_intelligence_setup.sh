#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# PARTISAN INTELLIGENCE INTEGRATION SETUP
# ═══════════════════════════════════════════════════════════════
# Integrates the Partisan Intelligence system with ARK95X
# ═══════════════════════════════════════════════════════════════

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

BASE_DIR="$HOME/ark95x-complete"
PI_DIR="$BASE_DIR/partisan-intelligence"
REPO_URL="https://github.com/Ark95x-sAn/openai-assistants-quickstart.git"
BRANCH="claude/partisan-intelligence-01SVpXFVayXkCFEruDcyYoSZ"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      PARTISAN INTELLIGENCE INTEGRATION SETUP           ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create directory
mkdir -p "$BASE_DIR"

# Clone or update repository
if [ -d "$PI_DIR" ]; then
    echo -e "${YELLOW}→${NC} Updating existing Partisan Intelligence repository..."
    cd "$PI_DIR"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
    echo -e "${GREEN}✓${NC} Repository updated"
else
    echo -e "${BLUE}→${NC} Cloning Partisan Intelligence repository..."
    cd "$BASE_DIR"
    git clone "$REPO_URL" partisan-intelligence
    cd partisan-intelligence
    git checkout "$BRANCH"
    echo -e "${GREEN}✓${NC} Repository cloned"
fi

# Install dependencies if package.json exists
if [ -f "$PI_DIR/package.json" ]; then
    echo -e "${BLUE}→${NC} Installing Node.js dependencies..."
    cd "$PI_DIR"
    npm install
    echo -e "${GREEN}✓${NC} Dependencies installed"
fi

# Create integration bridge
cat > "$BASE_DIR/scripts/pi_bridge.py" << 'EOBRIDGE'
#!/usr/bin/env python3
"""
Partisan Intelligence Bridge
Integrates PI system with ARK95X Gateway
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "ark95x-production" / "backend"))

from unified_api_gateway import gateway
import json

class PartisanIntelligenceBridge:
    """Bridge between ARK95X and Partisan Intelligence"""

    def __init__(self):
        self.gateway = gateway
        self.pi_dir = Path.home() / "ark95x-complete" / "partisan-intelligence"

    def query_with_pi_context(self, prompt: str, context: dict = None) -> dict:
        """
        Query AI with Partisan Intelligence context

        Args:
            prompt: The user query
            context: Additional context from PI system

        Returns:
            AI response with PI integration
        """
        enhanced_prompt = prompt

        if context:
            enhanced_prompt = f"Context: {json.dumps(context)}\n\nQuery: {prompt}"

        # Use intelligent routing
        result = self.gateway.intelligent_route(enhanced_prompt, preference="local")

        return {
            "success": result["success"],
            "response": result.get("response", ""),
            "source": result.get("source", "unknown"),
            "context_used": context is not None
        }

    def multi_model_consensus(self, prompt: str) -> dict:
        """
        Get consensus from multiple models

        Args:
            prompt: The query to ask multiple models

        Returns:
            Aggregated responses from multiple models
        """
        responses = []

        # Query local models
        for model in ["llama3.2:3b", "deepseek-r1:7b"]:
            result = self.gateway.query_ollama(model, prompt)
            if result["success"]:
                responses.append({
                    "model": model,
                    "response": result["response"],
                    "source": "local"
                })

        # Query cloud if configured
        cloud_result = self.gateway.query_anthropic(prompt)
        if cloud_result["success"]:
            responses.append({
                "model": "claude",
                "response": cloud_result["response"],
                "source": "cloud"
            })

        return {
            "success": len(responses) > 0,
            "responses": responses,
            "consensus_count": len(responses)
        }

# Global bridge instance
pi_bridge = PartisanIntelligenceBridge()

if __name__ == "__main__":
    print("🌐 Partisan Intelligence Bridge initialized")

    # Test query
    result = pi_bridge.query_with_pi_context("What is AI?")
    print(f"\nTest query result:")
    print(f"  Success: {result['success']}")
    print(f"  Source: {result['source']}")
    print(f"  Response: {result['response'][:100]}...")
EOBRIDGE

chmod +x "$BASE_DIR/scripts/pi_bridge.py"

echo -e "${GREEN}✓${NC} Integration bridge created"

# Create configuration
cat > "$BASE_DIR/configs/partisan_intelligence.yaml" << 'EOCONFIG'
# Partisan Intelligence Configuration

# Integration Settings
integration:
  enabled: true
  bridge_mode: "hybrid"  # local, cloud, hybrid
  fallback_enabled: true

# Model Preferences
models:
  primary: "llama3.2:3b"
  reasoning: "deepseek-r1:7b"
  coding: "qwen2.5-coder:7b"
  cloud_fallback: "claude"

# Features
features:
  multi_model_consensus: true
  context_enhancement: true
  intelligent_routing: true
  failover: true

# Performance
performance:
  timeout_seconds: 30
  max_retries: 3
  cache_enabled: true
  cache_ttl_minutes: 60

# Logging
logging:
  level: "INFO"
  file: "partisan_intelligence.log"
  max_size_mb: 100
  retention_days: 30
EOCONFIG

echo -e "${GREEN}✓${NC} Configuration created"

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Partisan Intelligence Integration Complete${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Location:${NC} $PI_DIR"
echo -e "${YELLOW}Bridge:${NC} $BASE_DIR/scripts/pi_bridge.py"
echo -e "${YELLOW}Config:${NC} $BASE_DIR/configs/partisan_intelligence.yaml"
echo ""
echo -e "${CYAN}Test the bridge:${NC}"
echo -e "${YELLOW}  python3 $BASE_DIR/scripts/pi_bridge.py${NC}"
echo ""
