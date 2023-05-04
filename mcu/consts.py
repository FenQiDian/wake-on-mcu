from micropython import const

SERVER_RETRY_DURATION = const(30) # seconds
SERVER_TOKEN_EXPIRED = const(180) # seconds

MONITOR_TICK = const(20) # seconds
MONITOR_RETRY_TIMES = const(3)

WAKER_TICK = const(60) # seconds
