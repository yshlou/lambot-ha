"""Lambot 扫地机 vacuum 平台（标准 VacuumEntity）。

v5: 按协议实测（docs/PROTOCOL.md v1.3）校准——
  - 模式设置改用 f78 裸标量（旧 f54 下发无效，54 实为上行方向的模式上报）；
  - 模式码修正：0=沿边、2=弓形（旧映射沿边=3 有误）；区域清扫无独立模式码，
    仅更新本地显示（指定区域清扫是独立指令，暂不启用）；
  - f16 状态映射按实测修正：5=回充中、7=清扫挂起/暂停（旧映射颠倒），
    补充 0/2/9/14/15；清扫/回充类残留（4/5/6/14）静默后按待机兜底；
  - 暂停跟随官方带参 f24 p=1；
  - f22 上行实为状态事件镜像（非清扫时长），models 已同码处理，"清扫时长"
    属性因无真实数据源不再展示。
v4: 状态推断带时间戳（models.LambotData.inferred_at）——设备休眠后停止上报，
推断状态 10 分钟后过期，避免状态永久卡死。
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

# 本地控制指令（功能码）
CMD_START_SWEEP = 26
CMD_PAUSE = 24
CMD_RETURN_HOME = 25
CMD_SET_MODE = 78  # v5 修正：78=设置清扫模式（裸标量 p）；54 是上行方向的模式上报，下发无效

# f=16 设备状态码 → HA vacuum 状态（协议实测校准，见 docs/PROTOCOL.md v1.3）
_STATE_MAP = {
    0: "idle",        # 遥控模式待机
    1: "docked",      # 待机/在充电座上（落座过渡）
    2: "docked",      # 在座充电/充电完成
    5: "returning",   # 回充对接/返航中
    6: "cleaning",    # 清扫中
    7: "paused",      # 清扫挂起/暂停（静止待命，不移动不返航）
    9: "idle",        # 遥控旋转执行中（瞬时动作）
    14: "cleaning",   # 区域清扫中
    15: "paused",     # 区域清扫暂停
}
STATE_DOCKED = "docked"
STATE_IDLE = "idle"

# 清扫/回充类瞬时状态码：设备长时间静默后属于残留值，按待机兜底
# （7/15 挂起类保留 paused 显示，不在兜底之列）
_STALE_PRONE_STATES = (4, 5, 6, 14)
# 状态残留判定阈值（秒）：设备超过该时长无任何上报，清扫/回充类状态码才视为残留
# （设备活跃上报期间，6/5 等状态必须正常映射为清扫中/回充中）
_STALE_AFTER_SECONDS = 600

# 推断状态最长可信时长（秒）
_INFERRED_TTL_SECONDS = 600

_INFERRED_MAP = {
    "充电中": "docked",
    "回充中": "returning",
    "清扫中": "cleaning",
    "工作中": "cleaning",
    "暂停/待机": "paused",
}

# 清扫模式：文本 ↔ 设备码（f78 裸标量；0=沿边、1=默认、2=弓形，实测见 docs/PROTOCOL.md）
FAN_SPEEDS = ["弓形清扫", "沿边清扫", "区域清扫"]
_MODE_TO_CODE = {"弓形清扫": 2, "沿边清扫": 0, "区域清扫": None}
# 区域清扫无独立模式码（走指定区域清扫指令，暂不启用），仅更新本地显示
_MODE_FROM_CODE = {0: "沿边清扫", 2: "弓形清扫"}


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
        # f54 上行=当前清扫模式（0=沿边 1=默认 2=弓形），用于回显
        cm = self.coordinator.data.clean_mode
        if isinstance(cm, int) and cm in _MODE_FROM_CODE:
            self._fan_speed = _MODE_FROM_CODE[cm]
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
            if (
                data.state in _STALE_PRONE_STATES
                and data.update_time
                and (time.time() - data.update_time) > _STALE_AFTER_SECONDS
            ):
                # 设备静默超过阈值后，清扫/回充类状态码属于残留值，按待机兜底；
                # 设备活跃上报期间必须正常映射（6=清扫中、5=回充中）
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
        self.coordinator.send_command(CMD_PAUSE, 1)  # 官方带参 p=1

    async def async_stop(self) -> None:
        self.coordinator.send_command(CMD_PAUSE, 1)

    async def async_return_to_base(self) -> None:
        self.coordinator.send_command(CMD_RETURN_HOME)

    async def async_set_fan_speed(self, fan_speed: str) -> None:
        """切换清扫模式（f78 裸标量下发；区域清扫无独立模式码，仅更新显示）。"""
        if fan_speed in FAN_SPEEDS:
            self._fan_speed = fan_speed
            code = _MODE_TO_CODE[fan_speed]
            if code is not None:
                self.coordinator.send_command(CMD_SET_MODE, code)
            self.async_write_ha_state()
