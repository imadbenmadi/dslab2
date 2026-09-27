from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class TorchSupport:
    torch: Any
    nn: Any
    optim: Any


def require_torch() -> TorchSupport:
    """Import torch lazily and raise a clear error if missing."""
    try:
        import torch  # type: ignore
        import torch.nn as nn  # type: ignore
        import torch.optim as optim  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "PyTorch is required for PCNME agent training/inference. "
            "Install it with `pip install torch` (or the appropriate wheel for your platform)."
        ) from exc

    return TorchSupport(torch=torch, nn=nn, optim=optim)
