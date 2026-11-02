#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*net_text_handler_t)(const char *json);

/* 初始化 Wi-Fi（阻塞直到连上或重试超限） */
void net_wifi_start(void);

/* 建立 WebSocket 连接；内部自动重连 */
void net_ws_start(void);

/* 注册收到文本帧时的回调（由 main.c 实现指令解析） */
void net_set_text_handler(net_text_handler_t handler);

/* 发送：文本（JSON）或二进制（PCM 音频） */
int net_send_text(const char *json);
int net_send_bin(const void *data, size_t len);

bool net_is_connected(void);

#ifdef __cplusplus
}
#endif
