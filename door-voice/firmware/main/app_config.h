#pragma once

/* ============ 需要按实际情况修改的配置 ============ */

/* Wi-Fi */
#define WIFI_SSID       "your-ssid"
#define WIFI_PASSWORD   "your-password"

/* 云服务：服务器 IP + 设备白名单里的 id/token（与 server/.env 的 DEVICE_TOKENS 一致） */
#define SERVER_HOST     "192.168.1.100"     /* 生产环境应为域名 + wss */
#define SERVER_PORT     8000
#define DEVICE_ID       "esp32-01"
#define DEVICE_TOKEN    "dev-secret-change-me"
#define DEVICE_SECRET   "dev-secret-change-me"   /* 用于校验指令签名，建议与 token 分开 */

/* 门锁：多功能接口引出的 GPIO10（继电器控制），板载 IO 扩展芯片不占用 */
#define DOOR_RELAY_GPIO     10
#define DOOR_UNLOCK_PULSE_MS 800      /* 继电器吸合时长 */
#define DOOR_ACTIVE_LEVEL    1        /* 高电平吸合；低电平模块改成 0 */

/* 音频：立创实战派 ESP32-S3 板载 ES7210(双麦) + ES8311 + NS4150B */
#define AUDIO_SAMPLE_RATE   16000
#define AUDIO_CHANNEL       1
#define AUDIO_FRAME_MS      40        /* 每帧 40ms = 640 字节 */

/* 看门狗与重连 */
#define WS_RECONNECT_MIN_MS 1000
#define WS_HEARTBEAT_S      20
