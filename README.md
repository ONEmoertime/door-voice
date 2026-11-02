# 门禁语音 Agent（作品 B · 硬件版）

用一块**立创·实战派 ESP32-S3**（板载双麦 + 1W 喇叭 + ES7210/ES8311）做“耳朵和嘴巴”，
云端跑 ASR + LLM Agent + TTS 做“大脑”，继电器控制门锁。

目标不是“能聊”，而是**敢让它执行**：指令签名、防重放、二次确认、离线兜底，一个都不能少。

## 架构

```
ESP32-S3（端）                          云服务器（脑）
┌────────────────┐    WebSocket        ┌──────────────────────────┐
│ ES7210 双麦采集 │ ──PCM 帧──────────► │ VAD 断句 → ASR           │
│ 唤醒词 / 命令词  │                     │  → Agent（工具调用）      │
│ ES8311 + 喇叭   │ ◄──TTS 音频──────── │  → TTS                   │
│ 继电器(GPIO10)  │ ◄──签名指令──────── │  → 指令签名 + 审计        │
└────────────────┘                     └──────────────────────────┘
```

**双通道设计**：本地命令词（“开门/关门”）走快通道，<600 ms 直接执行；
复杂语义（“我朋友到了，帮他开一下”）走云端慢通道，1.5–3 s。

## 目录

```
firmware/   ESP-IDF 固件骨架（音频 / WS / 继电器 / 签名校验）
server/     FastAPI + WebSocket 服务（VAD / ASR / Agent / TTS / 审计）
docs/       协议与安全说明
```

## 快速开始（先跑通云端，再上板子）

```bash
cd server
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # 填 API_KEY、DEVICE_TOKENS
python -m app.main              # 没有模型/密钥时会自动进入 mock 模式
```

打开 `http://127.0.0.1:8000/docs` 可以看到接口；`/health` 返回当前各组件是否就绪。

### 第一步：先让云端跑通（不需要板子）

```bash
# 终端 A：起服务
python -m app.main

# 终端 B：用模拟设备走完「理解 → 签名指令 → 校验 → 回执」
python tools/sim_device.py --text "帮我开一下门"
python tools/sim_device.py --text "别开门"      # 应该只收到 reply，没有 command
```

看到 `指令 unlock → 校验 ok` 就说明协议闭环了——**这一步过了再碰硬件**，
否则出问题你分不清是云端、协议还是板子。
![]https://github.com/ONEmoertime/-/blob/main/images/1.png

## 硬件接线

| 信号 | 位置 | 说明 |
|---|---|---|
| 继电器控制 | 多功能接口 **GPIO10** | 3.3V 电平，接光耦隔离继电器模块 |
| 门锁电源 | 独立 12V/2A | 与板子共地，锁两端并联续流二极管 |
| 音频 | 板载 | ES7210 双麦 + ES8311 + NS4150B，**注意 PA_EN 需经 IO 扩展芯片拉高** |

## 安全清单（门锁项目必须逐条打勾）

- [ ] 设备 token 鉴权，未知设备拒绝连接
- [ ] 指令 HMAC 签名 + 时间戳 + nonce，防重放
- [ ] 指令 TTL 5 秒，过期作废
- [ ] 开门动作二次确认（口令 / App）
- [ ] 断网兜底：本地命令词 + 机械钥匙
- [ ] 全量审计日志（谁、何时、什么指令、是否确认）
- [ ] 云端不落原始音频

详见 [docs/protocol.md](docs/protocol.md)。



