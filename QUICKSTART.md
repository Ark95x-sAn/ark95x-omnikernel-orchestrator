# ARK95X Quick Start Guide

Get your sovereign AI intelligence system running in minutes!

## Prerequisites

- Linux system (Ubuntu/Debian recommended)
- 16GB+ RAM (for local models)
- 20GB+ free disk space
- Internet connection for downloading models
- sudo/root access (for installing system packages)

## Installation

### One-Command Deploy

```bash
cd ark95x-omnikernel-orchestrator
./ark95x_ultimate_deploy.sh
```

The deployment script will automatically:

1. ✅ Install system prerequisites (Python, Docker, Git, Ollama)
2. ✅ Download and configure 3 optimized AI models (~10GB)
3. ✅ Set up API key management system
4. ✅ Deploy Partisan Intelligence routing engine
5. ✅ Configure FastAPI server
6. ✅ Create monitoring and management tools
7. ✅ Generate documentation

**Estimated time:** 15-30 minutes (depending on your internet speed)

## Post-Installation

### 1. Start All Services

```bash
~/ark95x-complete/scripts/start_all.sh
```

This starts:
- Ollama local AI server (port 11434)
- ARK95X API server (port 8000)
- Health monitoring daemon

### 2. Verify Installation

```bash
# Check service status
~/ark95x-complete/scripts/status.sh

# Run system tests
~/ark95x-complete/scripts/test_system.py

# Check API health
curl http://localhost:8000/health
```

### 3. Try Your First Query

```bash
# Using CLI
~/ark95x-complete/scripts/ark95x_cli.py query "What is artificial intelligence?"

# Using curl
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing", "task_type": "general"}'
```

## Common Commands

### Service Management

```bash
# Start all services
~/ark95x-complete/scripts/start_all.sh

# Stop all services
~/ark95x-complete/scripts/stop_all.sh

# Check status
~/ark95x-complete/scripts/status.sh
```

### Using the CLI

```bash
# General query
~/ark95x-complete/scripts/ark95x_cli.py query "Your question here"

# Code generation
~/ark95x-complete/scripts/ark95x_cli.py query "Write a Python web scraper" --type code

# Advanced reasoning
~/ark95x-complete/scripts/ark95x_cli.py query "Analyze this problem" --type reasoning

# Force local models only (no cloud API calls)
~/ark95x-complete/scripts/ark95x_cli.py query "Explain Docker" --local

# System status
~/ark95x-complete/scripts/ark95x_cli.py status

# List models
~/ark95x-complete/scripts/ark95x_cli.py models
```

### Using the REST API

```bash
# API documentation (in browser)
http://localhost:8000/docs

# Health check
curl http://localhost:8000/health

# System status
curl http://localhost:8000/status | python3 -m json.tool

# Send query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Your question",
    "task_type": "general",
    "force_local": false
  }'

# List available models
curl http://localhost:8000/models

# API key statistics
curl http://localhost:8000/api-keys/stats
```

## Architecture Overview

```
User
  ↓
ARK95X API (FastAPI) :8000
  ↓
Partisan Intelligence Router
  ├─→ Local Ollama :11434
  │   ├─ llama3.2:3b (general)
  │   ├─ deepseek-r1:7b (reasoning)
  │   └─ qwen2.5-coder:7b (code)
  │
  └─→ Cloud APIs
      ├─ OpenAI (GPT-4)
      ├─ Anthropic (Claude)
      ├─ Grok (xAI)
      └─ Perplexity (search)
```

## Task Routing

The system automatically routes queries to the best model:

| Your Task Type | Primary Model | Fallback | Best For |
|----------------|---------------|----------|----------|
| `code` | qwen2.5-coder:7b | OpenAI | Code generation, review, debugging |
| `reasoning` | deepseek-r1:7b | Anthropic | Analysis, problem-solving |
| `general` | llama3.2:3b | Grok | General questions, chat |
| `research` | Perplexity | llama3.2:3b | Current events, research |

## Configuration

### Update API Keys

1. Edit the key setup script:
```bash
nano ~/ark95x-complete/scripts/setup_api_keys.py
```

2. Update the `keys_to_add` dictionary with your keys

3. Run the setup:
```bash
python3 ~/ark95x-complete/scripts/setup_api_keys.py
```

### Configure Models

To add or remove models:

```bash
# List current models
ollama list

# Pull new model
ollama pull <model-name>

# Remove model
ollama rm <model-name>
```

## Monitoring

### View Logs

```bash
# Deployment log
tail -f ~/ark95x-complete/logs/deployment_*.log

# Ollama log
tail -f ~/ark95x-complete/logs/ollama.log

# API server log
tail -f ~/ark95x-complete/logs/api_server.log

# Health monitor log
tail -f ~/ark95x-complete/logs/health_*.log
```

### Real-time Status

```bash
# Watch system status (refreshes every 2 seconds)
watch -n 2 "curl -s http://localhost:8000/status | python3 -m json.tool"
```

## Troubleshooting

### Services Won't Start

```bash
# Check if ports are in use
lsof -i :8000  # API server
lsof -i :11434 # Ollama

# Kill conflicting processes
pkill -f main_server.py
pkill ollama

# Restart services
~/ark95x-complete/scripts/start_all.sh
```

### Ollama Not Responding

```bash
# Restart Ollama
pkill ollama
ollama serve &

# Check if models are installed
ollama list

# Re-pull models if needed
ollama pull llama3.2:3b
ollama pull deepseek-r1:7b
ollama pull qwen2.5-coder:7b
```

### API Server Errors

```bash
# Check logs for errors
tail -50 ~/ark95x-complete/logs/api_server.log

# Start manually to see errors
cd ~/ark95x-production/backend
python3 main_server.py
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R $USER:$USER ~/ark95x-complete ~/ark95x-production

# Fix permissions
chmod +x ~/ark95x-complete/scripts/*.sh
chmod +x ~/ark95x-complete/scripts/*.py
```

## Docker Alternative

If you prefer Docker deployment:

```bash
cd ~/ark95x-production
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

## Systemd Service (Auto-start on Boot)

To run ARK95X as a system service:

```bash
# Install service
~/ark95x-complete/scripts/install_service.sh

# Manage service
sudo systemctl start ark95x
sudo systemctl enable ark95x
sudo systemctl status ark95x
```

## Performance Tips

### Speed Optimization

- **Use local models** for fast, offline responses (add `--local` flag)
- **Small model for simple tasks** - llama3.2:3b is fastest
- **Enable GPU** - If you have NVIDIA GPU, configure Ollama to use it
- **Increase context** - Set `OLLAMA_NUM_CTX=4096` for larger contexts

### Cost Optimization

- **Default to local** - Set `force_local: true` to avoid API costs
- **Monitor usage** - Check `curl http://localhost:8000/api-keys/stats`
- **Use task types** - Correct routing reduces cloud API calls

## Next Steps

1. ✅ Explore the API documentation: http://localhost:8000/docs
2. ✅ Read the full README: `~/ark95x-complete/README.md`
3. ✅ Try different task types to see intelligent routing
4. ✅ Monitor your system with the health dashboard
5. ✅ Integrate ARK95X into your applications via REST API

## Getting Help

- Check logs: `~/ark95x-complete/logs/`
- Run status: `~/ark95x-complete/scripts/status.sh`
- Run tests: `~/ark95x-complete/scripts/test_system.py`
- Full documentation: `README.md`

## Example Use Cases

### Code Development
```bash
# Generate code
ark95x_cli.py query "Create a Flask REST API with authentication" --type code

# Debug code
ark95x_cli.py query "Why am I getting 'NoneType' error in Python?" --type code

# Code review
ark95x_cli.py query "Review this function for security issues: [paste code]" --type code
```

### Research & Analysis
```bash
# Current events
ark95x_cli.py query "Latest AI developments in 2025" --type research

# Analysis
ark95x_cli.py query "Compare microservices vs monolithic architecture" --type reasoning

# Technical concepts
ark95x_cli.py query "Explain Kubernetes architecture" --type general
```

### Automation
```bash
# Integrate into scripts
RESPONSE=$(curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize this log: [log content]", "task_type": "general"}')

echo $RESPONSE | python3 -m json.tool
```

---

**You're ready to go!** 🚀

For more detailed information, see [README.md](README.md)

**ARK95X OmniKernel Orchestrator** - Your Sovereign AI Intelligence System
