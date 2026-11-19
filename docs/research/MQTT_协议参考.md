# MQTT 协议参考（Lambot / SLAMTEC RoboHome）

由 `o3/b0.java`（MqttCommand.kt）与 `o3/c0.java`（MqttDataType.kt）反编译还原。
数字 code 为枚举构造时的整数值；部分 code 因 R8 内联/复用存在重复或存疑，命令名本身可靠。

## 连接

| 模式 | 地址 | 凭据 |
|---|---|---|
| 云端远程 | `ssl://iot.lambot.ai:8883`（欧区）/ `ssl://iot.slamtec.com:8883`（中/日区） | 运行时传入 `userName` / `pwd`（需抓包获取） |
| 局域网直连 | `tcp://<机器人IP>:1883` | 硬编码 `Lambot` / `lambot123`（`n3/j.java`） |

## 主题

- 发布（App → 机器人）：`device/{device_id}/robot`
- 订阅（机器人 → App）：`device/{device_id}/app`

## 报文（依据 MqttService.kt 的 JSONObject 构造）

```json
{ "id": "<uuid>", "command": "<命令名小写或 get/put>",
  "param": { ... }, "timestamp": 1730000000000, "uuid": "<uuid>",
  "type": <MqttDataType code> }
```

常用 param 键：`mode`、`mop_mode`、`sweep_areas`、`regions`、`points`、`spot`、
`direction`、`value`、`number`、`track`、`uuid`、`count`、`index`、`add_mode`、
`size`、`time_zone`、`sound_volume_percent`、`voice_id`、`sensor_status`、
`walls`、`v_wall`、`regions`、`smart_doors`、`data`。

## MqttCommand（57 条）

| 命令 | code |
|---|---|
| `FORWARD` | 20 |
| `BACKWARD` | 21 |
| `TURN_LEFT` | 22 |
| `TURN_RIGHT` | 23 |
| `STOP` | 24 |
| `GO_HOME` | 25 |
| `SWEEP` | 26 |
| `SWEEP_SPOT` | 27 |
| `MOVE_TO` | 28 |
| `UPDATE_VIRTUAL_WALL` | 29 |
| `SYNC_SCHEDULE_TASK` | 31 |
| `SWEEP_TIME` | 32 |
| `UPDATE_FIRMWARE` | 33 |
| `FIRMWARE_INFO` | 34 |
| `FIRMWARE_PROCESS` | 35 |
| `FIRMWARE_UPGRADE_SUCCESS` | 36 |
| `START_MQTT_UPDATE` | 40 |
| `HELLO` | 41 |
| `ENTIRE_MAP` | 42 |
| `ROBO_TRACK` | 53 |
| `CLEAR_MAP` | 55 |
| `SWEEP_AREA` | 56 |
| `FIND_ME` | 57 |
| `NETWORK_INFO` | 58 |
| `GET_SWEEP_FAN_MODE` | 59 |
| `SET_SWEEP_FAN_MODE` | 60 |
| `GET_KID_MODE` | 61 |
| `SET_KID_MODE` | 62 |
| `GET_DO_NOT_DISTURB` | 63 |
| `SET_DO_NOT_DISTURB` | 30 |
| `GET_SWEEP_REGION` | 64 |
| `CREATE_SWEEP_REGION` | 66 |
| `DELETE_SWEEP_REGION` | 67 |
| `UPDATE_SWEEP_REGION` | 33 |
| `START_SWEEP_REGION` | 34 |
| `GET_SWEEPING_REGION` | 35 |
| `START_DRAWING_SWEEP` | 36 |
| `GET_SWEEP_DRAWING` | 71 |
| `SET_MAP` | 72 |
| `GET_SWEEP_DIRECTION` | 77 |
| `SET_SWEEP_DIRECTION` | 40 |
| `SET_DEVICE_VOICE` | 41 |
| `VOICE_PROCESS` | 42 |
| `VOICE_UPGRADE_SUCCESS` | 81 |
| `GET_VOICE_ID` | 82 |
| `GET_SMART_PRESSURIZATION` | 83 |
| `VOICE_VOLUME` | 86 |
| `SWEEP_PARTITION_SIZE` | 87 |
| `DYEING_MAP` | 88 |
| `CHECK_SENSORS_STATUS` | 84 |
| `SET_SENSORS_STATUS` | 51 |
| `SET_MOP_MODE` | 101 |
| `SET_SMART_AREA_MODE` | 102 |
| `OPERATE_GOOGLE_HOME` | 106 |
| `SET_TIMEZONE` | 108 |
| `START_AUTO_EXPLORING` | 56 |
| `START_EDGE_SWEEPING` | 109 |

## MqttDataType（45 条）

| 数据类型 | code |
|---|---|
| `POSE` | 1 |
| `CURRENT_ACTION` | 3 |
| `BATTERY_PERCENTAGE` | 4 |
| `BATTERY_IS_CHARGING` | 5 |
| `DC_IS_CONNECTED` | 6 |
| `BOARD_TEMPERATURE` | 7 |
| `EXPLORE_MAP` | 8 |
| `SWEEP_MAP` | 9 |
| `VIRTUAL_WALLS` | 12 |
| `SWEEP_TIME` | 10 |
| `FIRMWARE_PROCESS` | 13 |
| `FIRMWARE_INFO` | 14 |
| `HELLO` | 17 |
| `ENTIRE_EXPLORE_MAP` | 18 |
| `ENTIRE_SWEEP_MAP` | 15 |
| `ROBOTRACK` | 19 |
| `SWEEP_AREA` | 21 |
| `DOCK_POSE` | 22 |
| `ROBOT_STATUS` | 23 |
| `FIRMWARE_UPGRADE_SUCCESS` | 24 |
| `NETWORK_INFO` | 25 |
| `SWEEP_FAN_MODE` | 26 |
| `CHILD_SAFETY_LOCK` | 27 |
| `SILENCE_MODE` | 28 |
| `SWEEP_REGION` | 29 |
| `SWEEPING_REGION` | 26 |
| `DRAWING_SWEEP_TRACK` | 30 |
| `SET_MAP_RESPONSE` | 31 |
| `SWEEP_MOP_MODE` | 32 |
| `SYSTEM_EVENT` | 50 |
| `SWEEP_DIRECTION` | 54 |
| `VOICE_UPGRADE_PROCESS` | 55 |
| `VOICE_UPGRADE_SUCCESS` | 56 |
| `DEVICE_VOICE_ID` | 57 |
| `SMART_PRESSURIZATION` | 58 |
| `SENSORS_STATUS` | 59 |
| `VOICE_VOLUME` | 60 |
| `SWEEP_PARTITION_SIZE` | 61 |
| `WATER_BOX_ON` | 62 |
| `DYEING_MAP` | 66 |
| `DEVICE_EVENTS` | 67 |
| `MOP_MODE` | 101 |
| `SMART_AREA_MODE` | 102 |
| `GOOGLE_HOME_SERVICE` | 103 |
| `DISCONNECT` | 100 |
