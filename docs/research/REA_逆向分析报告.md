# ai.lambot.android.vacuum.apk 逆向分析报告

> 目标：把 Lambot 扫地机的完整功能迁移到 Home Assistant
> 分析日期：2026-11-09 ｜ 工具链：REA 6.8.0 + 其锁定的 jadx-headless-mcp 0.7.1 + androguard 4.1.4
> 样本：`<LOCAL_ARCHIVE_PATH>`

> ## ⚠️ 2026-11-09 重要更正（请先读）
>
> 本报告完成后，参考了同目录 `README.md`，发现用户**已有一套真机抓包验证、正在运行的集成**
> （`lambot/lambot-ha-push/`，协议文档 `docs/PROTOCOL.md` v1.3）。对照结论：
>
> 1. **本报告第 1 节"可做出可运行集成"和随附 `custom_components/lambot_vacuum/` 骨架，不得直接部署。**
>    本地通道实际是 `tcp://<设备IP>:19883`（非 1883）、报文格式 `{"f":<功能码>,"p":<参数>}`
>    （非 `{"id","command","param",...}`），且必须先发 **f88 握手**、持续发 **f41 心跳** 才有状态流。
> 2. **"需真机抓包校准"已不再是待办**——PROTOCOL.md v1.3 就是校准答案；APK 枚举与 f-code
>    属同一编号体系，但存在重码、错位与语义不符，详见 **`与现役集成对照与校准.md`**。
> 3. 云端 REST 65 接口在当前"品牌云已关闭、纯本地直连"的环境下基本无用。
> 4. 本报告与 evidence 的价值重新定位为：**App 层枚举命名、云端 API、交叉验证素材**；
>    固件侧关键控制 f2 / f16 / f68 / f69 / f78 只能由抓包得到。
>
> 以下正文保留原始分析记录，涉及上述结论之处以本更正为准。

---

## 1. 结论先行

**可以做出一套覆盖 App 全部可见功能的 Home Assistant 集成**，因为这台机器的控制面并不是黑盒私有二进制协议，而是两个已经完全还原的标准通道：

| 通道 | 用途 | 还原程度 |
|---|---|---|
| 云端 REST（Retrofit + Moshi） | 账号、设备、地图、定时任务、清扫记录、耗材、消息、固件、分享 | **65 个接口全部还原**（动词 + 路径 + 请求头 + 参数） |
| MQTT（Eclipse Paho） | 实时控制命令与遥测（清扫/暂停/回充/定点/区域/吸力/拖地/虚拟墙…） | **57 条命令 + 45 种遥测类型全部还原**，broker/主题/凭据已知 |

随附的 `custom_components/lambot_vacuum/` 是一次协议建模的代码骨架：vacuum / sensor / select / switch / number 五个平台，共 **27 个实体**（1 + 17 + 3 + 4 + 2）、**27 个服务**，以及配置流 / 选项流。**注意：经与现役抓包协议对照，此骨架不兼容设备本地通道，请勿部署，详见顶部"重要更正"。**

**必须说清的三个限制**（否则"完整可用"是空话）：

1. **凭据未随 APK 硬编码**：OAuth 的 `app_key`/`app_secret`、远程 MQTT 的 `userName`/`pwd` 是运行时注入/下发的，静态分析无法得到。需要你用自己的账号做一次抓包（或提供已有的 token/凭据）才能真机跑通。局域网直连的凭据倒是硬编码的（`Lambot` / `lambot123`）。
2. **MQTT 报文的部分字段是推断的**：命令名、数据类型、topic 是确证的；每条命令 `param` 里的精确字段组合，需一次真机抓包逐条校对。代码里保留了 `raw_command` 服务，可以原样回放抓到的报文而不改代码。
3. **合规**：本报告仅用于你自有设备的互操作（Home Assistant 本地接入）。请遵守云服务的条款，不要用于绕过授权、批量访问他人设备或分发凭据。

---

## 2. APK 基本信息

| 项 | 值 |
|---|---|
| 包名 | `ai.lambot.android.vacuum` |
| 版本 | 2.1.0（versionCode 10130） |
| SDK | min 21 / target 33 |
| 体积 | 45.5 MB，2453 个文件 |
| DEX | 3 个，12447 类 / 74291 方法 / 213 万条指令（R8 混淆） |
| 权限 | 34 项（INTERNET、BLUETOOTH、定位、WiFi、推送、相机等） |
| 组件 | 52 个 Activity、19 个 Service |
| 主要三方库 | Retrofit/OkHttp、Moshi、RxJava、Realm、Eclipse Paho MQTT、HMS/小米/魅族/OPPO/vivo/阿里推送、Sentry、微信/微博 SDK |

核心业务代码在 `com.slamtec.android.*`（SLAMTEC RoboHome SDK，542 类）和 `ai.lambot.android.*`（Lambot 自家 UI，118 类）；网络层被混淆进 `i3`、`h3`、`n3`、`o3` 等短包名。

---

## 3. 系统架构

```
┌──────────────────────┐   HTTPS + OAuth2 Bearer    ┌────────────────────────┐
│  Home Assistant      │ ─────────────────────────▶ │ cloud.lambot.ai        │
│  custom_components/  │  /api/devices, /api/maps…  │ cloud.slamtec.com      │
│  lambot_vacuum       │ ◀───────────────────────── │  (65 个 REST 接口)     │
└──────────┬───────────┘   JSON + vendor media type  └────────────────────────┘
           │  MQTT over TLS :8883
           │  publish   device/{id}/robot
           │  subscribe device/{id}/app
           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ iot.lambot.ai / iot.slamtec.com   （或局域网 tcp://机器人IP:1883）        │
└──────────────────────────────┬───────────────────────────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │  扫地机器人本体       │
                    └──────────────────────┘
```

### 3.1 云端 REST

基础地址（`h3/v.java` = NetworkService.kt）：

| 区域 | API Base | 辅助服务 |
|---|---|---|
| 中国 / 日本 | `https://cloud.slamtec.com/` | `https://lambda-jp.lambot.ai` |
| 欧洲 / 全球 | `https://cloud.lambot.ai/` | `https://lambda-eu.lambot.ai` |

鉴权（`h3/q2.java` = OAuthApi 客户端）：

- `POST /oauth/token`，`grant_type=password`（username/password）、`grant_type=refresh_token`、或 `client_credentials`
- 请求头 `Authorization: Basic base64(app_key:app_secret)`（`x-www-form-urlencoded`）
- 后续请求 `Authorization: Bearer <access_token>`，`OAuthMoshi` 字段：`access_token` / `refresh_token` / `expires_in` / `scope` / `token_type`
- 微信登录：`GET /oauth/wechat/auth_code?code=...`；登出 `POST /oauth/revoke`

内容协商使用自定义 vendor media type（**必须带，否则接口可能拒绝**）：
`application/vnd.slamtec.device-v1.0+json`、`devicelist`、`deviceproperty`、`map`、`task`、`tasklist`、`scheduledtask`、`scheduledtasklist`、`user`、`sweepdetail`、`sweeptotal`、`supplystatlist`、`messagelist`、`mobileapp`、`voicepage`，以及 `application/vnd.lambot.user-v2.0+json`。

Retrofit 注解被 R8 混淆成 `g9.*`，通过 `compiled from` 元数据还原：`g9.f=GET`、`g9.p=PUT`、`g9.o=POST`、`g9.b=DELETE`、`g9.n=PATCH`、`g9.g=HEAD`、`g9.h=HTTP`、`g9.k=Headers`、`g9.s=Path`、`g9.t=Query`、`g9.a=Body`。

**完整的 65 个接口表见 `API_参考.md`。** 按功能分组：

| 组 | 代表接口 |
|---|---|
| 设备 | `GET/PUT /api/devices/{id}`、`GET/PUT /api/devices/{id}/properties`、`DELETE /api/devices/{id}/properties/{key}`、`PUT /api/devices/{id}:init`、`GET /api/devices/{id}/flashes` |
| 用户 | `GET/POST /api/users`、`/api/users/v2`、`/api/users/{id}`、`/api/users/{id}/password`、`GET /prod/user/properties`、短信/邮箱验证码 |
| 地图 | `GET /api/maps/{map_id}`（含 `v_areas` / `v_walls` / `v_forbidden_areas` / `dock_pose` / `pose`）、`GET /api/maps/{map_id}/binary` |
| 任务 | `GET /api/devices/{id}/tasks`、`GET /api/devices/{id}/tasks/{task_id}` |
| 定时 | `GET/POST /api/devices/{id}/scheduled-tasks`、`PUT/DELETE .../{task_id}` |
| 清扫记录 | `GET /api/sweeps/devices/{id}`、`GET /api/sweeps/devices/{id}/tasks/{task_id}` |
| 耗材 | `GET /api/supplies/devices/{id}`、`PUT .../categories/{category_id}` |
| 消息 | `GET/POST/PATCH/DELETE /api/messages`、`/api/messages/broadcasts`、`/api/notifications/users/{id}` |
| 分享/试用 | `/api/invitations/...`、`/api/trials/devices/...`、`DELETE /api/devices/{id}/users/{user_id}` |
| 其他 | `/api/voices`、`/api/apps/latest`、`/api/image2path` |

### 3.2 MQTT 实时通道

| 项 | 值 | 出处 |
|---|---|---|
| 远程 broker | `ssl://iot.lambot.ai:8883`、`ssl://iot.slamtec.com:8883` | `n3/p.java` (MqttRemoteSession.kt) |
| 本地 broker | `tcp://<机器人IP>:1883`，用户 `Lambot` / 密码 `lambot123` | `n3/j.java` (MqttLocalSession.kt) |
| 发布主题 | `device/{device_id}/robot` | `n3/u.java` (MqttService.kt) |
| 订阅主题 | `device/{device_id}/app` | 同上 |
| MQTT 版本 | 3.1.1，`cleanSession=true`，QoS 1，keepalive 60 | Paho `MqttConnectOptions` |
| WebSocket 备用路径 | `/mqtt` | `w8/e.java` (WebSocketHandshake) |

报文由 `org.json.JSONObject` 手工构造，字段：`id`(UUID)、`command`、`param`、`timestamp`、`uuid`、`type`(MqttDataType code)，另有 `count`、`index`、`add_mode`、`size`、`track` 等按命令附加。

**完整的 57 条命令 + 45 种遥测类型表见 `MQTT_协议参考.md`。** 关键命令：

- 基础：`SWEEP` / `SWEEP_SPOT` / `STOP` / `GO_HOME` / `FIND_ME` / `MOVE_TO`
- 手动：`FORWARD` / `BACKWARD` / `TURN_LEFT` / `TURN_RIGHT`
- 地图：`ENTIRE_MAP` / `CLEAR_MAP` / `SET_MAP` / `DYEING_MAP` / `UPDATE_VIRTUAL_WALL` / `START_AUTO_EXPLORING`
- 区域：`GET/CREATE/DELETE/UPDATE/START_SWEEP_REGION`、`SWEEP_AREA`、`START_DRAWING_SWEEP`、`GET_SWEEP_DRAWING`
- 设置：`SET_SWEEP_FAN_MODE` / `SET_MOP_MODE` / `SET_SWEEP_DIRECTION` / `SET_KID_MODE` / `SET_DO_NOT_DISTURB` / `VOICE_VOLUME` / `SET_DEVICE_VOICE` / `SET_TIMEZONE` / `SET_SMART_AREA_MODE` / `SET_SENSORS_STATUS` / `SWEEP_PARTITION_SIZE`
- 维护：`UPDATE_FIRMWARE` / `FIRMWARE_INFO` / `CHECK_SENSORS_STATUS` / `SYNC_SCHEDULE_TASK` / `HELLO` / `NETWORK_INFO`
- 生态：`OPERATE_GOOGLE_HOME` / `START_EDGE_SWEEPING`

遥测（MqttDataType）覆盖：电池百分比与充电状态、DC 连接、主板温度、当前动作、位姿/充电座位姿、机器人状态、各类地图/轨迹/清扫面积与时长、吸力档位、童锁、静音、拖地模式、水量、水箱、传感器状态、语音、固件升级进度、系统事件、断连等。Kotlin data class 的 `toString` 模板还直接暴露了字段名（`BatteryPercentageMqttModel(percentage=`、`SweepFanModeMqttModel(mode=` 等）。

### 3.3 数据模型

`com.slamtec.android.common_models.moshi` 下的 52 个 Moshi JsonAdapter（另有 2 个位于 `robohome/service/device` 包，全 APK 共 54 个）给出了全部 JSON 字段名，已整理在 `11-models-keys.json`。几个关键模型：

| 模型 | 字段 |
|---|---|
| `DeviceMoshi` | `device_id`, `device_name`, `status`, `properties`, `manufacturer(_id)`, `model(_id)`, `hardware_version`, `software_version`, `owner_id`, `device_users`, `activated`, `is_trial`, `is_expired` |
| `MapMoshi` | `map_id`, `kind`, `type`, `size`, `checksum`, `pose`, `dock_pose`, `v_areas`, `v_walls`, `v_forbidden_areas`, `resource_key` |
| `TaskMoshi` | `task_id`, `type`, `task`, `status`, `result`, `started_time`, `finished_time`, `created`, `last_updated` |
| `TaskResultMoshi` | `dock_pose`, `explorer_map`, `robotrack`, `smart_sweep`, `sweep_regions`, `tracks` |
| `ScheduledTaskMoshi` | `scheduled_task_id`, `enabled`, `repeat`, `start_date`, `max_duration_in_minutes`, `info`, `task`, `version` |
| `SweepDetailMoshi` / `SweepTotalMoshi` | `area`, `area_square`, `duration` / `sweep_count`, `total_area_squre`, `total_duration` |
| `SupplyMoshi` / `SupplyStatMoshi` | 耗材类别、用量、时长 |
| `VersionConfigMoshi` | 功能开关清单（见下） |

---

## 4. 完整功能清单（来自 UI 与功能开关）

从 `com/slamtec/android/robohome/views/**` 的 Activity/Widget 名称、`VersionConfigMoshi` 的字段和 MQTT 命令交叉验证，App 的功能全集如下：

| 分类 | 功能 | 证据 |
|---|---|---|
| 清扫控制 | 全屋清扫、暂停/停止、回充、定点清扫、区域/分区清扫、画线条清扫、沿边清扫、自动探索建图、寻找机器人 | `SWEEP`, `SWEEP_SPOT`, `SWEEP_AREA`, `START_SWEEP_REGION`, `START_DRAWING_SWEEP`, `START_EDGE_SWEEPING`, `START_AUTO_EXPLORING`, `FIND_ME`, `GO_HOME` |
| 手动遥控 | 前进/后退/左转/右转/停止、移动到指定坐标 | `ManualControlActivity`, `SDPSteeringWheelView`, `FORWARD`…`MOVE_TO` |
| 吸力/拖地 | 吸力档位、拖地模式、水箱、智能增压、地毯增压、清扫方向、分区大小 | `VacuumFanModeWidget`, `VacuumMopModeWidget`, `SET_SWEEP_FAN_MODE`, `SET_MOP_MODE`, `SET_SMART_AREA_MODE`, `carpet_boost` |
| 地图 | 实时地图、多地图加载/保存、地图染色、虚拟墙、禁区、分区编辑与命名、清除地图、收藏地图 1–6 | `MapView`, `LoadMapActivity`, `SweepPartitionActivity`, `MapRegionMoshi`, `MapVirtualWallMoshi`, `fav_map_*` |
| 定时 | 定时清扫、重复周期、最大时长、指定区域/智能清扫、启停 | `ScheduleSweepActivity`, `ScheduledTaskMoshi`, `SYNC_SCHEDULE_TASK` |
| 状态/传感器 | 电量、充电、DC 连接、主板温度、当前动作、位姿/充电座位姿、传感器状态、错误事件（碰撞/悬崖/尘盒/滚刷/边刷/激光雷达/墙感/水箱/卡住/重定位） | `device.*` 事件键（31 个）、`SensorsStatusMqttModel`、`DeviceEventsMqttModel` |
| 历史/耗材 | 清扫记录、单次面积/时长、累计次数/面积/时长、耗材寿命与重置 | `SweepHistoryActivity`, `ConsumableItemActivity`, `/api/sweeps`, `/api/supplies` |
| 语音 | 语音包下载/切换（15 种语言）、音量、语音升级进度、设备语音版本 | `DeviceVoiceActivity`, `/api/voices`, `SET_DEVICE_VOICE`, `VOICE_VOLUME` |
| 固件/维护 | OTA 升级、升级进度、固件版本、传感器自检 | `FirmwareUpdateActivity`, `/api/devices/{id}/flashes`, `UPDATE_FIRMWARE` |
| 设置 | 童锁、勿扰时段、时区、面积单位、自适应地面检测、Wi-Fi 信息 | `KidsModeActivity`, `DoNotDisturbActivity`, `AdaptiveFloorDetectionActivity`, `SET_TIMEZONE` |
| 账号/分享 | 注册/登录/找回密码（短信/邮箱）、微信/微博登录、设备分享与邀请、试用设备、消息中心、Google Home / Google Assistant / Alexa 绑定 | `/api/users`, `/api/invitations`, `/api/trials`, `GoogleHomeServiceActivity`, `GoogleAssistantActivity`, `alexa_refreash_token` |
| 配网 | BLE 辅助配网、Wi-Fi 列表扫描、国家/区域码 | `WifiScanService`, `ble_read_wifi_list_version`, `ble_set_country` |

`VersionConfigMoshi` 的完整功能开关：`adaptive_floor_detection`, `auto_explore_cn/eu`, `ble_read_wifi_list_version`, `ble_set_country`, `ble_set_time_version`, `clear_map_version`, `device_voice_version`, `device_voice_volume_and_sweep_partition`, `drawing_sweep_version`, `edge_sweep_cn/eu`, `endpoint_setting`, `firmware_success_version`, `google_home_support`, `lambot_minium_firmware`, `load_map_version`, `mop_forbidden_version`, `mop_water_control_version`, `region_schedule_version`, `smart_area_property_version`, `smart_partition_version`, `smart_sweep_schedule_version`, `sweep_direction_version`, `time_zone_setting`, `version`。

---

## 5. Home Assistant 功能映射

| APK 功能 | HA 实体 / 服务 | 实现方式 |
|---|---|---|
| 全屋清扫 / 暂停 / 停止 / 回充 / 寻找 | `vacuum.lambot_*` 的 `start`/`pause`/`stop`/`return_to_base`/`locate` | MQTT `SWEEP`/`STOP`/`GO_HOME`/`FIND_ME` |
| 定点 / 区域 / 分区 / 画线 / 沿边 / 探索 | `lambot_vacuum.clean_spot` / `clean_zone` / `clean_region` / `clean_track` / `start_edge` / `start_explore` | MQTT 对应命令 + `param` |
| 吸力档位 | `select.fan_mode` + `vacuum.set_fan_speed` | `SET_SWEEP_FAN_MODE` |
| 拖地模式 / 清扫方向 | `select.mop_mode` / `select.sweep_direction` | `SET_MOP_MODE` / `SET_SWEEP_DIRECTION` |
| 童锁 / 勿扰 / 水箱 / 智能增压 | `switch.*` | `SET_KID_MODE` / `SET_DO_NOT_DISTURB` / `SET_MOP_MODE` / `SET_SMART_AREA_MODE` |
| 语音音量 / 分区大小 | `number.*` | `VOICE_VOLUME` / `SWEEP_PARTITION_SIZE` |
| 电量 / 温度 / 当前动作 / 坐标 / 面积 / 时长 / 累计 / 耗材 / Wi-Fi / 固件 | 17 个 `sensor.*` | MQTT 遥测 + `/api/sweeps` + `/api/supplies` |
| 地图、虚拟墙、禁区、分区编辑 | `set_virtual_walls` / `load_map` / `clear_map` / `get_sweep_regions` | MQTT + `GET/PUT /api/maps/{id}` |
| 定时清扫 | `lambot_vacuum.set_schedule` | `/api/devices/{id}/scheduled-tasks` |
| 设备属性（云端） | `lambot_vacuum.set_properties` | `PUT /api/devices/{id}/properties` |
| 固件升级 / 传感器 / 时区 | `firmware_update` / `set_sensors` / `get_sensors` / `set_timezone` | MQTT |
| 手动遥控 | `manual_*` 服务 | `FORWARD`/`BACKWARD`/`TURN_LEFT`/`TURN_RIGHT` |
| 任何未覆盖命令 | `lambot_vacuum.raw_command` | 直接发 MQTT 命令名或完整 JSON |

---

## 6. 部署与验证步骤

1. 把 `custom_components/lambot_vacuum/` 复制到 HA 的 `config/custom_components/`，重启 HA。
2. 「设置 → 设备与服务 → 添加集成 → Lambot / SLAMTEC 扫地机」，填写账号、密码、区域、`app_key`/`app_secret`。
3. 若要实时控制，再填远程 MQTT 凭据；或勾选「使用局域网直连」并填机器人 IP（此时用 APK 内置的本地凭据）。
4. 首次建议开 `debug` 日志，观察 `device/{id}/app` 上的实际报文，用 `raw_command` 校对每条命令的 `param`。
5. 逐步在自动化/仪表盘里启用 27 个服务，验证后再把校准过的字段固化到 `const.py` 与 `robohome_mqtt.py`。

### 抓包建议（补齐最后 5%）

- 用 mitmproxy 抓 App 登录，取 `Authorization: Basic` 解码即 `app_key:app_secret`，同时拿到 `/oauth/token` 响应。
- 抓 `GET /prod/user/properties` 与登录后配置下发，寻找远程 MQTT 的 `userName`/`pwd`（当前静态分析未定位到其生成点）。
- 对 MQTT over TLS 8883 用带证书透明代理或 App 本地日志（APK 内保留了 `MQTT Snd:` / `MQTT Rec:` 日志字符串）核对 `param`。
- 逐条触发 App 功能，记录 `device/{id}/robot` 报文，形成命令字典后回填代码。

---

## 7. 证据文件清单（本目录 `rea-analysis/`）

| 文件 | 内容 |
|---|---|
| `05-manifest.json` | 清单解析结果 |
| `06-dex-strings-clean.txt` | 58126 条正确解码的 DEX 字符串（含中文） |
| `07-all-classes.txt` | 12447 个类名 |
| `09-retrofit-api.json` / `10-annotations.json` | 注解级 REST 端点证据 |
| `11-models-keys.json` | Moshi 模型 JSON 字段全集 |
| `12-MqttCommand.json` / `12-MqttDataType.json` | 命令与遥测枚举 |
| `13-rest-api.json` / `API_参考.md` | 65 个 REST 接口表 |
| `MQTT_协议参考.md` | MQTT 协议与枚举表 |
| `java-all/sources/` | 6642 个类的 jadx 反编译源码（0 错误） |

---

## 8. 合规声明

本次分析仅针对用户提供的本地 APK 副本，目的为自有设备的 Home Assistant 互操作。REA 项目与本报告均不提供、也不认可任何绕过授权、破解付费功能、访问他人设备或规避服务条款的用法。集成代码只使用你自己的账号凭据，不内置任何第三方密钥。
