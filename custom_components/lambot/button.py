"""Lambot 扫地机控制按钮平台。"""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LambotCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

BUTTON_DESCRIPTIONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="start_sweep",
        name="开始清扫",
        icon="mdi:play",
    ),
    ButtonEntityDescription(
        key="pause",
        name="暂停",
        icon="mdi:pause",
    ),
    ButtonEntityDescription(
        key="return_home",
        name="回充",
        icon="mdi:home-import-outline",
    ),
)

# 本地控制指令（功能码）
CMD_START_SWEEP = 26
CMD_PAUSE = 24
CMD_RETURN_HOME = 25


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置按钮平台。"""
    coordinator: LambotCoordinator = hass.data[DOMAIN][entry.entry_id]
    buttons = [LambotButton(coordinator, desc) for desc in BUTTON_DESCRIPTIONS]
    async_add_entities(buttons)


class LambotButton(ButtonEntity):
    """控制扫地机的按钮。"""

    def __init__(
        self, coordinator: LambotCoordinator, description: ButtonEntityDescription
    ) -> None:
        self.entity_description = description
        self.coordinator = coordinator
        self._attr_unique_id = f"lambot_{coordinator.device_id}_btn_{description.key}"
        self._attr_name = f"岚豹 {description.name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name="岚豹扫地机",
            manufacturer="Lambot",
            model="Vacuum",
        )

    async def async_press(self) -> None:
        """按下按钮执行对应指令。"""
        key = self.entity_description.key
        if key == "start_sweep":
            self.coordinator.send_command(CMD_START_SWEEP)
        elif key == "pause":
            self.coordinator.send_command(CMD_PAUSE)
        elif key == "return_home":
            self.coordinator.send_command(CMD_RETURN_HOME)