# 🔥 ARK95X Omnikernel Orchestrator

## Sovereign AI Intelligence System - Complete Deployment Package

<div align="center">

**Local Control • Cloud Power • Infinite Possibilities**

[![License](https://img.shields.io/badge/license-Private-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Production%20Ready-green.svg)]()
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey.svg)]()

</div>

---

## 🎯 What is ARK95X?

ARK95X is a complete AI orchestration system that combines **local AI models** (Ollama) with **cloud-based APIs** (OpenAI, Anthropic, Grok, Perplexity) into a unified, intelligent gateway with automatic failover, API key rotation, and comprehensive monitoring.

Originally designed for restaurant operations automation, now evolved into a sovereign AI intelligence system.

### Key Features

- 🤖 **Multi-Model Support**: 3 local models + 4 cloud providers
- 🔀 **Intelligent Routing**: Automatically selects best available AI
- 🔑 **API Key Management**: Round-robin rotation with failover
- 🏥 **Health Monitoring**: Real-time system and AI status
- 🚀 **One-Command Deploy**: Complete installation in 20-40 minutes
- 🔒 **Privacy-First**: Local models for sensitive queries
- ♾️ **Unlimited**: No API costs for local models
- 📊 **Production-Ready**: Logging, backups, auto-restart

---

## 🚀 Quick Start

### One-Command Installation

```bash
chmod +x scripts/ark95x_ultimate_deploy.sh
./scripts/ark95x_ultimate_deploy.sh
```

### What Gets Installed

1. ✅ **Ollama Local AI** - Privacy-focused local inference
2. ✅ **3 AI Models**:
   - llama3.2:3b (Fast general purpose)
   - deepseek-r1:7b (Advanced reasoning)
   - qwen2.5-coder:7b (Code specialist)
3. ✅ **API Key Manager** - Multi-key rotation & failover
4. ✅ **Unified AI Gateway** - Intelligent model routing
5. ✅ **Health Monitor** - System status & auto-recovery
6. ✅ **Auto-start Scripts** - Easy system management
7. ✅ **Complete Documentation** - Guides & examples

**Installation Time**: 20-40 minutes (depending on internet speed)

---

## 📦 What's Included

```
ark95x-omnikernel-orchestrator/
├── scripts/
│   ├── ark95x_ultimate_deploy.sh      # Master deployment script
│   ├── test_deployment.sh              # Validation tests
│   ├── partisan_intelligence_setup.sh  # PI integration
│   └── monitor_system.sh               # Continuous monitoring
├── docs/
│   ├── INSTALLATION_GUIDE.md           # Complete install guide
│   ├── USER_GUIDE.md                   # Usage documentation
│   └── API_REFERENCE.md                # API documentation
├── configs/
│   └── (Configuration templates)
└── README.md                           # This file
```

**After installation creates**:

```
~/ark95x-complete/                      # Base directory
├── logs/                               # System logs
├── scripts/                            # Management scripts
├── configs/                            # Configuration files
└── partisan-intelligence/              # PI repository

~/ark95x-production/                    # Production files
├── backend/
│   ├── api_key_manager.py             # API key management
│   ├── unified_api_gateway.py         # AI routing gateway
│   └── health_monitor.py              # Health monitoring
└── configs/
    └── api_keys.json                  # Encrypted API keys
```

---

## 🎮 Usage Examples

### Start the System

```bash
~/ark95x-complete/scripts/start_ark95x.sh
```

### Quick Chat (Local AI)

```bash
ollama run llama3.2:3b "What is machine learning?"
```

### Python Usage

```python
from unified_api_gateway import gateway

# Intelligent routing (local first, cloud fallback)
result = gateway.intelligent_route(
    "Explain quantum computing in simple terms",
    preference="local"
)

print(result['response'])
```

### Health Check

```bash
python3 ~/ark95x-production/backend/health_monitor.py
```

### Run Examples

```bash
python3 ~/ark95x-complete/scripts/example_usage.py
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              ARK95X Unified AI Gateway                  │
│                                                         │
│  ┌──────────────────┐      ┌──────────────────────┐   │
│  │   Local Ollama   │      │    Cloud APIs        │   │
│  │  ┌────────────┐  │      │  ┌────────────────┐ │   │
│  │  │ llama3.2   │  │      │  │ OpenAI GPT-4   │ │   │
│  │  │ deepseek-r1│  │◄────►│  │ Claude Sonnet  │ │   │
│  │  │ qwen-coder │  │      │  │ Grok xAI       │ │   │
│  │  └────────────┘  │      │  │ Perplexity AI  │ │   │
│  └──────────────────┘      │  └────────────────┘ │   │
│                             └──────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │   API Key Manager (Rotation & Failover)         │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │   Health Monitor (Auto-restart & Alerts)        │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/INSTALLATION_GUIDE.md) | Complete installation instructions |
| [User Guide](docs/USER_GUIDE.md) | Usage examples and best practices |
| Quick Start | `cat ~/ARK95X_QUICK_START.txt` (after install) |
| System README | `cat ~/ark95x-complete/README.md` (after install) |

---

## 🔧 System Requirements

### Minimum

- **OS**: Ubuntu 20.04+ / Debian 11+ / macOS
- **RAM**: 8GB
- **Disk**: 20GB free
- **CPU**: 4 cores

### Recommended

- **RAM**: 16GB+
- **Disk**: 50GB+ SSD
- **CPU**: 8+ cores
- **GPU**: NVIDIA GPU (optional, for faster inference)

---

## 🛠️ Management Commands

```bash
# System Control
~/ark95x-complete/scripts/start_ark95x.sh    # Start system
~/ark95x-complete/scripts/stop_ark95x.sh     # Stop system
~/ark95x-complete/scripts/monitor_system.sh  # Monitor health

# Maintenance
~/ark95x-complete/scripts/backup_ark95x.sh   # Create backup
~/ark95x-complete/scripts/update_models.sh   # Update AI models
~/ark95x-complete/scripts/clean_logs.sh      # Clean old logs

# Testing
~/ark95x-complete/scripts/test_deployment.sh # Validate install
python3 ~/ark95x-complete/scripts/example_usage.py  # Examples
```

---

## 🐛 Troubleshooting

### Common Issues

**Ollama won't start**
```bash
pkill ollama
ollama serve &
```

**Models not found**
```bash
ollama pull llama3.2:3b
ollama pull deepseek-r1:7b
ollama pull qwen2.5-coder:7b
```

**Permission denied**
```bash
chmod +x scripts/*.sh
```

See [Installation Guide](docs/INSTALLATION_GUIDE.md#troubleshooting) for more.

---

## 📞 Support

### Resources

- 📖 [Installation Guide](docs/INSTALLATION_GUIDE.md)
- 📖 [User Guide](docs/USER_GUIDE.md)
- 📋 Quick Start: `cat ~/ARK95X_QUICK_START.txt`
- 🔍 Logs: `~/ark95x-complete/logs/`

---

<div align="center">

**🔥 ARK95X - Sovereign AI Intelligence System 🔥**

*One Command. Complete System. Unlimited Potential.*

**[Get Started](#-quick-start)** • **[Documentation](docs/)** • **[Examples](#-usage-examples)**

</div>

---

**Last Updated**: 2025-11-19
**Version**: 1.0.0
**Status**: Production Ready ✅
