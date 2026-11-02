#include "net.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "app_config.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_websocket_client.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

static const char *TAG = "net";

#define WIFI_CONNECTED_BIT BIT0
static EventGroupHandle_t s_wifi_events;
static esp_websocket_client_handle_t s_ws;
static net_text_handler_t s_handler;
static volatile bool s_ws_connected;

static void wifi_event_handler(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGW(TAG, "wifi disconnected, retrying...");
        esp_wifi_connect();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)data;
        ESP_LOGI(TAG, "got ip: " IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(s_wifi_events, WIFI_CONNECTED_BIT);
    }
}

void net_wifi_start(void)
{
    s_wifi_events = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t init_cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init_cfg));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                                        wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                                        wifi_event_handler, NULL, NULL));

    wifi_config_t wifi_cfg = {0};
    strlcpy((char *)wifi_cfg.sta.ssid, WIFI_SSID, sizeof(wifi_cfg.sta.ssid));
    strlcpy((char *)wifi_cfg.sta.password, WIFI_PASSWORD, sizeof(wifi_cfg.sta.password));
    wifi_cfg.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "connecting to %s ...", WIFI_SSID);
    xEventGroupWaitBits(s_wifi_events, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);
}

static void ws_event_handler(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    esp_websocket_event_data_t *ev = (esp_websocket_event_data_t *)data;
    switch (id) {
    case WEBSOCKET_EVENT_CONNECTED: {
        s_ws_connected = true;
        ESP_LOGI(TAG, "websocket connected");
        char hello[160];
        snprintf(hello, sizeof(hello),
                 "{\"type\":\"hello\",\"device_id\":\"%s\",\"fw\":\"0.1.0\",\"caps\":[\"pcm16\",\"aec\"]}",
                 DEVICE_ID);
        esp_websocket_client_send_text(s_ws, hello, strlen(hello), pdMS_TO_TICKS(1000));
        break;
    }
    case WEBSOCKET_EVENT_DISCONNECTED:
        s_ws_connected = false;
        ESP_LOGW(TAG, "websocket disconnected");
        break;
    case WEBSOCKET_EVENT_DATA:
        if (ev->op_code == 0x1 && ev->data_len > 0 && s_handler != NULL) {
            char *json = calloc(1, ev->data_len + 1);
            if (json) {
                memcpy(json, ev->data_ptr, ev->data_len);
                s_handler(json); /* 由 main.c 负责释放 */
            }
        } else if (ev->op_code == 0x2) {
            ESP_LOGI(TAG, "audio frame: %d bytes", ev->data_len);
            /* TODO: 送 ES8311 播放（板载喇叭） */
        }
        break;
    case WEBSOCKET_EVENT_ERROR:
        ESP_LOGE(TAG, "websocket error");
        break;
    default:
        break;
    }
}

void net_set_text_handler(net_text_handler_t handler)
{
    s_handler = handler;
}

void net_ws_start(void)
{
    char uri[192];
    snprintf(uri, sizeof(uri), "ws://%s:%d/ws/%s?token=%s",
             SERVER_HOST, SERVER_PORT, DEVICE_ID, DEVICE_TOKEN);

    esp_websocket_client_config_t cfg = {
        .uri = uri,
        .reconnect_timeout_ms = WS_RECONNECT_MIN_MS,
        .network_timeout_ms = 10000,
        .disable_auto_reconnect = false,
    };
    s_ws = esp_websocket_client_init(&cfg);
    esp_websocket_register_events(s_ws, WEBSOCKET_EVENT_ANY, ws_event_handler, NULL);
    esp_websocket_client_start(s_ws);
    ESP_LOGI(TAG, "connecting %s", uri);
}

int net_send_text(const char *json)
{
    if (!s_ws_connected) {
        return -1;
    }
    return esp_websocket_client_send_text(s_ws, json, strlen(json), pdMS_TO_TICKS(1000));
}

int net_send_bin(const void *data, size_t len)
{
    if (!s_ws_connected) {
        return -1;
    }
    return esp_websocket_client_send_bin(s_ws, (const char *)data, len, pdMS_TO_TICKS(1000));
}

bool net_is_connected(void)
{
    return s_ws_connected;
}
