def get_block_reward(height: int) -> int:
    halvings = height // 525960
    if halvings >= 10:
        return 0
    return int(4 * 10**8 // (2**halvings))
