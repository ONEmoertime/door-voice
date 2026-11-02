#include "board_audio.h"

#include "app_config.h"
#include "esp_log.h"

static const char *TAG = "audio";

/*
 * TODO(1)：初始化 I2S + ES7210 + ES8311。
 *   - 参考官方例程第 7、8 章，用 esp_codec_dev 创建 codec 句柄；
 *   - 采样率 16000、单声道、16bit，与本文件上面的宏保持一致；
 *   - 双麦建议开启 ES7210 的 AEC，否则喇叭播放时会被自己的声音打断。
 *
 * TODO(2)：PA_EN 由板载 IO 扩展芯片控制（默认拉低＝静音），
 *   必须先初始化 IO 扩展并把 PA_EN 拉高，否则“能采集但没声音”。
 *
 * TODO(3)：唤醒词用 esp-sr 的 WakeNet，命令词用 MultiNet，
 *   命中后直接调用 door_unlock()，不必等云端返回（快通道）。
 */
bool board_audio_init(void)
{
    ESP_LOGW(TAG, "board_audio_init() 尚未实现，请对照官方例程补齐");
    return false;
}

int board_audio_read(int16_t *buf, size_t frames)
{
    (void)buf;
    (void)frames;
    return -1;
}

void board_audio_play(const uint8_t *data, size_t len)
{
    (void)data;
    (void)len;
}

void board_audio_set_pa(bool on)
{
    (void)on;
}
