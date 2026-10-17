"""Lambot 集成配置流。"""
from __future__ import annotations

from typing import Any

from probatio import Schema
from probatio.markers import Optional, Required

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from .const import (
    CONF_DEVICE_ID,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
)

SCHEMA = Schema(
    {
        Required(CONF_HOST, description="扫地机 IP 地址，如 192.168.x.x"): str,
        Optional(CONF_PORT, default=DEFAULT_PORT): int,
        Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
        Required(CONF_DEVICE_ID, description="设备唯一 ID（局域网 MQTT topic 中使用）"): str,
    }
)


class LambotConfigFlow(ConfigFlow, domain=DOMAIN):
    """处理 Lambot 的配置流。"""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="岚豹扫地机", data=user_input)
        return self.async_show_form(step_id="user", data_schema=SCHEMA)