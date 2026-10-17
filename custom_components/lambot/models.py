# Lambot 数据模型
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class LambotData:
    state: int | None = None
    battery: int | None = None
    sweep_area: float | None = None
    sweep_time: int | None = None
    pose: Any | None = None
    path: Any | None = None
    track: Any | None = None
    map_png: bytes | None = None
    map_dimensions: tuple[int, int] | None = None
    map_resolution: float | None = None
    map_updated: float = 0.0
    rooms: Any | None = None
    device_mode: Any | None = None
    mop_mode: Any | None = None
    update_time: float = 0.0
    _last_sweep_time: int | None = None
    _last_battery: int | None = None
    inferred_state: str | None = None
    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def update(self, f: int | None, p: Any) -> None:
        self.update_time = time.time()
        if f == 16 and isinstance(p, int):
            self.state = p
            self.inferred_state = None
        elif f == 3 and isinstance(p, int):
            self.battery = p
            if self._last_battery is not None and p > self._last_battery and p < 100:
                self.inferred_state = "充电中"
            elif p >= 100:
                self.inferred_state = None
            self._last_battery = p
        elif f == 20 and isinstance(p, (int, float)):
            self.sweep_area = float(p)
        elif f == 22 and isinstance(p, int):
            self.sweep_time = p
            if self._last_sweep_time is not None and p > self._last_sweep_time:
                self.state = 6
                if self.battery is not None and self._last_battery is not None:
                    if self.battery > self._last_battery:
                        self.inferred_state = "回充中"
                    elif self.battery < self._last_battery:
                        self.inferred_state = "清扫中"
                    else:
                        self.inferred_state = "工作中"
                else:
                    self.inferred_state = "工作中"
            elif self._last_sweep_time is not None and p == self._last_sweep_time and p > 0:
                self.inferred_state = "暂停/待机"
            elif p == 0:
                self.inferred_state = None
            self._last_sweep_time = p
        elif f == 1 and isinstance(p, dict):
            self.pose = p
        elif f == 2:
            self.path = p
        elif f == 19 and isinstance(p, dict):
            self.track = p
        elif f in (7, 17, 66) and isinstance(p, dict):
            # SLAM 地图（格式已破解：自适应转义 RLE，见 map_utils.py）
            self.map_dimensions = (int(p.get("dimension_x", 0)), int(p.get("dimension_y", 0)))
            self.map_resolution = p.get("resolution")
            from .map_utils import decode_map_payload
            try:
                result = decode_map_payload(p)
                if result:
                    png, dx, dy = result
                    self.map_png = png
                    self.map_dimensions = (dx, dy)
                    self.map_updated = time.time()
            except Exception:
                pass
        elif f == 28:
            self.rooms = p
        elif f == 32 and isinstance(p, dict):
            self.device_mode = p
        elif f == 101 and isinstance(p, dict):
            self.mop_mode = p

        for listener in list(self._listeners):
            try:
                listener()
            except Exception:
                pass