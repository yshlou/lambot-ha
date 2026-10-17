"""Lambot 集成常量。"""
from __future__ import annotations

DOMAIN = "lambot"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DEVICE_ID = "device_id"

DEFAULT_PORT = 19883
DEFAULT_USERNAME = "Lambot"
DEFAULT_PASSWORD = "lambot123"

# 默认 topic 模板
TOPIC_APP = "device/{device_id}/app"
TOPIC_ROBOT = "device/{device_id}/robot"

# 设备状态码（f:16 上报的状态值）
STATE_MAP = {
    0: "未知",
    1: "待机/充电",
    2: "回充中",
    3: "充电完成",
    4: "清扫中",
    5: "暂停",
    6: "清扫中",
    7: "回充中",
    8: "异常",
    9: "待机",
}