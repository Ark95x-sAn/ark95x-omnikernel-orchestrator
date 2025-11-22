# ARK95X Omnikernel Orchestrator - Configuration Guide

This guide explains all configuration options available in the ARK95X Omnikernel Orchestrator. The orchestrator uses TOML format for configuration files.

## Table of Contents

- [Quick Start](#quick-start)
- [Core Model Settings](#core-model-settings)
- [Orchestrator Settings](#orchestrator-settings)
- [CrewAI Agent Configuration](#crewai-agent-configuration)
- [Clone Manager](#clone-manager)
- [Gatekeeper Security](#gatekeeper-security)
- [Decision Router](#decision-router)
- [Restaurant Operations](#restaurant-operations)
- [Profiles](#profiles)
- [Feature Flags](#feature-flags)
- [Advanced Configuration](#advanced-configuration)

## Quick Start

The orchestrator looks for configuration in these locations (in order of precedence):

1. `./config.toml` - Local configuration file
2. `~/.config/omnikernel/config.toml` - User configuration
3. `/etc/omnikernel/config.toml` - System-wide configuration

### Basic Configuration

Create a `config.toml` file in your project root:

```toml
model = "hlm-9"
model_provider = "openai"
orchestrator_mode = "supervised"
```

### Using CLI Arguments

Override configuration values from the command line:

```bash
omnikernel --model gpt-4 --config orchestrator_mode="autonomous"
```

## Core Model Settings

These settings control which AI model the orchestrator uses and how it behaves.

### Default Model

Pick which model the orchestrator uses by default.

**Config:**
```toml
model = "hlm-9"
```

**CLI:**
```bash
omnikernel --model gpt-4
```

**Options:** `hlm-9`, `hlm-7`, `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`, `claude-3-opus`, `claude-3-sonnet`, `llama2`, `mistral`, etc.

### Model Provider

Select the backend provider for your model.

**Config:**
```toml
model_provider = "openai"
```

**CLI:**
```bash
omnikernel --config model_provider="anthropic"
```

**Options:** `openai`, `anthropic`, `ollama`, `hlm`, `local`

### Reasoning Effort

Tune how much computational effort the model applies (for supported models).

**Config:**
```toml
model_reasoning_effort = "high"
```

**CLI:**
```bash
omnikernel --config model_reasoning_effort="high"
```

**Options:** `low`, `medium`, `high`

### Temperature

Control the randomness of model responses (0.0 = deterministic, 2.0 = very creative).

**Config:**
```toml
model_temperature = 0.7
```

**Default:** `0.7`

### Max Tokens

Maximum number of tokens in model responses.

**Config:**
```toml
model_max_tokens = 4096
```

**Default:** `4096`

## Orchestrator Settings

Control the core orchestration behavior.

### Operation Mode

Define how the orchestrator operates.

**Config:**
```toml
orchestrator_mode = "supervised"
```

**Options:**
- `autonomous` - Fully automated, minimal human intervention
- `supervised` - Human oversight on critical decisions
- `interactive` - Constant human interaction required

### Concurrent Agents

Maximum number of agents running simultaneously.

**Config:**
```toml
max_concurrent_agents = 5
```

**Default:** `5`

### Agent Timeout

Maximum time (in seconds) an agent can run before being terminated.

**Config:**
```toml
agent_timeout = 300
```

**Default:** `300` (5 minutes)

### Distributed Mode

Enable orchestration across multiple nodes.

**Config:**
```toml
distributed_mode = false
```

**Default:** `false`

### Heartbeat Interval

How often (in seconds) to check agent health.

**Config:**
```toml
heartbeat_interval = 30
```

**Default:** `30`

## CrewAI Agent Configuration

Configure the CrewAI agent framework integration.

### Enable CrewAI

**Config:**
```toml
[crewai]
enabled = true
```

**Default:** `true`

### Default Crew Size

Number of agents in a standard crew.

**Config:**
```toml
[crewai]
default_crew_size = 3
```

**Default:** `3`

### Collaboration Mode

How agents work together.

**Config:**
```toml
[crewai]
collaboration_mode = "hierarchical"
```

**Options:**
- `sequential` - Agents work one after another
- `parallel` - Agents work simultaneously
- `hierarchical` - Leader-follower structure

### Agent Memory

Enable persistent memory for agents.

**Config:**
```toml
[crewai]
memory_enabled = true
memory_backend = "local"
```

**Memory backends:** `redis`, `postgresql`, `local`

### Delegation

Allow agents to delegate tasks to other agents.

**Config:**
```toml
[crewai]
allow_delegation = true
max_delegation_depth = 2
```

**Default max depth:** `2`

## Clone Manager

Manage agent replication and scaling.

### Enable Clone Manager

**Config:**
```toml
[clone_manager]
enabled = true
```

### Maximum Clones

Maximum clones per agent type.

**Config:**
```toml
[clone_manager]
max_clones = 10
```

**Default:** `10`

### Lifecycle Policy

How clones are managed.

**Config:**
```toml
[clone_manager]
lifecycle_policy = "hybrid"
```

**Options:**
- `ephemeral` - Clones destroyed after task completion
- `persistent` - Clones remain active
- `hybrid` - Mix of both based on load

### Auto-scaling

Automatic scaling based on workload.

**Config:**
```toml
[clone_manager]
auto_scale = true
scale_up_threshold = 0.75
scale_down_threshold = 0.25
```

- `scale_up_threshold`: Load % to trigger scaling up (0.0-1.0)
- `scale_down_threshold`: Load % to trigger scaling down (0.0-1.0)

### Clone Warmup Time

Time (seconds) for clones to initialize before receiving tasks.

**Config:**
```toml
[clone_manager]
warmup_time = 5
```

## Gatekeeper Security

Security and approval policies.

### Approval Policy

Control when the orchestrator asks for permission before executing commands.

**Config:**
```toml
[gatekeeper]
approval_policy = "on-request"
```

**CLI:**
```bash
omnikernel --ask-for-approval risky-only
```

**Options:**
- `always` - Approve every command
- `never` - No approval required (use with caution)
- `on-request` - Approve when model requests it
- `untrusted` - Approve untrusted/third-party commands
- `risky-only` - Approve potentially dangerous commands

### Sandbox Mode

Restrict filesystem and network access.

**Config:**
```toml
[gatekeeper]
sandbox_mode = "workspace-write"
```

**CLI:**
```bash
omnikernel --sandbox read-only
```

**Options:**
- `disabled` - No sandboxing
- `read-only` - Read files, no writes
- `workspace-write` - Write within workspace only
- `full-access` - Unrestricted access

### Rate Limiting

Limit requests per minute.

**Config:**
```toml
[gatekeeper]
rate_limit = 100
```

**Default:** `100` requests/minute

### Command Filtering

Define allowed and blocked command patterns.

**Config:**
```toml
[gatekeeper]
allowed_commands = [
    "^(ls|cat|grep|find|echo).*",
    "^python .*"
]

blocked_commands = [
    "^(rm -rf|sudo|chmod 777).*",
    ".*delete.*database.*"
]
```

Uses regex patterns for matching.

### Input Validation & Output Sanitization

**Config:**
```toml
[gatekeeper]
input_validation = true
output_sanitization = true
```

## Decision Router

Configure intelligent task routing.

### Enable Router

**Config:**
```toml
[decision_router]
enabled = true
```

### Routing Strategy

How tasks are distributed to agents.

**Config:**
```toml
[decision_router]
routing_strategy = "hybrid"
```

**Options:**
- `round-robin` - Distribute evenly in rotation
- `weighted` - Based on agent capabilities
- `least-loaded` - Send to least busy agent
- `semantic` - Match task content to agent expertise
- `hybrid` - Combination of strategies

### Task Classification

Enable AI-powered task classification.

**Config:**
```toml
[decision_router]
task_classification = true
```

### Fallback Strategy

What to do when an agent fails.

**Config:**
```toml
[decision_router]
fallback_strategy = "delegate"
max_retries = 3
retry_backoff = 2.0
```

**Strategies:**
- `retry` - Try same agent again
- `delegate` - Assign to different agent
- `escalate` - Send to supervisor/human
- `abort` - Stop execution

**Backoff:** Multiplier for retry delays (2.0 = double wait time each retry)

### Routing Analytics

Track routing decisions and performance.

**Config:**
```toml
[decision_router]
analytics_enabled = true
```

## Restaurant Operations

Settings specific to restaurant automation.

### Operating Hours

**Config:**
```toml
[restaurant]
operating_hours_start = "08:00"
operating_hours_end = "22:00"
timezone = "America/New_York"
```

### Feature Toggles

**Config:**
```toml
[restaurant]
order_processing_enabled = true
inventory_management_enabled = true
customer_service_enabled = true
reservation_system = "integrated"
pos_integration = "enabled"
```

## Profiles

Profiles bundle configuration values for different scenarios.

### Defining Profiles

**Config:**
```toml
[profiles.production]
model = "hlm-9"
orchestrator_mode = "autonomous"
approval_policy = "risky-only"
max_concurrent_agents = 10

[profiles.development]
model = "gpt-3.5-turbo"
orchestrator_mode = "interactive"
approval_policy = "always"
max_concurrent_agents = 3
```

### Using Profiles

**CLI:**
```bash
omnikernel --profile production
```

### Default Profile

Set a default profile in config:

```toml
profile = "production"
```

### Profile Precedence

Configuration resolves in this order:
1. Explicit CLI flags (highest priority)
2. Profile values
3. Root-level config.toml entries
4. Built-in defaults (lowest priority)

### Built-in Profiles

The orchestrator includes these profiles out-of-the-box:

- **development** - Interactive mode, verbose logging, conservative agents
- **production** - Autonomous mode, optimized for throughput, distributed
- **testing** - Supervised mode, moderate logging, isolated environment
- **high-security** - Maximum security, all approvals required, read-only sandbox
- **lightweight** - Minimal resources, reduced features, fast startup

## Feature Flags

Enable or disable experimental and optional capabilities.

### Enabling Features

**In config.toml:**
```toml
[features]
streamable_shell = true
web_search_request = true
```

**CLI (one-time):**
```bash
omnikernel --enable streamable_shell --enable web_search_request
```

**Disable explicitly:**
```toml
[features]
ghost_commit = false
```

### Available Features

| Feature | Default | Stage | Description |
|---------|---------|-------|-------------|
| `unified_exec` | false | Experimental | Unified PTY-backed execution tool |
| `streamable_shell` | true | Experimental | Streamable exec-command/write-stdin |
| `web_search_request` | true | Stable | Allow model to request web searches |
| `view_image_tool` | true | Stable | Include image viewing capabilities |
| `experimental_sandbox_command_assessment` | false | Experimental | Model-based sandbox risk assessment |
| `ghost_commit` | false | Experimental | Create ghost commit each turn |
| `multi_modal_processing` | true | Stable | Enable multi-modal AI processing |
| `agent_collaboration` | true | Stable | Allow agents to collaborate |
| `realtime_analytics` | true | Stable | Real-time performance analytics |
| `auto_recovery` | true | Stable | Automatic failure recovery |
| `semantic_caching` | true | Stable | Cache semantically similar requests |
| `knowledge_graph` | false | Beta | Knowledge graph integration |

## Advanced Configuration

### Custom Model Providers

Define additional model providers:

**Config:**
```toml
[model_providers.custom_provider]
name = "My Custom Provider"
base_url = "https://api.example.com/v1"
env_key = "CUSTOM_API_KEY"
wire_api = "chat"
models = ["custom-model-1", "custom-model-2"]

[model_providers.custom_provider.headers]
"X-Custom-Header" = "value"

[model_providers.custom_provider.query_params]
version = "2024-01"
```

Then use it:
```toml
model = "custom-model-1"
model_provider = "custom_provider"
```

### Shell Environment Policy

Control which environment variables are passed to spawned commands.

**Config:**
```toml
[shell_environment_policy]
include_only = ["PATH", "HOME", "USER", "PYTHONPATH"]
exclude = ["AWS_SECRET_ACCESS_KEY", "DATABASE_PASSWORD"]
```

**CLI:**
```bash
omnikernel --config shell_environment_policy.include_only='["PATH","HOME"]'
```

### Logging

**Config:**
```toml
[logging]
level = "info"
format = "json"
output = "both"
file_path = "/var/log/omnikernel/orchestrator.log"
rotation_enabled = true
max_file_size = "100MB"
max_backup_count = 10
```

**Log levels:** `debug`, `info`, `warning`, `error`, `critical`
**Formats:** `json`, `text`, `structured`
**Output:** `stdout`, `file`, `both`

### Monitoring

**Config:**
```toml
[monitoring]
metrics_enabled = true
metrics_backend = "prometheus"
metrics_port = 9090
tracing_enabled = true
tracing_backend = "opentelemetry"
```

**Metrics backends:** `prometheus`, `statsd`, `datadog`
**Tracing backends:** `jaeger`, `zipkin`, `opentelemetry`

### Database & Message Queue

**Config:**
```toml
[advanced]
database_url = "postgresql://user:pass@localhost:5432/omnikernel"
redis_url = "redis://localhost:6379/0"
message_queue = "redis"
worker_pool_size = 4
```

### API Server

**Config:**
```toml
[advanced]
api_port = 8080
cors_enabled = true
cors_origins = ["http://localhost:3000"]
```

### Plugins

**Config:**
```toml
[advanced]
plugins_dir = "./plugins"
plugin_hot_reload = false
experimental_mode = false
```

### Graceful Shutdown

**Config:**
```toml
[advanced]
graceful_shutdown = true
shutdown_timeout = 30
```

## Environment Variables

The orchestrator respects these environment variables:

- `OMNIKERNEL_CONFIG` - Path to config file
- `OMNIKERNEL_PROFILE` - Default profile to use
- `OMNIKERNEL_LOG_LEVEL` - Override log level
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `HLM_API_KEY` - HLM API key

## Examples

### Example 1: High-Security Production Setup

```toml
model = "hlm-9"
model_provider = "hlm"
orchestrator_mode = "supervised"

[gatekeeper]
approval_policy = "always"
sandbox_mode = "read-only"
rate_limit = 50
input_validation = true
output_sanitization = true

[features]
experimental_sandbox_command_assessment = true

[logging]
level = "warning"
```

### Example 2: Development Environment

```toml
model = "gpt-3.5-turbo"
model_provider = "openai"
orchestrator_mode = "interactive"

[gatekeeper]
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[logging]
level = "debug"
output = "stdout"

[crewai]
default_crew_size = 2
allow_delegation = false
```

### Example 3: Distributed High-Performance

```toml
model = "hlm-9"
orchestrator_mode = "autonomous"
distributed_mode = true
max_concurrent_agents = 20

[clone_manager]
auto_scale = true
max_clones = 50
scale_up_threshold = 0.8

[decision_router]
routing_strategy = "least-loaded"
fallback_strategy = "delegate"

[monitoring]
metrics_enabled = true
tracing_enabled = true

[advanced]
worker_pool_size = 8
message_queue = "kafka"
```

## Troubleshooting

### Configuration Not Loading

1. Check file path: `omnikernel --config-path`
2. Validate TOML syntax: Use an online TOML validator
3. Check file permissions: Config file must be readable

### Profile Not Found

Ensure profile is defined in config:
```toml
[profiles.my_profile]
model = "hlm-9"
```

### API Key Issues

Set environment variables before running:
```bash
export OPENAI_API_KEY="sk-..."
export HLM_API_KEY="hlm-..."
omnikernel
```

## See Also

- [Main README](README.md)
- [API Documentation](docs/API.md) (if available)
- [Agent Development Guide](docs/AGENTS.md) (if available)
- [Security Best Practices](docs/SECURITY.md) (if available)

---

For more information, visit the ARK95X Omnikernel Orchestrator repository or file an issue.
