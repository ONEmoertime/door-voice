# 设备 ↔ 云端协议

## 1. 连接

```
ws://<host>/ws/<device_id>?token=<device_token>
```

- `device_id`：设备唯一标识（如 MAC 或自定义序列号）
- `token`：预共享密钥，服务端在 `.env` 的 `DEVICE_TOKENS` 里配置
- 鉴权失败直接 4401 关闭，不进入消息循环

## 2. 帧格式

| 方向 | 类型 | 说明 |
|---|---|---|
| 设备 → 云 | 二进制帧 | PCM16 / 16 kHz / 单声道，每帧 20–60 ms |
| 设备 → 云 | JSON | 控制信令：`hello` / `ping` / `ack` |
| 云 → 设备 | JSON | `command` / `reply` / `pong` |
| 云 → 设备 | 二进制帧 | TTS 音频（MP3/PCM，按 `reply.audio` 声明） |

```json
// 设备上线
{"type":"hello","device_id":"esp32-01","fw":"0.1.0","caps":["pcm16","aec"]}

// 云端下发指令（必须带签名）
{
  "type":"command","cmd_id":"c-7f3a","action":"unlock","door":"front",
  "nonce":"b1e4c9a2","ts":1762000000,"ttl":5000,
  "sig":"9f2c…"
}

// 设备回执
{"type":"ack","cmd_id":"c-7f3a","result":"ok","latency_ms":180}

// 云端文字回复（可选，用于屏幕显示）
{"type":"reply","text":"已为你开门","audio":"mp3"}
```

## 3. 签名算法

```
sig = HMAC_SHA256(device_secret, action + "|" + door + "|" + nonce + "|" + ts)
```

设备侧校验顺序：

1. `abs(now - ts) <= ttl/1000`，否则丢弃（**过期指令不执行**）；
2. 重算签名，与 `sig` 比对（常量时间比较）；
3. 查 nonce 缓存，重复则丢弃（**防重放**）；
4. `action` 是否在白名单内（`unlock` / `lock` / `query`）；
5. `unlock` 额外要求二次确认（口令或 App 确认），否则降级为“请确认”。

## 4. 为什么这么设计

| 风险 | 对策 |
|---|---|
| 抓包重放 | nonce + 时间戳 + TTL |
| 中间人改指令 | HMAC 覆盖 action/door/nonce/ts |
| 云端被攻破 | 设备白名单 + 二次确认 + 审计留痕 |
| 断网变砖 | 本地命令词快通道 + 机械钥匙 |
| 音频隐私 | 端侧 VAD 后才上传，识别完即丢 |

## 5. 错误码

| code | 含义 |
|---|---|
| 4401 | token 无效 |
| 4403 | device_id 不在白名单 |
| 4408 | 指令过期 |
| 4409 | nonce 重复（重放） |
| 4413 | 签名校验失败 |
