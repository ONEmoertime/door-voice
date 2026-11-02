#include "door.h"

#include "app_config.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "door";
static volatile int64_t s_open_until_ms = 0;

static inline int active_level(int level)
{
    return DOOR_ACTIVE_LEVEL ? level : !level;
}

void door_init(void)
{
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << DOOR_RELAY_GPIO,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&io));
    gpio_set_level(DOOR_RELAY_GPIO, active_level(0)); /* 上电默认释放 */
    ESP_LOGI(TAG, "relay ready on GPIO%d", DOOR_RELAY_GPIO);
}

void door_unlock(void)
{
    int64_t now = esp_timer_get_time() / 1000;
    s_open_until_ms = now + DOOR_UNLOCK_PULSE_MS;

    gpio_set_level(DOOR_RELAY_GPIO, active_level(1));
    ESP_LOGI(TAG, "unlock pulse start (%d ms)", DOOR_UNLOCK_PULSE_MS);

    /* 用独立任务释放，避免阻塞调用方（WS 回调） */
    vTaskDelay(pdMS_TO_TICKS(DOOR_UNLOCK_PULSE_MS));
    gpio_set_level(DOOR_RELAY_GPIO, active_level(0));
    ESP_LOGI(TAG, "unlock pulse end");
}

void door_lock(void)
{
    gpio_set_level(DOOR_RELAY_GPIO, active_level(0));
    s_open_until_ms = 0;
    ESP_LOGI(TAG, "locked");
}

bool door_is_open(void)
{
    return (esp_timer_get_time() / 1000) < s_open_until_ms;
}
