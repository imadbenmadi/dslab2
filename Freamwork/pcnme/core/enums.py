from __future__ import annotations

from enum import Enum


class OffloadTarget(str, Enum):
    DEVICE = "device"
    FOG = "fog"
    CLOUD = "cloud"


class HandoffMode(str, Enum):
    DIRECT = "direct"
    PROACTIVE = "proactive"
    REACTIVE_HTB = "htb"


class TaskClass(str, Enum):
    BOULDER = "boulder"
    PEBBLE = "pebble"
    SUPER_PEBBLE = "super_pebble"
