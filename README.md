# ARK95X Omnikernel Orchestrator

Autonomous multi-agent orchestration engine with self-healing, adaptive routing, DAG pipelines, and real-time telemetry.

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repo
git clone https://github.com/Ark95x-sAn/ark95x-omnikernel-orchestrator.git
cd ark95x-omnikernel-orchestrator

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Launch full stack
docker-compose up -d

# Check status
curl http://localhost:8000/status
```

### Option 2: Local Python

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run with API server
python main.py --api

# Or run standalone
python main.py
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Full system status |
| `/health` | GET | Health check for all subsystems |
| `/metrics` | GET | Real-time performance metrics |
| `/task` | POST | Submit a task to the orchestrator |

## Architecture

```
src/
  core/
    orchestrator.py    # Adaptive agent scheduling engine
    self_healing.py    # Circuit breakers & auto-recovery
    pipeline_manager.py # DAG task pipelines
    telemetry.py       # Metrics & alerting
    config.py          # Centralized configuration
  models/              # AI model integration (Ollama/OpenAI)
  agents/              # Agent implementations
  slvss/               # SLVSS chamber system
```

## Stack

- **Runtime**: Python 3.11 + FastAPI + Uvicorn
- **AI Models**: Ollama (local) + OpenAI (fallback)
- **Vector Store**: Qdrant
- **Cache/Queue**: Redis
- **Container**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

## Configuration

All settings can be configured via:
1. `.env` file (environment variables)
2. JSON config file (`--config path/to/config.json`)
3. Environment variable overrides (`ARK95X_SECTION__KEY=value`)

## License

MIT
