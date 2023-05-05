from micropython import const

SERVER_RETRY_DURATION = const(30) # seconds

MONITOR_TICK = const(20) # seconds
MONITOR_RETRY_TIMES = const(3)

WORKER_TICK = const(60) # seconds
WORKER_OFFSET = const(120) # seconds
