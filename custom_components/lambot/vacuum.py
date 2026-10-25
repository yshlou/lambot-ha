"""Lambot 扫地机 vacuum 平台（标准 VacuumEntity）。

v4: 状态推断带时间戳（models.LambotData.inferred_at）——设备休眠后停止上报，
推断状态 10 分钟后过期；f=16 清扫类残留状态码（4/6）在推断过期后按待机兜底，
避免状态永久卡死在"回充中"。清扫中的实时显示由 f=22 时长增长的推断驱动。
v3: 用 fan_speed（HA 2026.9 的正确 API：FAN_SPEED/fan_speed/fan_speeds）承载清扫模式。
"""
from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LambotCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# 本地控制指令（功能码，同 button.py）
CMD_START_SWEEP = 26
CMD_PAUSE = 24
CMD_RETURN_HOME = 25
CMD_SET_MODE = 54

# f=16 设备状态码 → HA vacuum 状态
_STATE_MAP = {
    1: "docked",      # 待机/充电
    2: "returning",   # 回充中
    3: "docked",      # 充电完成
    4: "cleaning",    # 清扫中
    5: "paused",      # 暂停
    6: "cleaning",    # 清扫中
    7: "returning",   # 回充中
    8: "error",       # 异常
    9: "idle",        # 待机
}
STATE_DOCKED = "docked"
STATE_IDLE = "idle"

# 清扫/回充类状态码：设备静默后属于残留值，按待机兜底
_STALE_PRONE_STATES = (4, 6)

# 推断状态最长可信时长（秒）
_INFERRED_TTL_SECONDS = 600

_INFERRED_MAP = {
    "充电中": "docked",
    "回充中": "returning",
    "清扫中": "cleaning",
    "工作中": "cleaning",
    "暂停/待机": "paused",
}

# 清扫模式枚举（2=弓形 / 3=沿边 / 9=区域）
FAN_SPEEDS = ["弓形清扫", "沿边清扫", "区域清扫"]
_MODE_TO_CODE = {"弓形清扫": 2, "沿边清扫": 3, "区域清扫": 9}
_MODE_FROM_CODE = {2: "弓形清扫", 3: "沿边清扫", 9: "区域清扫"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LambotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LambotVacuum(coordinator)])


class LambotVacuum(StateVacuumEntity):
    """岚豹扫地机（标准 vacuum 实体：状态+控制+清扫模式）。"""

    _attr_name = "岚豹扫地机"
    _attr_supported_features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.STATE
        | VacuumEntityFeature.FAN_SPEED
    )
    _attr_fan_speed_list = FAN_SPEEDS

    def __init__(self, coordinator: LambotCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"lambot_{coordinator.device_id}_vacuum"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name="岚豹扫地机",
            manufacturer="Lambot",
            model="Vacuum",
        )
        self._fan_speed: str = "弓形清扫"

    @callback
    def _update_callback(self) -> None:
        dm = self.coordinator.data.device_mode
        if isinstance(dm, dict):
            mode_val = dm.get("mode") or dm.get("clean_mode")
            if isinstance(mode_val, int) and mode_val in _MODE_FROM_CODE:
                self._fan_speed = _MODE_FROM_CODE[mode_val]
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.coordinator.data._listeners.append(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        try:
            self.coordinator.data._listeners.remove(self._update_callback)
        except ValueError:
            pass

    @property
    def state(self) -> str | None:
        data = self.coordinator.data
        # 推断状态带时间戳：设备休眠后停止上报，推断 10 分钟后过期，避免永久卡死
        inferred_fresh = bool(
            data.inferred_state
            and data.inferred_at
            and (time.time() - data.inferred_at) < _INFERRED_TTL_SECONDS
        )
        if inferred_fresh:
            return _INFERRED_MAP.get(data.inferred_state, STATE_IDLE)
        if data.state is not None:
            if data.state in _STALE_PRONE_STATES:
                # 清扫类状态码在推断过期后属于残留值（设备静默），按待机兜底
                return STATE_IDLE
            return _STATE_MAP.get(data.state, STATE_IDLE)
        if data.battery is not None and data.battery >= 99:
            return STATE_DOCKED
        if data.update_time and (time.time() - data.update_time) > 300:
            return STATE_IDLE
        return None

    @property
    def battery_level(self) -> int | None:
        return self.coordinator.data.battery

    @property
    def fan_speed_list(self) -> list[str]:
        return FAN_SPEEDS

    @property
    def fan_speed(self) -> str | None:
        return self._fan_speed

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        attrs: dict[str, Any] = {}
        if data.sweep_area is not None:
            attrs["清扫面积"] = data.sweep_area
        if data.sweep_time is not None:
            attrs["清扫时长"] = data.sweep_time
        if data.inferred_state:
            attrs["设备状态"] = data.inferred_state
        attrs["清扫模式"] = self._fan_speed
        return attrs if attrs else None

    async def async_start(self) -> None:
        self.coordinator.send_command(CMD_START_SWEEP)

    async def async_pause(self) -> None:
        self.coordinator.send_command(CMD_PAUSE)

    async def async_stop(self) -> None:
        self.coordinator.send_command(CMD_PAUSE)

    async def async_return_to_base(self) -> None:
        self.coordinator.send_command(CMD_RETURN_HOME)

    async def async_set_fan_speed(self, fan_speed: str) -> None:
        """切换清扫模式。"""
        if fan_speed in FAN_SPEEDS:
            self._fan_speed = fan_speed
            self.coordinator.send_command(CMD_SET_MODE, {"mode": _MODE_TO_CODE[fan_speed]})
            self.async_write_ha_state()