# ark95x-omnikernel-orchestrator

ARK95X Unified Intelligence Stack - Omnikernel Orchestrator with HLM-9, CrewAI Agents, Clone Manager, Gatekeeper, and Decision Router for restaurant operations automation

## Quick Start

1. **Configure the orchestrator**: Copy `example.config.toml` to `config.toml` and customize it for your needs
2. **Review configuration options**: See [CONFIG.md](CONFIG.md) for detailed documentation
3. **Run the orchestrator**: `omnikernel --profile production`

## Configuration

The orchestrator provides extensive configuration options:

- **[config.toml](config.toml)** - Main configuration file with all available options
- **[example.config.toml](example.config.toml)** - Simple template to get started quickly
- **[CONFIG.md](CONFIG.md)** - Complete configuration documentation

### Key Features

- **Multiple AI Models**: Support for HLM-9, GPT-4, Claude, Llama, and custom models
- **CrewAI Integration**: Hierarchical, parallel, and sequential agent collaboration
- **Clone Manager**: Auto-scaling agent replication for high-load scenarios
- **Gatekeeper Security**: Approval policies, sandboxing, and command filtering
- **Decision Router**: Intelligent task routing with fallback strategies
- **Profiles**: Quick switching between development, production, and testing environments
- **Feature Flags**: Enable/disable experimental and optional capabilities

## Documentation

- [Configuration Guide](CONFIG.md) - Comprehensive configuration documentation
- API Documentation - Coming soon
- Agent Development Guide - Coming soon
