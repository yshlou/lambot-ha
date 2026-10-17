"""Lambot 岚豹扫地机 Home Assistant 集成。

通过本地 MQTT 通道（扫地机内置 broker，端口 19883）读取设备状态并控制。
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from datetime import timedelta

import paho.mqtt.client as mqtt

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    DOMAIN,
)
from .models import LambotData

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.IMAGE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置配置项。"""
    coordinator = LambotCoordinator(hass, entry)
    await coordinator.async_connect()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置项。"""
    coordinator: LambotCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_disconnect()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok


class LambotCoordinator:
    """负责与扫地机 MQTT broker 通信的协调器。"""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.data = LambotData()
        self._mqtt: mqtt.Client | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._unsub_poll: callable | None = None

    @property
    def device_id(self) -> str:
        return self.entry.data[CONF_DEVICE_ID]

    @property
    def topic_app(self) -> str:
        return f"device/{self.device_id}/app"

    @property
    def topic_robot(self) -> str:
        return f"device/{self.device_id}/robot"

    async def async_connect(self) -> None:
        """建立 MQTT 连接并开始订阅。"""
        self._loop = asyncio.get_running_loop()
        host = self.entry.data[CONF_HOST]
        port = self.entry.data.get(CONF_PORT, 19883)
        username = self.entry.data.get(CONF_USERNAME, "Lambot")
        password = self.entry.data.get(CONF_PASSWORD, "lambot123")

        client = mqtt.Client(
            client_id=f"ha-lambot-{uuid.uuid4().hex[:8]}",
            protocol=mqtt.MQTTv311,
        )
        client.username_pw_set(username, password)
        client.on_connect = self._on_connect
        client.on_message = self._on_message

        self._mqtt = client
        try:
            client.connect(host, port, keepalive=30)
            client.loop_start()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Lambot MQTT 连接失败: %s", err)
            raise

    async def async_disconnect(self) -> None:
        if self._unsub_poll is not None:
            self._unsub_poll()
            self._unsub_poll = None
        if self._mqtt is not None:
            self._mqtt.loop_stop()
            self._mqtt.disconnect()

    def _on_connect(self, client, userdata, flags, rc, props=None) -> None:
        _LOGGER.info("Lambot MQTT 已连接 rc=%s", rc)
        if rc == 0:
            client.subscribe(self.topic_app)
            # 连接后先发握手，触发设备上报地图与状态
            self._send_handshake()
            # 启动周期轮询（每 60 秒查询一次状态）
            if self._unsub_poll is None:
                self._unsub_poll = async_track_time_interval(
                    self.hass, self._async_poll, timedelta(seconds=60)
                )

    def _on_message(self, client, userdata, msg) -> None:
        try:
            text = msg.payload.decode("utf-8", "replace")
        except Exception:
            return
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._process_message, text)
        else:
            self._process_message(text)

    def _process_message(self, text: str) -> None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            _LOGGER.debug("无法解析的消息: %s", text[:100])
            return

        f = payload.get("f")
        p = payload.get("p")
        _LOGGER.debug("Lambot 收到 f=%s p=%s", f, str(p)[:200])
        self.data.update(f, p)

    async def _async_poll(self, _now=None) -> None:
        """周期查询状态。"""
        if self._mqtt is None:
            return
        self._publish(
            self.topic_robot,
            json.dumps(
                {
                    "f": 40,
                    "p": {
                        "pose": True,
                        "c_act": True,
                        "b_per": True,
                        "b_chr": True,
                        "dc": False,
                        "b_tmp": False,
                        "e_map": True,
                        "s_map": False,
                        "v_wall": True,
                        "run_time": True,
                        "sweep_area": True,
                        "d_pose": True,
                        "sweeping_region": True,
                        "mop_sensor_mount": True,
                    },
                }
            ),
        )
        self._publish(self.topic_robot, json.dumps({"f": 64}))
        self._publish(self.topic_robot, json.dumps({"f": 69}))
        # 注意：f26 是"开始清扫"控制指令（非查询），严禁加入轮询，否则设备反复启动清扫
        self._publish(self.topic_robot, json.dumps({"f": 53, "p": 12}))

    def _send_handshake(self) -> None:
        self._publish(
            self.topic_robot,
            json.dumps({"f": 88, "p": {"id": str(uuid.uuid4()), "command": "require"}}),
        )
        # 查询状态
        self._publish(
            self.topic_robot,
            json.dumps(
                {
                    "f": 40,
                    "p": {
                        "pose": True,
                        "c_act": True,
                        "b_per": True,
                        "b_chr": True,
                        "dc": False,
                        "b_tmp": False,
                        "e_map": True,
                        "s_map": False,
                        "v_wall": True,
                        "run_time": True,
                        "sweep_area": True,
                        "d_pose": True,
                        "sweeping_region": True,
                        "mop_sensor_mount": True,
                    },
                }
            ),
        )
        # 房间/区域
        self._publish(self.topic_robot, json.dumps({"f": 42, "p": {"e_map": True, "s_map": False}}))

    def _publish(self, topic: str, payload: str) -> None:
        if self._mqtt is not None:
            self._mqtt.publish(topic, payload)

    def send_command(self, f: int, p: dict | None = None) -> None:
        """向扫地机下发控制指令（本地通道）。

        扫地机对未在近期握手的客户端会忽略控制指令，因此先重新握手再发送。
        """
        if self._mqtt is None:
            _LOGGER.warning("Lambot MQTT 未连接，指令 f=%s 未发送", f)
            return
        payload = json.dumps({"f": f, "p": p if p is not None else {}})
        handshake = json.dumps(
            {"f": 88, "p": {"id": str(uuid.uuid4()), "command": "require"}}
        )
        self._mqtt.publish(self.topic_robot, handshake)
        _LOGGER.info("Lambot 握手+下发 f=%s payload=%s", f, payload)

        def _do_send() -> None:
            try:
                info = self._mqtt.publish(self.topic_robot, payload)
                _LOGGER.info("Lambot publish rc=%s", info.rc)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Lambot publish 异常: %s", err)

        threading.Timer(1.0, _do_send).start()