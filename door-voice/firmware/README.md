# 固件（ESP-IDF / ESP32-S3）

目标板：**立创·实战派 ESP32-S3**（ESP32-S3-WROOM-1-N16R8，板载 ES7210 双麦 + ES8311 + NS4150B 喇叭）。

## 编译烧录

```bash
idf.py set-target esp32s3
idf.py menuconfig      # Component config → ESP PSRAM → 打开 Octal 模式
idf.py build flash monitor
```

> PSRAM 必须打开（录音环形缓冲要用到），否则 `malloc` 大块内存会失败。

## 引脚

| 功能 | 引脚 | 说明 |
|---|---|---|
| 继电器 | **GPIO10** | 多功能接口 GH 端子引出；接 3.3V 兼容光耦继电器 |
| 门锁电源 | 外部 12V | 与板子共地，锁两端并联续流二极管 |
| 音频 | 板载 | ES7210 / ES8311；`PA_EN` 由 IO 扩展芯片控制 |

## 文件职责

| 文件 | 作用 |
|---|---|
| `main.c` | 启动流程、指令队列、命令解析与执行、音频上传任务 |
| `net.c` | Wi-Fi STA + WebSocket 客户端 + 自动重连 |
| `door.c` | 继电器脉冲开锁、状态维护 |
| `secure.c` | HMAC-SHA256 签名校验、时间窗、nonce 防重放 |
| `board_audio.c` | 板载音频薄封装（**待你按官方例程补齐**） |
| `app_config.h` | 所有需要改的宏：Wi-Fi、服务器、GPIO、音频参数 |

## 待补齐（按优先级）

1. **`board_audio.c`**：I2S + ES7210/ES8311 初始化，参考官方例程第 7、8 章；
2. **PA_EN**：IO 扩展芯片拉高，否则“能录不能放”；
3. **唤醒词**：esp-sr WakeNet + MultiNet，命中“开门”直接本地执行（快通道）；
4. **TTS 播放**：云端回的是 MP3，需要解码后送 ES8311（可用 esp-audio-libs 或改回 PCM）；
5. **OTA**：门禁设备拆机烧录成本高，建议第一版就留 OTA 分区。

## 联调步骤

1. 先只烧 `net.c` 部分：确认串口打印 `websocket connected`，服务器 `/health` 里 `devices_online=1`；
2. 再把继电器接上，用服务器 `/docs` 或脚本发一条 `unlock` 指令，确认“咔哒”一声；
3. 最后接音频，确认能上传 PCM、服务器 `/audit` 能看到 `audio_received`。
