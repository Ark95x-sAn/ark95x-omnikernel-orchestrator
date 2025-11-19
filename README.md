# ARK95X OmniKernel Orchestrator

**Sovereign AI Intelligence System** - Complete deployment package for local + cloud AI orchestration

## 🎯 What Is This?

ARK95X Ultimate Deployment is a one-command solution that deploys a complete AI intelligence infrastructure combining:

- **Local AI** via Ollama (private, fast, no API costs)
- **Cloud AI** via OpenAI, Anthropic, Grok, Perplexity (powerful, specialized)
- **Intelligent Routing** that picks the best model for each task
- **API Management** for key rotation and usage tracking
- **Health Monitoring** for 24/7 system oversight

## 🚀 One-Command Deployment

```bash
./ark95x_ultimate_deploy.sh
```

That's it! The script will:
1. Install all prerequisites (Python, Docker, Ollama)
2. Download and configure AI models (~10GB)
3. Set up API key management
4. Deploy the Partisan Intelligence routing system
5. Create monitoring and management tools
6. Generate complete documentation

**Time:** ~15-30 minutes (depending on download speeds)

## 📦 What Gets Installed

### Local AI Models (Ollama)
- **llama3.2:3b** (2GB) - Fast general-purpose model
- **deepseek-r1:7b** (4GB) - Advanced reasoning and analysis
- **qwen2.5-coder:7b** (4GB) - Code generation and review

### Cloud AI Providers
- **OpenAI** - GPT-4 for complex reasoning
- **Anthropic** - Claude for analysis and writing
- **Grok** - xAI models for diverse tasks
- **Perplexity** - Research and real-time information

### Infrastructure
- FastAPI REST API server (Port 8000)
- Partisan Intelligence routing engine
- API key management system
- Health monitoring daemon
- Command-line interface (CLI)
- Docker configuration
- Systemd service files

## 🎮 Usage After Deployment

### Start the System
```bash
~/ark95x-complete/scripts/start_all.sh
```

### Check Status
```bash
~/ark95x-complete/scripts/status.sh
```

### Use the CLI
```bash
# Ask a general question
~/ark95x-complete/scripts/ark95x_cli.py query "What is quantum computing?"

# Code-specific query
~/ark95x-complete/scripts/ark95x_cli.py query "Write a Python function to sort a list" --type code

# Force local models only (no API calls)
~/ark95x-complete/scripts/ark95x_cli.py query "Explain Docker" --local

# Check system status
~/ark95x-complete/scripts/ark95x_cli.py status

# List all models
~/ark95x-complete/scripts/ark95x_cli.py models
```

### Use the REST API
```bash
# Send a query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain AI", "task_type": "general"}'

# Get system status
curl http://localhost:8000/status | python3 -m json.tool

# Check health
curl http://localhost:8000/health

# List models
curl http://localhost:8000/models

# View API documentation
open http://localhost:8000/docs
```

## 🧠 Intelligent Routing

The Partisan Intelligence system automatically routes queries to the optimal model:

| Task Type | Primary Model | Fallback | Use Case |
|-----------|---------------|----------|----------|
| **code** | qwen2.5-coder:7b | OpenAI | Programming, debugging, code review |
| **reasoning** | deepseek-r1:7b | Anthropic | Analysis, problem-solving, logic |
| **general** | llama3.2:3b | Grok | General questions, conversation |
| **research** | Perplexity | llama3.2:3b | Current events, research queries |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              User Applications & Clients                 │
│         (CLI, REST API, Web UI, Scripts)                │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │   ARK95X API Server     │
        │   FastAPI (Port 8000)   │
        └────────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │ Partisan Intelligence    │
        │  Routing Engine         │
        └───┬──────────────────┬───┘
            │                  │
    ┌───────┴────────┐   ┌────┴──────────┐
    │  Local Ollama  │   │  Cloud APIs   │
    │  Port 11434    │   │               │
    ├────────────────┤   ├───────────────┤
    │ llama3.2:3b    │   │ OpenAI GPT-4  │
    │ deepseek-r1:7b │   │ Anthropic     │
    │ qwen-coder:7b  │   │ Grok xAI      │
    │                │   │ Perplexity    │
    └────────────────┘   └───────────────┘
```

## 📁 Directory Structure

After deployment, you'll have:

```
~/ark95x-complete/               # Main installation directory
├── logs/                        # All system logs
│   ├── deployment_*.log         # Deployment logs
│   ├── ollama.log              # Ollama service logs
│   ├── api_server.log          # API server logs
│   └── health_*.log            # Health monitoring logs
├── scripts/                     # Utility scripts
│   ├── start_all.sh            # Start all services
│   ├── stop_all.sh             # Stop all services
│   ├── status.sh               # Check system status
│   ├── setup_api_keys.py       # Configure API keys
│   ├── health_monitor.py       # Health monitoring daemon
│   ├── test_system.py          # System tests
│   └── ark95x_cli.py           # Command-line interface
├── configs/                     # Configuration files
├── data/                        # Data storage
└── backups/                     # Backup directory

~/ark95x-production/             # Production deployment
├── backend/                     # Backend services
│   ├── main_server.py          # Main FastAPI server
│   ├── api_key_manager.py      # API key management
│   ├── partisan_intelligence.py # Routing engine
│   ├── requirements.txt        # Python dependencies
│   └── Dockerfile              # Docker build file
├── configs/                     # Production configs
│   └── api_keys.json           # Encrypted API keys
├── data/                        # Production data
└── docker-compose.yml          # Docker orchestration
```

## 🔐 API Key Configuration

API keys are configured during deployment. To update them:

1. Edit `~/ark95x-complete/scripts/setup_api_keys.py`
2. Add/update keys in the `keys_to_add` dictionary
3. Run: `python3 ~/ark95x-complete/scripts/setup_api_keys.py`

Keys are base64 encoded and stored in `~/ark95x-production/configs/api_keys.json`

**Security Note:** For production, upgrade to AES-256 encryption.

## 📊 Monitoring

### Health Monitor
Automatically started with the system:
- Checks API server health every 60 seconds
- Monitors Ollama service status
- Logs to `~/ark95x-complete/logs/health_*.log`

### Manual Status Check
```bash
~/ark95x-complete/scripts/status.sh
```

### API Status Endpoint
```bash
curl http://localhost:8000/status | python3 -m json.tool
```

## 🧪 Testing

Run the complete test suite:
```bash
~/ark95x-complete/scripts/test_system.py
```

Tests include:
- API health check
- System status verification
- Model availability
- Query routing
- Response validation

## 🐳 Docker Deployment

For containerized deployment:

```bash
cd ~/ark95x-production
docker-compose up -d
```

This starts:
- `ark95x-api` - The API server
- `ark95x-ollama` - Ollama service with persistent storage

View logs:
```bash
docker-compose logs -f
```

Stop containers:
```bash
docker-compose down
```

## 🔧 Systemd Service (Optional)

To run ARK95X as a system service:

```bash
~/ark95x-complete/scripts/install_service.sh
```

Then manage with systemd:
```bash
sudo systemctl start ark95x    # Start service
sudo systemctl stop ark95x     # Stop service
sudo systemctl status ark95x   # Check status
sudo systemctl enable ark95x   # Start on boot
```

## 🆘 Troubleshooting

### Ollama Not Responding
```bash
# Check if running
pgrep ollama

# Restart service
pkill ollama
ollama serve

# Check logs
tail -f ~/ark95x-complete/logs/ollama.log
```

### API Server Won't Start
```bash
# Check if port is in use
lsof -i :8000

# Start manually to see errors
cd ~/ark95x-production/backend
python3 main_server.py

# Check logs
tail -f ~/ark95x-complete/logs/api_server.log
```

### Models Not Available
```bash
# List installed models
ollama list

# Pull missing models
ollama pull llama3.2:3b
ollama pull deepseek-r1:7b
ollama pull qwen2.5-coder:7b
```

### Permission Errors
```bash
# Ensure correct ownership
sudo chown -R $USER:$USER ~/ark95x-complete ~/ark95x-production

# Make scripts executable
chmod +x ~/ark95x-complete/scripts/*.sh
chmod +x ~/ark95x-complete/scripts/*.py
```

## 📈 Performance Tips

### Speed Up Local Models
- Use smaller models for faster responses (llama3.2:3b)
- Enable GPU acceleration if available
- Increase Ollama context size: `OLLAMA_NUM_CTX=4096`

### Optimize Cloud Usage
- Use `--local` flag to avoid API costs
- Set task types correctly for better routing
- Monitor usage: `curl http://localhost:8000/api-keys/stats`

### Resource Management
```bash
# Check Ollama memory usage
ps aux | grep ollama

# Limit concurrent requests
# Edit ~/ark95x-production/backend/main_server.py
# Set workers in uvicorn.run()
```

## 🔄 Updates & Maintenance

### Update Models
```bash
ollama pull llama3.2:3b
ollama pull deepseek-r1:7b
ollama pull qwen2.5-coder:7b
```

### Update Python Dependencies
```bash
pip3 install --upgrade -r ~/ark95x-production/backend/requirements.txt
```

### Backup Configuration
```bash
# Backup API keys and configs
tar -czf ~/ark95x-backup-$(date +%Y%m%d).tar.gz \
  ~/ark95x-production/configs \
  ~/ark95x-complete/configs
```

## 🎯 Use Cases

### Software Development
```bash
# Code generation
ark95x_cli.py query "Create a REST API in Python" --type code

# Code review
ark95x_cli.py query "Review this function: [code]" --type code

# Debugging
ark95x_cli.py query "Why does this error occur: [error]" --type code
```

### Research & Analysis
```bash
# Current events
ark95x_cli.py query "Latest developments in AI" --type research

# Deep analysis
ark95x_cli.py query "Analyze the pros and cons of microservices" --type reasoning
```

### General Assistant
```bash
# Quick questions
ark95x_cli.py query "How do I configure SSH?" --type general

# Explanations
ark95x_cli.py query "Explain Kubernetes" --type general --local
```

## 🌟 Features

✅ **Multi-Provider Support** - Seamlessly use 7+ AI models
✅ **Intelligent Routing** - Automatic best-model selection
✅ **Cost Optimization** - Prefer local models, fall back to cloud
✅ **API Key Rotation** - Automatic key management and rotation
✅ **Health Monitoring** - 24/7 system health tracking
✅ **REST API** - Full-featured HTTP API
✅ **CLI Tool** - Easy command-line access
✅ **Docker Ready** - Complete containerization support
✅ **Production Ready** - Systemd service, logging, monitoring
✅ **Extensible** - Easy to add new models and providers

## 📞 Support & Resources

- **Documentation**: `~/ark95x-complete/README.md`
- **Logs**: `~/ark95x-complete/logs/`
- **API Docs**: http://localhost:8000/docs
- **Status Check**: `~/ark95x-complete/scripts/status.sh`

## 📝 License

This deployment system is provided as-is for the ARK95X project.

## 🙏 Credits

- **Ollama** - Local AI inference
- **FastAPI** - High-performance API framework
- **OpenAI, Anthropic, xAI, Perplexity** - Cloud AI providers

---

**ARK95X OmniKernel Orchestrator** - Sovereign Intelligence at Your Command 🚀
