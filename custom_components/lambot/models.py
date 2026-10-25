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
    clean_mode: int | None = None
    mop_mode: Any | None = None
    update_time: float = 0.0
    _last_battery: int | None = None
    inferred_state: str | None = None
    inferred_at: float = 0.0
    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def _set_inferred(self, value: str | None) -> None:
        """记录推断状态及其产生时间（供 vacuum 平台做过期判断）。"""
        self.inferred_state = value
        self.inferred_at = time.time() if value else 0.0

    def update(self, f: int | None, p: Any) -> None:
        self.update_time = time.time()
        if f == 16 and isinstance(p, int):
            self.state = p
            self._set_inferred(None)
        elif f == 22 and isinstance(p, int):
            # 协议实测（docs/PROTOCOL.md v1.3）：f22 上行是状态事件镜像（与 f16
            # 同值推送），并非清扫时长。与 f16 同样处理：更新 state、清除推断。
            # 旧版"时长增长推断"基于误读，是状态显示冻结的根源，已移除。
            self.state = p
            self._set_inferred(None)
        elif f == 3 and isinstance(p, int):
            self.battery = p
            if self._last_battery is not None and p > self._last_battery and p < 100:
                self._set_inferred("充电中")
            elif p >= 100:
                self._set_inferred(None)
            self._last_battery = p
        elif f == 20 and isinstance(p, (int, float)):
            self.sweep_area = float(p)
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
        elif f == 54 and isinstance(p, int):
            # 协议实测：f54 仅上行（当前清扫模式：0=沿边 1=默认 2=弓形），供回显
            self.clean_mode = p
        elif f == 101 and isinstance(p, dict):
            self.mop_mode = p

        for listener in list(self._listeners):
            try:
                listener()
            except Exception:
                pass
