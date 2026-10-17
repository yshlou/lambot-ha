"""Lambot 扫地机 SLAM 地图图像实体。"""
from __future__ import annotations

import logging

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import LambotCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LambotCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LambotMapImage(coordinator)])


class LambotMapImage(ImageEntity):
    """显示扫地机 SLAM 地图的图像实体。"""

    def __init__(self, coordinator: LambotCoordinator) -> None:
        super().__init__(coordinator.hass)
        self.coordinator = coordinator
        self._attr_unique_id = f"lambot_{coordinator.device_id}_map"
        self._attr_name = "岚豹 地图"
        self._attr_content_type = "image/png"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name="岚豹扫地机",
            manufacturer="Lambot",
            model="Vacuum",
        )
        self._attr_image_last_updated = dt_util.utcnow()

    async def async_added_to_hass(self) -> None:
        self.coordinator.data._listeners.append(self._on_data)
        await super().async_added_to_hass()

    def _on_data(self) -> None:
        if self.coordinator.data.map_png:
            self._attr_image_last_updated = dt_util.utcnow()
            self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        return self.coordinator.data.map_png
