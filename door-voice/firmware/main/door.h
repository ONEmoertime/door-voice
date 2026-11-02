#pragma once

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

void door_init(void);

/* 开门：继电器吸合 DOOR_UNLOCK_PULSE_MS 后释放（脉冲式，避免长时间通电烧线圈） */
void door_unlock(void);

/* 上锁：仅在 fail-secure 的电插锁上有意义；电磁锁断电即开，这里只记录状态 */
void door_lock(void);

/* 返回 true 表示当前为“已开锁”窗口内 */
bool door_is_open(void);

#ifdef __cplusplus
}
#endif
