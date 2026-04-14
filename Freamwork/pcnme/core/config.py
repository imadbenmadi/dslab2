from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _deep_merge(base: Dict[str, Any], updates: Mapping[str, Any]) -> Dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), Mapping):
            base[key] = _deep_merge(dict(base[key]), value)  # type: ignore[arg-type]
        else:
            base[key] = value
    return base


class Settings(BaseSettings):
    """PCNME configuration (environment + optional YAML overrides)."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # Compute
    FOG_MIPS: int = 2000
    CLOUD_MIPS: int = 8000
    EC_THRESHOLD: float = 1.0
    Q_MAX: int = 50

    # Network
    BANDWIDTH_MBPS: float = 100.0
    FOG_CLOUD_BW: float = 1000.0
    FOG_FOG_BW: float = 100.0
    WAN_LATENCY_MS: float = 30.0
    G5_LATENCY_MS: float = 2.0
    SDN_PREINSTALL_MS: float = 0.0
    SDN_REACTIVE_MS: float = 12.0

    # Fog coverage
    FOG_COVERAGE_RADIUS: float = 250.0

    # NSGA-II + MMDE
    NSGA_POP_SIZE: int = 100
    NSGA_GENS: int = 200
    MMDE_F: float = 0.5
    MMDE_CR: float = 0.9
    NSGA_BATCH_SIZE: int = 100
    N_OFFLINE_BATCHES: int = 1000

    # DQN Agent 1
    AGENT1_STATE_DIM: int = 13
    AGENT1_ACTION_DIM: int = 5
    AGENT1_HIDDEN: list[int] = Field(default_factory=lambda: [256, 128])
    AGENT1_LR: float = 0.001
    AGENT1_GAMMA: float = 0.95
    AGENT1_EPSILON_START: float = 0.30
    AGENT1_EPSILON_END: float = 0.05
    AGENT1_EPSILON_DECAY: int = 10000
    AGENT1_BATCH_SIZE: int = 64
    AGENT1_BUFFER_SIZE: int = 50000
    AGENT1_TARGET_UPDATE: int = 1000

    # DQN Agent 2
    AGENT2_STATE_DIM: int = 15
    AGENT2_ACTION_DIM: int = 5
    AGENT2_HIDDEN: list[int] = Field(default_factory=lambda: [256, 128])
    AGENT2_LR: float = 0.001
    AGENT2_GAMMA: float = 0.95
    AGENT2_EPSILON_START: float = 0.25
    AGENT2_EPSILON_END: float = 0.05
    AGENT2_EPSILON_DECAY: int = 8000
    AGENT2_BATCH_SIZE: int = 64
    AGENT2_BUFFER_SIZE: int = 50000
    AGENT2_TARGET_UPDATE: int = 1000

    # Rewards
    AGENT1_REWARD_LATENCY: float = 0.5
    AGENT1_REWARD_ENERGY: float = 0.3
    AGENT1_REWARD_VIOLATION: float = 0.2
    AGENT1_DEADLINE_PENALTY: float = 10.0
    AGENT2_REWARD_DELIVERY: float = 0.5
    AGENT2_REWARD_DELAY: float = 0.3
    AGENT2_REWARD_OVERHEAD: float = 0.2
    AGENT2_PACKET_DROP_PENALTY: float = 50.0
    AGENT2_PREINSTALL_BONUS: float = 0.3

    # Simulation
    N_VEHICLES: int = 50
    VEHICLE_SPEED_MEAN: float = 60.0
    VEHICLE_SPEED_STD: float = 15.0
    TASK_RATE_HZ: float = 10.0
    SIM_DURATION_S: float = 600.0
    WARMUP_S: float = 60.0
    RANDOM_SEED: int = 42
    N_RUNS: int = 5

    # Storage
    REDIS_URL: str = "redis://localhost:6379/0"
    TIMESCALE_DSN: Optional[str] = None

    # Runtime
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8080
    WS_PATH: str = "/ws/stream"

    # Runtime agent model paths (optional)
    AGENT1_MODEL_PATH: Optional[str] = None
    AGENT2_MODEL_PATH: Optional[str] = None

    @field_validator("AGENT1_HIDDEN", "AGENT2_HIDDEN", mode="before")
    @classmethod
    def _parse_hidden_layers(cls, value: Any):
        if value is None:
            return value
        if isinstance(value, list):
            return [int(v) for v in value]
        if isinstance(value, tuple):
            return [int(v) for v in value]
        if isinstance(value, str):
            raw = [p.strip() for p in value.split(",") if p.strip()]
            return [int(v) for v in raw]
        return value


def load_settings(
    *,
    config_path: Optional[Path] = None,
    overrides: Optional[Mapping[str, Any]] = None,
    env_file: Optional[Path] = None,
) -> Settings:
    base = Settings(_env_file=str(env_file) if env_file else None)
    merged: Dict[str, Any] = base.model_dump()

    if config_path:
        data = load_yaml(config_path)
        merged = _deep_merge(merged, data)

    if overrides:
        merged = _deep_merge(merged, overrides)

    return Settings.model_validate(merged)


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML structure in {path}")
    return data


def resolve_first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None

