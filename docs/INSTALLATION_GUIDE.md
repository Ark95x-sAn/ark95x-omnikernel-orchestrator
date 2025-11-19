# 🚀 ARK95X INSTALLATION GUIDE

## Complete Step-by-Step Installation Instructions

This guide will help you deploy the ARK95X Sovereign AI Intelligence System from scratch.

---

## 📋 Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04+ / Debian 11+ / macOS
- **RAM**: 8GB minimum (16GB recommended)
- **Disk Space**: 20GB free space minimum
- **CPU**: 4+ cores recommended
- **GPU**: Optional (NVIDIA GPU for faster local AI)

### Required Software

The deployment script will automatically install:
- Python 3.8+
- Docker & Docker Compose
- Git
- Ollama
- Required Python packages

---

## ⚡ Quick Installation (Recommended)

### One-Command Deploy

```bash
curl -fsSL https://raw.githubusercontent.com/Ark95x-sAn/ark95x-omnikernel-orchestrator/main/scripts/ark95x_ultimate_deploy.sh | bash
```

**OR** if you have the repository cloned:

```bash
cd /path/to/ark95x-omnikernel-orchestrator
chmod +x scripts/ark95x_ultimate_deploy.sh
./scripts/ark95x_ultimate_deploy.sh
```

### What This Does

The deployment script automatically:

1. ✅ Creates directory structure
2. ✅ Installs all prerequisites (Docker, Python, etc.)
3. ✅ Installs and starts Ollama
4. ✅ Downloads AI models (llama3.2, deepseek-r1, qwen2.5-coder)
5. ✅ Configures API key management
6. ✅ Sets up Partisan Intelligence integration
7. ✅ Creates unified AI gateway
8. ✅ Installs health monitoring
9. ✅ Creates auto-start scripts
10. ✅ Generates complete documentation
11. ✅ Validates installation

**Estimated Time**: 20-40 minutes (depending on internet speed)

---

## 🔧 Manual Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/Ark95x-sAn/ark95x-omnikernel-orchestrator.git
cd ark95x-omnikernel-orchestrator
```

### Step 2: Create Directory Structure

```bash
mkdir -p ~/ark95x-complete/{logs,scripts,configs,data,backups}
mkdir -p ~/ark95x-production/{backend,frontend,configs,data/logs}
```

### Step 3: Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Start Ollama:

```bash
ollama serve &
```

### Step 4: Install AI Models

```bash
ollama pull llama3.2:3b
ollama pull deepseek-r1:7b
ollama pull qwen2.5-coder:7b
```

### Step 5: Install Python Dependencies

```bash
pip3 install fastapi uvicorn requests pydantic aiofiles pyyaml motor pymongo redis websockets
```

### Step 6: Copy Configuration Files

```bash
# Copy all scripts from repository to ~/ark95x-complete/scripts/
cp scripts/*.sh ~/ark95x-complete/scripts/
cp scripts/*.py ~/ark95x-complete/scripts/

# Make executable
chmod +x ~/ark95x-complete/scripts/*.sh
chmod +x ~/ark95x-complete/scripts/*.py
```

### Step 7: Configure API Keys

Edit and run:

```bash
python3 ~/ark95x-complete/scripts/setup_api_keys.py
```

### Step 8: Verify Installation

```bash
bash ~/ark95x-complete/scripts/test_deployment.sh
```

---

## 🔑 API Key Configuration

### Adding Your API Keys

1. **Option A**: Edit the setup script

```bash
nano ~/ark95x-complete/scripts/setup_api_keys.py
```

Add your keys to the `keys_to_add` dictionary.

2. **Option B**: Use Python directly

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path.home() / "ark95x-production" / "backend"))
from api_key_manager import key_manager

# Add keys
key_manager.add_key("openai", "sk-your-key-here", "My OpenAI Key")
key_manager.add_key("anthropic", "sk-ant-your-key", "My Claude Key")
```

### Supported Providers

- **OpenAI** - GPT-4, GPT-3.5
- **Anthropic** - Claude 3.5 Sonnet, Claude 3 Opus
- **Grok** - xAI's Grok models
- **Perplexity** - Perplexity AI

---

## ✅ Post-Installation

### Start the System

```bash
~/ark95x-complete/scripts/start_ark95x.sh
```

### Run Health Check

```bash
python3 ~/ark95x-production/backend/health_monitor.py
```

### Test AI Gateway

```bash
python3 ~/ark95x-production/backend/unified_api_gateway.py
```

### Run Examples

```bash
python3 ~/ark95x-complete/scripts/example_usage.py
```

---

## 🐛 Troubleshooting

### Ollama Won't Start

**Problem**: `ollama serve` fails

**Solution**:
```bash
# Check if already running
pgrep ollama

# Kill existing process
pkill ollama

# Restart
ollama serve &

# Check logs
tail -f ~/ark95x-complete/logs/ollama.log
```

### Models Not Downloading

**Problem**: `ollama pull` hangs or fails

**Solution**:
```bash
# Check internet connection
ping -c 3 ollama.com

# Try manual download
ollama pull llama3.2:3b --verbose

# Check disk space
df -h
```

### Permission Denied Errors

**Problem**: Scripts won't execute

**Solution**:
```bash
# Make all scripts executable
chmod +x ~/ark95x-complete/scripts/*.sh
chmod +x ~/ark95x-complete/scripts/*.py

# Check ownership
ls -la ~/ark95x-complete/scripts/
```

### Python Module Not Found

**Problem**: Import errors when running Python scripts

**Solution**:
```bash
# Reinstall dependencies
pip3 install --upgrade fastapi uvicorn requests pydantic

# Check Python path
python3 -c "import sys; print(sys.path)"

# Use full path
python3 -m pip install fastapi uvicorn requests
```

### Docker Issues

**Problem**: Docker commands fail

**Solution**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
```

---

## 🔄 Updating

### Update Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Update Models

```bash
~/ark95x-complete/scripts/update_models.sh
```

### Update Scripts

```bash
cd /path/to/ark95x-omnikernel-orchestrator
git pull origin main
cp scripts/*.sh ~/ark95x-complete/scripts/
cp scripts/*.py ~/ark95x-complete/scripts/
```

---

## 🗑️ Uninstallation

### Remove ARK95X

```bash
# Stop services
~/ark95x-complete/scripts/stop_ark95x.sh

# Remove directories
rm -rf ~/ark95x-complete
rm -rf ~/ark95x-production

# Remove Ollama (optional)
sudo rm -rf /usr/local/bin/ollama
sudo rm -rf ~/.ollama
```

---

## 📞 Support

### Getting Help

1. **Check Logs**: `~/ark95x-complete/logs/`
2. **Run Health Check**: `python3 ~/ark95x-production/backend/health_monitor.py`
3. **Review Documentation**: `~/ark95x-complete/README.md`
4. **GitHub Issues**: Report issues on GitHub repository

### Common Paths

- **Base Directory**: `~/ark95x-complete/`
- **Production**: `~/ark95x-production/`
- **Logs**: `~/ark95x-complete/logs/`
- **Scripts**: `~/ark95x-complete/scripts/`
- **Configs**: `~/ark95x-complete/configs/`

---

## 🎉 Next Steps

After successful installation:

1. ✅ Review the [User Guide](USER_GUIDE.md)
2. ✅ Learn about [API Usage](API_REFERENCE.md)
3. ✅ Explore [Advanced Configuration](ADVANCED_CONFIG.md)
4. ✅ Set up [Auto-start on Boot](AUTOSTART_GUIDE.md)

---

**ARK95X** - Sovereign AI Intelligence System
*Installation made easy. Power at your fingertips.*
