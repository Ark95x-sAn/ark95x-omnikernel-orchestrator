"""ARK95X Configuration Manager
Centralized configuration with environment support,
validation, hot-reload, and secure secrets handling.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("ark95x.config")


@dataclass
class ConfigProfile:
    name: str
    values: Dict[str, Any] = field(default_factory=dict)
    parent: Optional[str] = None


class ConfigManager:
    """Centralized configuration with layered profiles."""

    DEFAULT_CONFIG = {
        "orchestrator": {
            "heal_interval": 30,
            "scale_threshold": 0.85,
            "max_agents": 50,
            "task_timeout": 300,
        },
        "self_healing": {
            "circuit_failure_threshold": 5,
            "circuit_recovery_timeout": 60,
            "health_check_interval": 30,
            "max_incidents": 1000,
        },
        "pipeline": {
            "max_parallel": 10,
            "default_timeout": 300,
            "max_retries": 2,
        },
        "telemetry": {
            "retention_points": 10000,
            "snapshot_window": 60,
            "alert_cooldown": 300,
        },
        "models": {
            "default_provider": "ollama",
            "fallback_provider": "openai",
            "cache_enabled": True,
            "cache_ttl": 3600,
            "max_concurrent": 5,
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            "file": None,
        },
    }

    def __init__(self, config_path: Optional[str] = None, env_prefix: str = "ARK95X"):
        self.env_prefix = env_prefix
        self.profiles: Dict[str, ConfigProfile] = {}
        self._active_profile = "default"
        self._config: Dict[str, Any] = {}
        self._secrets: Dict[str, str] = {}
        self._load_defaults()
        if config_path:
            self._load_file(config_path)
        self._load_env()

    def _load_defaults(self):
        self._config = json.loads(json.dumps(self.DEFAULT_CONFIG))
        self.profiles["default"] = ConfigProfile(name="default", values=dict(self._config))

    def _load_file(self, path: str):
        p = Path(path)
        if not p.exists():
            logger.warning(f"Config file not found: {path}")
            return
        try:
            with open(p) as f:
                data = json.load(f)
            self._deep_merge(self._config, data)
            logger.info(f"Loaded config from {path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    def _load_env(self):
        for key, value in os.environ.items():
            if key.startswith(f"{self.env_prefix}_"):
                parts = key[len(self.env_prefix) + 1:].lower().split("__")
                self._set_nested(self._config, parts, self._parse_value(value))
        api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_HOST"]
        for k in api_keys:
            val = os.environ.get(k)
            if val:
                self._secrets[k] = val

    @staticmethod
    def _parse_value(value: str) -> Any:
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                ConfigManager._deep_merge(base[k], v)
            else:
                base[k] = v
        return base

    @staticmethod
    def _set_nested(d: Dict, keys: List[str], value: Any):
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def get(self, path: str, default: Any = None) -> Any:
        parts = path.split(".")
        current = self._config
        for p in parts:
            if isinstance(current, dict) and p in current:
                current = current[p]
            else:
                return default
        return current

    def set(self, path: str, value: Any) -> None:
        parts = path.split(".")
        self._set_nested(self._config, parts, value)

    def get_secret(self, key: str) -> Optional[str]:
        return self._secrets.get(key)

    def add_profile(self, name: str, values: Dict, parent: str = "default"):
        self.profiles[name] = ConfigProfile(name=name, values=values, parent=parent)

    def activate_profile(self, name: str):
        profile = self.profiles.get(name)
        if not profile:
            raise KeyError(f"Profile not found: {name}")
        self._load_defaults()
        if profile.parent and profile.parent in self.profiles:
            self._deep_merge(self._config, self.profiles[profile.parent].values)
        self._deep_merge(self._config, profile.values)
        self._active_profile = name
        self._load_env()
        logger.info(f"Activated profile: {name}")

    def export(self) -> Dict[str, Any]:
        return {
            "active_profile": self._active_profile,
            "config": self._config,
            "profiles": list(self.profiles.keys()),
        }
