#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * 板载音频的薄封装（立创·实战派 ESP32-S3）：
 *   ES7210 双麦（硬件 AEC）→ I2S 采集
 *   ES8311 + NS4150B → I2S 播放，PA_EN 需经板载 IO 扩展芯片拉高
 *
 * 这三个函数是骨架，实现请对照官方例程：
 *   wiki.lckfb.com/zh-hans/szpi-esp32s3/beginner/audio-input-es7210.html
 *   wiki.lckfb.com/zh-hans/szpi-esp32s3/beginner/audio-output-es8311.html
 *   wiki.lckfb.com/zh-hans/szpi-esp32s3/beginner/voice-recognition.html
 */
bool board_audio_init(void);

/* 读一帧 PCM16 单声道；返回实际采样点数，<0 表示失败 */
int board_audio_read(int16_t *buf, size_t frames);

/* 播放一段音频（TTS 回传的 MP3 需先解码） */
void board_audio_play(const uint8_t *data, size_t len);

/* 功放开关（PA_EN） */
void board_audio_set_pa(bool on);

#ifdef __cplusplus
}
#endif
