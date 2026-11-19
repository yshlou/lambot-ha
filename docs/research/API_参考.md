# Lambot / SLAMTEC 云端 REST API 参考

由 REA + jadx 反编译 `i3/*.java`（Retrofit 接口）自动还原，注解已按原始文件名还原为 HTTP 动词。
共 65 个接口。基础地址见分析报告。

| 接口类 | 方法 | HTTP | 路径 | 参数 | Accept / Content-Type |
|---|---|---|---|---|---|
| DeviceApi | a | `PUT` | `/api/devices/{device_id}:init` | Path:device_id | - |
| DeviceApi | b | `PUT` | `/api/image2path` | - | - |
| DeviceApi | c | `GET` | `/api/devices/{device_id}/properties` | Path:device_id | Accept: application/vnd.slamtec.deviceproperty-v1.0+json |
| DeviceApi | d | `GET` | `/api/devices` | Query:user, Query:filter, Query:page, Query:size, Query:sortby, Query:direction, Query:with_location, Query:with_users, Query:with_owner | Accept: application/vnd.slamtec.devicelist-v1.0+json |
| DeviceApi | e | `PUT` | `/api/devices/{device_id}/properties` | Path:device_id | Content-Type: application/vnd.slamtec.deviceproperty-v1.0+json<br>Accept: application/vnd.slamtec.deviceproperty-v1.0+json |
| DeviceApi | f | `GET` | `/api/devices/{device_id}` | Path:device_id, Query:with_location, Query:with_users, Query:with_owner | Accept: application/vnd.slamtec.device-v1.0+json |
| DeviceApi | g | `DELETE` | `/api/devices/{device_id}/properties/{key}` | Path:device_id, Path:key | - |
| DeviceApi | h | `GET` | `/api/voices` | Query:model_id, Query:manufacturer_id, Query:page, Query:size, Query:sortby, Query:direction | Accept: application/vnd.slamtec.voicepage-v1.0+json |
| DeviceApi | i | `PUT` | `/api/devices/{device_id}` | Path:device_id | Content-Type: application/vnd.slamtec.device-v1.0+json<br>Accept: application/vnd.slamtec.device-v1.0+json |
| DeviceApi | j | `GET` | `/api/devices/{device_id}/flashes` | Path:device_id | - |
| DeviceApi | k | `DELETE` | `/api/devices/{device_id}/users/{user_id}` | Path:device_id, Path:user_id | - |
| DeviceSharingApi | a | `DELETE` | `/api/invitations/devices/{device_id}/users/{user_id}` | Path:device_id, Path:user_id | - |
| DeviceSharingApi | b | `POST` | `/api/invitations/devices/{device_id}/users/{user_id}` | Path:device_id, Path:user_id | - |
| DeviceSharingApi | c | `GET` | `/api/invitations/devices/{device_id}` | Path:device_id, Query:status | - |
| DeviceSharingApi | d | `PUT` | `/api/invitations/devices/{device_id}/users/{user_id}` | Path:device_id, Path:user_id | - |
| DeviceSharingApi | e | `GET` | `/api/invitations` | Query:status | - |
| MapApi | a | `GET` | `/api/maps/{map_id}` | Path:map_id | Accept: application/vnd.slamtec.map-v1.0+json |
| MapApi | b | `GET` | `/api/maps/{map_id}/binary` | Path:map_id | - |
| MobileAppApi | a | `GET` | `/api/apps/latest` | Query:app_name, Query:platform | Accept: application/vnd.slamtec.mobileapp-v1.0+json |
| NotificationApi | b | `PUT` | `/api/messages/broadcasts/{msg_id}` | Path:msg_id, Query:read | - |
| NotificationApi | c | `PUT` | `/api/messages` | Query:all, Query:read | - |
| NotificationApi | d | `GET` | `/api/messages/broadcasts` | Query:page, Query:size, Query:app_name | Accept: application/vnd.slamtec.broadcastlist-v1.0+json |
| NotificationApi | e | `PUT` | `/api/notifications/users/{user_id}` | Path:user_id | Content-Type: application/vnd.slamtec.appinfo-v1.0+json |
| NotificationApi | f | `PUT` | `/api/messages/{msg_id}` | Path:msg_id, Query:read | - |
| NotificationApi | g | `PUT` | `/api/messages/broadcasts` | Query:all, Query:read | - |
| NotificationApi | j | `GET` | `/api/messages` | Query:lang, Query:page, Query:size | Accept: application/vnd.slamtec.messagelist-v1.0+json |
| NotificationApi | k | `PUT` | `/api/messages` | - | Content-Type: application/vnd.slamtec.readlist-v1.0+json |
| NotificationApi | l | `PUT` | `/api/messages/broadcasts` | - | Content-Type: application/vnd.slamtec.readlist-v1.0+json |
| OAuthApi | a | `POST` | `/oauth/wechat/auth_code` | Query:code | - |
| OAuthApi | b | `POST` | `/oauth/token` | Field:refresh_token, Field:grant_type | - |
| OAuthApi | c | `POST` | `/oauth/token` | Field:grant_type | - |
| OAuthApi | d | `POST` | `/oauth/revoke` | Field:token | - |
| OAuthApi | e | `POST` | `/oauth/token` | Field:username, Field:password, Field:grant_type | - |
| PinApi | a | `GET` | `/api/sms/{phone}` | Path:phone | - |
| PinApi | b | `GET` | `/api/email` | Query:account, Query:func, Query:lang, Query:lambot_pin_code | - |
| PinApi | c | `GET` | `/api/check-pin/{phone}/{code}` | Path:phone, Path:code | - |
| ScheduledTaskApi | a | `GET` | `/api/devices/{device_id}/scheduled-tasks` | Path:device_id | Accept: application/vnd.slamtec.scheduledtasklist-v1.0+json |
| ScheduledTaskApi | b | `PUT` | `/api/devices/{device_id}/scheduled-tasks/{task_id}` | Path:device_id, Path:task_id | Content-Type: application/vnd.slamtec.scheduledtask-v1.0+json<br>Accept: application/vnd.slamtec.scheduledtask-v1.0+json<br>Content-Type: application/vnd.slamtec.scheduledtask-v1.0+json<br>Accept: application/vnd.slamtec.scheduledtask-v1.0+json |
| ScheduledTaskApi | c | `POST` | `/api/devices/{device_id}/scheduled-tasks` | Path:device_id | - |
| ScheduledTaskApi | d | `DELETE` | `/api/devices/{device_id}/scheduled-tasks/{task_id}` | Path:device_id, Path:task_id | - |
| SupplyApi | a | `GET` | `/api/supplies/devices/{device_id}` | Path:device_id | Accept: application/vnd.slamtec.supplystatlist-v1.0+json |
| SupplyApi | b | `POST` | `/api/supplies/devices/{device_id}/categories/{category_id}` | Path:device_id, Path:category_id | - |
| TaskApi | a | `GET` | `/api/devices/{device_id}/tasks` | Path:device_id, Query:size, Query:sortby, Query:direction, Query:task, Query:status, Query:with_result | Accept: application/vnd.slamtec.tasklist-v1.0+json |
| TaskApi | b | `GET` | `/api/devices/{device_id}/tasks/{task_id}` | Path:device_id, Path:task_id | Accept: application/vnd.slamtec.task-v1.0+json |
| TaskApi | c | `GET` | `/api/sweeps/devices/{device_id}` | Path:device_id | Accept: application/vnd.slamtec.sweeptotal-v1.0+json |
| TaskApi | d | `GET` | `/api/sweeps/devices/{device_id}/tasks/{task_id}` | Path:device_id, Path:task_id | Accept: application/vnd.slamtec.sweepdetail-v1.0+json |
| TrialSharingApi | a | `GET` | `/api/trials/devices/{device_id}` | Path:device_id | Accept: application/vnd.slamtec.devicetrialstatus-v1.0+json |
| TrialSharingApi | b | `GET` | `/api/trials/devices/{device_id}:share` | Path:device_id | Accept: application/vnd.slamtec.devicetrialcfg-v1.0+json |
| TrialSharingApi | c | `POST` | `/api/trials/devices/{device_id}:trial` | Path:device_id | - |
| TrialSharingApi | d | `DELETE` | `/api/trials/devices/{device_id}:share` | Path:device_id | - |
| TrialSharingApi | e | `GET` | `/api/trials/devices` | - | Accept: application/vnd.slamtec.trialdevicelist-v1.0+json<br>Content-Type: application/vnd.slamtec.devicetrialcfg-v1.0+json |
| TrialSharingApi | f | `POST` | `/api/trials/devices/{device_id}:share` | Path:device_id | - |
| UserApi | a | `POST` | `/api/users/wx` | - | - |
| UserApi | b | `GET` | `/api/users` | Query:account | Accept: application/vnd.slamtec.user-v1.0+json<br>Content-Type: application/vnd.slamtec.user-v1.0+json<br>Accept: application/vnd.slamtec.user-v1.0+json |
| UserApi | c | `POST` | `/api/users` | Header:Accept-Language, Query:enable | - |
| UserApi | d | `GET` | `/api/users/{user_id}` | Path:user_id | Accept: application/vnd.slamtec.user-v1.0+json |
| UserApi | e | `GET` | `/prod/user/properties` | - | - |
| UserApi | f | `GET` | `/api/users/{user_id}:enable` | Path:user_id, Query:code, Query:force | - |
| UserApi | g | `PATCH` | `/api/users/{user_id}/password?source=email` | Path:user_id, Header:Accept-Language | Content-Type: application/vnd.slamtec.userpatch-v1.0+json<br>Accept: application/vnd.slamtec.user-v1.0+json |
| UserApi | h | `DELETE` | `/api/users/{user_id}?permanent=true` | Path:user_id | - |
| UserApi | i | `GET` | `/api/users` | - | Accept: application/vnd.slamtec.user-v1.0+json |
| UserApi | j | `PATCH` | `/api/users/{user_id}/password` | Path:user_id | Content-Type: application/vnd.slamtec.userpatch-v1.0+json<br>Accept: application/vnd.slamtec.user-v1.0+json |
| UserApi | k | `HEAD` | `/api/users` | Query:user | Content-Type: application/vnd.lambot.user-v2.0+json<br>Accept: application/vnd.lambot.user-v2.0+json |
| UserApi | l | `POST` | `/api/users/v2` | Header:Accept-Language, Query:enable | - |
| UserApi | m | `PATCH` | `/api/users/{user_id}` | Path:user_id | Content-Type: application/vnd.slamtec.userpatch-v1.0+json<br>Accept: application/vnd.slamtec.user-v1.0+json |
