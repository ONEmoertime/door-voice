#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 指令签名校验：与 server/app/protocol.py 的 canonical/sign 完全对齐 */
bool secure_verify_command(const char *action,
                           const char *door,
                           const char *nonce,
                           int64_t ts,
                           int64_t ttl_ms,
                           const char *sig_hex);

/* 计算签名（调试用；正常不放在设备上） */
void secure_sign(const char *action,
                 const char *door,
                 const char *nonce,
                 int64_t ts,
                 char out_hex[65]);

#ifdef __cplusplus
}
#endif
