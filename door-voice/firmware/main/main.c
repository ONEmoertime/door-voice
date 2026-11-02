#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "app_config.h"
#include "board_audio.h"
#include "cJSON.h"
#include "door.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "net.h"
#include "nvs_flash.h"
#include "secure.h"

static const char *TAG = "main";

static QueueHandle_t s_cmd_queue;

/* WS 回调里只做入队：不能在网络任务里阻塞（door_unlock 有 800ms 脉冲） */
static void on_ws_text(const char *json)
{
    if (json == NULL) {
        return;
    }
    if (xQueueSend(s_cmd_queue, &json, 0) != pdTRUE) {
        ESP_LOGW(TAG, "command queue full, drop");
        free((void *)json);
    }
}

static void send_ack(const char *cmd_id, const char *result, int latency_ms)
{
    char ack[192];
    snprintf(ack, sizeof(ack),
             "{\"type\":\"ack\",\"cmd_id\":\"%s\",\"result\":\"%s\",\"latency_ms\":%d}",
             cmd_id ? cmd_id : "", result, latency_ms);
    net_send_text(ack);
}

static void handle_command(const char *json)
{
    cJSON *root = cJSON_Parse(json);
    if (root == NULL) {
        ESP_LOGW(TAG, "bad json");
        return;
    }

    const cJSON *type = cJSON_GetObjectItem(root, "type");
    if (!cJSON_IsString(type) || strcmp(type->valuestring, "command") != 0) {
        cJSON_Delete(root);
        return;
    }

    const char *action = cJSON_GetStringValue(cJSON_GetObjectItem(root, "action"));
    const char *door_name = cJSON_GetStringValue(cJSON_GetObjectItem(root, "door"));
    const char *nonce = cJSON_GetStringValue(cJSON_GetObjectItem(root, "nonce"));
    const char *sig = cJSON_GetStringValue(cJSON_GetObjectItem(root, "sig"));
    const char *cmd_id = cJSON_GetStringValue(cJSON_GetObjectItem(root, "cmd_id"));
    const cJSON *ts_item = cJSON_GetObjectItem(root, "ts");
    const cJSON *ttl_item = cJSON_GetObjectItem(root, "ttl");

    int64_t ts = cJSON_IsNumber(ts_item) ? (int64_t)ts_item->valuedouble : 0;
    int64_t ttl = cJSON_IsNumber(ttl_item) ? (int64_t)ttl_item->valuedouble : 5000;

    bool ok = secure_verify_command(action, door_name, nonce, ts, ttl, sig);
    if (!ok) {
        ESP_LOGW(TAG, "command rejected");
        send_ack(cmd_id, "rejected", 0);
        cJSON_Delete(root);
        return;
    }

    if (strcmp(action, "unlock") == 0) {
        door_unlock();
        send_ack(cmd_id, "ok", DOOR_UNLOCK_PULSE_MS);
    } else if (strcmp(action, "lock") == 0) {
        door_lock();
        send_ack(cmd_id, "ok", 0);
    } else {
        send_ack(cmd_id, door_is_open() ? "open" : "locked", 0);
    }

    cJSON_Delete(root);
}

static void command_task(void *arg)
{
    char *json = NULL;
    while (true) {
        if (xQueueReceive(s_cmd_queue, &json, portMAX_DELAY) == pdTRUE) {
            handle_command(json);
            free(json);
        }
    }
}

static void audio_task(void *arg)
{
    if (!board_audio_init()) {
        ESP_LOGE(TAG, "audio not ready, upload disabled (fill board_audio.c first)");
        vTaskDelete(NULL);
        return;
    }

    const size_t frames = AUDIO_SAMPLE_RATE * AUDIO_FRAME_MS / 1000;
    int16_t *pcm = malloc(frames * sizeof(int16_t));
    if (pcm == NULL) {
        vTaskDelete(NULL);
        return;
    }

    while (true) {
        int got = board_audio_read(pcm, frames);
        if (got > 0 && net_is_connected()) {
            net_send_bin(pcm, (size_t)got * sizeof(int16_t));
        }
        vTaskDelay(pdMS_TO_TICKS(AUDIO_FRAME_MS));
    }
}

void app_main(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    door_init();

    s_cmd_queue = xQueueCreate(8, sizeof(char *));
    xTaskCreate(command_task, "cmd", 8192, NULL, 6, NULL);

    net_set_text_handler(on_ws_text);
    net_wifi_start();
    net_ws_start();

    xTaskCreate(audio_task, "audio", 8192, NULL, 5, NULL);

    ESP_LOGI(TAG, "door-voice booted, device=%s", DEVICE_ID);
}
