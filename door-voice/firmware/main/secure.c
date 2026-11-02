#include "secure.h"

#include <stdio.h>
#include <string.h>
#include <time.h>

#include "app_config.h"
#include "esp_log.h"
#include "mbedtls/md.h"

static const char *TAG = "secure";

/* 最近 16 个 nonce，防重放；掉电丢失可接受（指令 TTL 只有 5 秒） */
#define NONCE_SLOTS 16
static char s_nonces[NONCE_SLOTS][9];
static int s_nonce_idx = 0;

static void canonical(char *out, size_t len, const char *action, const char *door,
                      const char *nonce, int64_t ts)
{
    snprintf(out, len, "%s|%s|%s|%lld", action, door, nonce, (long long)ts);
}

static void hmac_sha256_hex(const char *msg, char out_hex[65])
{
    const mbedtls_md_info_t *info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    unsigned char digest[32];
    mbedtls_md_hmac(info, (const unsigned char *)DEVICE_SECRET, strlen(DEVICE_SECRET),
                    (const unsigned char *)msg, strlen(msg), digest);
    for (int i = 0; i < 32; i++) {
        sprintf(out_hex + i * 2, "%02x", digest[i]);
    }
    out_hex[64] = '\0';
}

void secure_sign(const char *action, const char *door, const char *nonce,
                 int64_t ts, char out_hex[65])
{
    char msg[160];
    canonical(msg, sizeof(msg), action, door, nonce, ts);
    hmac_sha256_hex(msg, out_hex);
}

static bool nonce_seen_and_add(const char *nonce)
{
    for (int i = 0; i < NONCE_SLOTS; i++) {
        if (s_nonces[i][0] != '\0' && strcmp(s_nonces[i], nonce) == 0) {
            return true;
        }
    }
    strlcpy(s_nonces[s_nonce_idx], nonce, sizeof(s_nonces[0]));
    s_nonce_idx = (s_nonce_idx + 1) % NONCE_SLOTS;
    return false;
}

bool secure_verify_command(const char *action, const char *door, const char *nonce,
                           int64_t ts, int64_t ttl_ms, const char *sig_hex)
{
    if (!action || !door || !nonce || !sig_hex) {
        return false;
    }
    if (strcmp(action, "unlock") != 0 && strcmp(action, "lock") != 0 &&
        strcmp(action, "query") != 0) {
        ESP_LOGW(TAG, "action not allowed: %s", action);
        return false;
    }

    int64_t now = (int64_t)time(NULL);
    if (llabs(now - ts) * 1000 > ttl_ms) {
        ESP_LOGW(TAG, "command expired: skew=%lld s", (long long)llabs(now - ts));
        return false;
    }

    char expected[65];
    secure_sign(action, door, nonce, ts, expected);
    if (strcmp(expected, sig_hex) != 0) {
        ESP_LOGW(TAG, "bad signature");
        return false;
    }

    if (nonce_seen_and_add(nonce)) {
        ESP_LOGW(TAG, "replayed nonce: %s", nonce);
        return false;
    }
    return true;
}
