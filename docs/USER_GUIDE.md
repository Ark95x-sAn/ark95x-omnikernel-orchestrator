# 📖 ARK95X USER GUIDE

## Complete Guide to Using the ARK95X System

---

## 🎯 Overview

ARK95X is a sovereign AI intelligence system that combines:
- **Local AI** (Ollama) - Private, fast, no API costs
- **Cloud AI** (OpenAI, Anthropic, etc.) - Powerful, advanced capabilities
- **Intelligent Routing** - Automatically uses the best available AI
- **API Management** - Handles multiple keys, failover, and rotation

---

## 🚀 Quick Start

### Start the System

```bash
~/ark95x-complete/scripts/start_ark95x.sh
```

### Check System Health

```bash
python3 ~/ark95x-production/backend/health_monitor.py
```

### Your First Query

```bash
ollama run llama3.2:3b "What is machine learning?"
```

---

## 🤖 Using AI Models

### Local Models (Ollama)

#### Llama 3.2 (Fast General Purpose)

```bash
# Command line
ollama run llama3.2:3b "Your question here"

# Python
from unified_api_gateway import gateway
result = gateway.query_ollama("llama3.2:3b", "Your question")
print(result['response'])
```

**Best For**: Quick questions, general knowledge, fast responses

#### DeepSeek R1 (Advanced Reasoning)

```bash
# Command line
ollama run deepseek-r1:7b "Analyze the pros and cons of renewable energy"

# Python
result = gateway.query_ollama("deepseek-r1:7b", "Complex reasoning task")
```

**Best For**: Complex analysis, reasoning, problem-solving

#### Qwen 2.5 Coder (Code Specialist)

```bash
# Command line
ollama run qwen2.5-coder:7b "Write a Python function to sort a list"

# Python
result = gateway.query_ollama("qwen2.5-coder:7b", "Code generation task")
```

**Best For**: Code generation, debugging, technical documentation

### Cloud APIs

#### OpenAI GPT-4

```python
from unified_api_gateway import gateway

result = gateway.query_openai("Your question here", model="gpt-4")
print(result['response'])
```

#### Anthropic Claude

```python
from unified_api_gateway import gateway

result = gateway.query_anthropic("Your question here")
print(result['response'])
```

---

## 🔀 Intelligent Routing

The unified gateway automatically selects the best AI for your task.

### Prefer Local First (Recommended)

```python
from unified_api_gateway import gateway

result = gateway.intelligent_route(
    "What is quantum computing?",
    preference="local"  # Try Ollama first
)

print(f"Response from {result['source']}: {result['response']}")
```

**How it works**:
1. Tries local Ollama first (fast, private, free)
2. Falls back to cloud APIs if local fails
3. Returns the first successful response

### Prefer Cloud

```python
result = gateway.intelligent_route(
    "Complex analysis requiring latest information",
    preference="cloud"  # Try cloud APIs first
)
```

**When to use**:
- Need latest information
- Complex reasoning beyond local models
- Specific cloud model features

---

## 🔑 API Key Management

### View Key Statistics

```python
from api_key_manager import key_manager

stats = key_manager.get_stats()
print(f"Total keys: {stats['total_keys']}")
print(f"Total requests: {stats['total_requests']}")

for provider, info in stats['by_provider'].items():
    print(f"{provider}: {info['active']}/{info['total']} active")
```

### Add New API Key

```python
from api_key_manager import key_manager

key_id = key_manager.add_key(
    provider="openai",
    api_key="sk-your-key-here",
    name="My OpenAI Key"
)
print(f"Key added with ID: {key_id}")
```

### Get Next Available Key

```python
from api_key_manager import key_manager

key_data = key_manager.get_next_key("openai")
if key_data:
    print(f"Using key: {key_data['name']}")
    # Use key_data['key'] for API calls
```

---

## 💡 Usage Examples

### Example 1: Simple Question & Answer

```python
from unified_api_gateway import gateway

result = gateway.intelligent_route(
    "Explain blockchain in simple terms",
    preference="local"
)

if result['success']:
    print(result['response'])
else:
    print(f"Error: {result['error']}")
```

### Example 2: Code Generation

```python
from unified_api_gateway import gateway

prompt = """
Write a Python function that:
1. Takes a list of numbers
2. Removes duplicates
3. Sorts in descending order
4. Returns the result
Include docstring and type hints.
"""

result = gateway.query_ollama("qwen2.5-coder:7b", prompt)
print(result['response'])
```

### Example 3: Multi-Model Consensus

```python
from partisan_intelligence_setup import pi_bridge

result = pi_bridge.multi_model_consensus(
    "What are the key principles of good software design?"
)

for response in result['responses']:
    print(f"\n{response['model']} ({response['source']}):")
    print(response['response'][:200] + "...")
```

### Example 4: With Context

```python
from partisan_intelligence_setup import pi_bridge

context = {
    "project": "E-commerce platform",
    "tech_stack": "Python, React, PostgreSQL",
    "team_size": 5
}

result = pi_bridge.query_with_pi_context(
    "What testing strategy should we use?",
    context=context
)

print(result['response'])
```

---

## 🏥 Health Monitoring

### Manual Health Check

```bash
python3 ~/ark95x-production/backend/health_monitor.py
```

### Continuous Monitoring

```bash
# Check every 5 minutes (default)
~/ark95x-complete/scripts/monitor_system.sh

# Custom interval (seconds)
~/ark95x-complete/scripts/monitor_system.sh 300
```

### What's Monitored

- ✅ Ollama service status
- ✅ Installed models
- ✅ API key availability
- ✅ System resources (disk, memory)
- ✅ Overall system health

---

## 📊 Performance Tips

### 1. Choose the Right Model

| Task Type | Recommended Model | Why |
|-----------|------------------|-----|
| Quick Q&A | llama3.2:3b | Fastest, lowest resource usage |
| Code tasks | qwen2.5-coder:7b | Optimized for programming |
| Deep analysis | deepseek-r1:7b | Best reasoning capabilities |
| Latest info | Cloud APIs | Access to current data |

### 2. Use Local First

```python
# Faster, private, no cost
result = gateway.intelligent_route(prompt, preference="local")
```

### 3. Batch Queries

```python
queries = ["Question 1", "Question 2", "Question 3"]
results = [gateway.query_ollama("llama3.2:3b", q) for q in queries]
```

### 4. Monitor Resources

```bash
# Check disk space
df -h

# Check memory
free -h

# Check Ollama process
ps aux | grep ollama
```

---

## 🔧 Maintenance

### Daily

- Check system health
- Review logs for errors

```bash
python3 ~/ark95x-production/backend/health_monitor.py
tail -f ~/ark95x-complete/logs/*.log
```

### Weekly

- Clean old logs
- Check disk space
- Review API usage

```bash
~/ark95x-complete/scripts/clean_logs.sh
df -h
python3 -c "from api_key_manager import key_manager; print(key_manager.get_stats())"
```

### Monthly

- Update models
- Create backup
- Review performance

```bash
~/ark95x-complete/scripts/update_models.sh
~/ark95x-complete/scripts/backup_ark95x.sh
```

---

## 🛠️ Command Reference

### System Control

```bash
# Start system
~/ark95x-complete/scripts/start_ark95x.sh

# Stop system
~/ark95x-complete/scripts/stop_ark95x.sh

# Monitor system
~/ark95x-complete/scripts/monitor_system.sh
```

### Testing

```bash
# Run deployment tests
~/ark95x-complete/scripts/test_deployment.sh

# Run usage examples
python3 ~/ark95x-complete/scripts/example_usage.py

# Test gateway
python3 ~/ark95x-production/backend/unified_api_gateway.py
```

### Maintenance

```bash
# Backup system
~/ark95x-complete/scripts/backup_ark95x.sh

# Update models
~/ark95x-complete/scripts/update_models.sh

# Clean logs
~/ark95x-complete/scripts/clean_logs.sh
```

### Ollama Commands

```bash
# List models
ollama list

# Pull new model
ollama pull <model-name>

# Run model
ollama run <model-name> "Your prompt"

# Remove model
ollama rm <model-name>

# Show model info
ollama show <model-name>
```

---

## 🔐 Security Best Practices

### 1. Protect API Keys

```bash
# Set restrictive permissions
chmod 600 ~/ark95x-production/configs/api_keys.json

# Never commit keys to git
echo "*/api_keys.json" >> .gitignore
```

### 2. Use Environment Variables (Production)

```bash
export OPENAI_API_KEY="sk-your-key"
export ANTHROPIC_API_KEY="sk-ant-your-key"
```

### 3. Regular Backups

```bash
# Automated backup (add to crontab)
0 2 * * * ~/ark95x-complete/scripts/backup_ark95x.sh
```

### 4. Monitor Access

```bash
# Check recent API usage
python3 -c "
from api_key_manager import key_manager
print(key_manager.get_stats())
"
```

---

## 📈 Advanced Usage

### Custom Model Parameters

```python
import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3.2:3b",
        "prompt": "Your question",
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 500
    }
)
```

### Streaming Responses

```python
import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3.2:3b",
        "prompt": "Write a long story",
        "stream": True
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

### Custom API Endpoint

```python
from fastapi import FastAPI
from unified_api_gateway import gateway

app = FastAPI()

@app.post("/query")
async def query_ai(prompt: str):
    result = gateway.intelligent_route(prompt, preference="local")
    return result

# Run with: uvicorn your_app:app --host 0.0.0.0 --port 8000
```

---

## 🎓 Learning Resources

### Understanding AI Models

- **LLMs**: Large Language Models for text generation
- **Parameters**: Model size (3B = 3 billion parameters)
- **Context Window**: How much text the model can process
- **Temperature**: Creativity vs consistency (0.1-1.0)

### Best Practices

1. **Start local**: Try Ollama first for speed and privacy
2. **Be specific**: Clear prompts get better results
3. **Iterate**: Refine prompts based on responses
4. **Monitor**: Keep track of usage and costs

---

## ❓ FAQ

**Q: Which model should I use?**
A: Start with llama3.2:3b for general tasks. Use deepseek-r1:7b for complex reasoning, qwen2.5-coder:7b for code.

**Q: How do I know if local or cloud was used?**
A: Check the `source` field in the response: `result['source']`

**Q: Can I use this offline?**
A: Yes! Local Ollama models work completely offline once downloaded.

**Q: How much disk space do models use?**
A: llama3.2:3b (~2GB), deepseek-r1:7b (~4GB), qwen2.5-coder:7b (~4GB)

**Q: Are my queries private?**
A: Local Ollama queries are 100% private. Cloud API queries are sent to third parties.

**Q: How do I add more models?**
A: `ollama pull <model-name>` - Browse models at https://ollama.com/library

---

**ARK95X** - Sovereign AI Intelligence System
*Power. Privacy. Performance.*
