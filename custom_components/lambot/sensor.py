"""Lambot 传感器平台。"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfArea, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LambotCoordinator
from .const import DOMAIN, STATE_MAP

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="state",
        name="设备状态",
        icon="mdi:robot-vacuum",
    ),
    SensorEntityDescription(
        key="battery",
        name="电量",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),
    SensorEntityDescription(
        key="sweep_area",
        name="清扫面积",
        native_unit_of_measurement=UnitOfArea.SQUARE_METERS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:floor-plan",
    ),
    SensorEntityDescription(
        key="sweep_time",
        name="清扫时长",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-outline",
    ),
    SensorEntityDescription(
        key="room_count",
        name="区域数量",
        icon="mdi:home-map-marker",
    ),
    SensorEntityDescription(
        key="mop_mode",
        name="拖地模式",
        icon="mdi:water",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置传感器平台。"""
    coordinator: LambotCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [LambotSensor(coordinator, desc) for desc in SENSOR_DESCRIPTIONS]
    async_add_entities(entities)


class LambotSensor(SensorEntity):
    """读取协调器数据的传感器。"""

    def __init__(self, coordinator: LambotCoordinator, description: SensorEntityDescription) -> None:
        self.entity_description = description
        self.coordinator = coordinator
        self._attr_unique_id = f"lambot_{coordinator.device_id}_{description.key}"
        self._attr_name = f"岚豹 {description.name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name="岚豹扫地机",
            manufacturer="Lambot",
            model="Vacuum",
        )

    @callback
    def _update_callback(self) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """注册更新回调。"""
        self.coordinator.data._listeners.append(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """移除更新回调。"""
        try:
            self.coordinator.data._listeners.remove(self._update_callback)
        except ValueError:
            pass

    @property
    def state(self) -> Any:
        data = self.coordinator.data
        key = self.entity_description.key
        if key == "state":
            if data.inferred_state:
                return data.inferred_state
            return STATE_MAP.get(data.state, "未知")
        if key == "battery":
            return data.battery
        if key == "sweep_area":
            return data.sweep_area
        if key == "sweep_time":
            return data.sweep_time
        if key == "room_count":
            rooms = data.rooms
            if isinstance(rooms, list):
                return len(rooms)
            return None
        if key == "mop_mode":
            mop = data.mop_mode
            if isinstance(mop, dict):
                return mop.get("data", {}).get("mop_mode", None)
            return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        attrs: dict[str, Any] = {}
        if data.pose:
            attrs["pose_x"] = data.pose.get("x")
            attrs["pose_y"] = data.pose.get("y")
            attrs["pose_yaw"] = data.pose.get("yaw")
        if data.map_dimensions:
            attrs["map_dimensions"] = data.map_dimensions
        if data.map_resolution:
            attrs["map_resolution"] = data.map_resolution
        if data.device_mode:
            attrs["device_mode"] = data.device_mode.get("device_mode")
        return attrs if attrs else None