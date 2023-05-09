from micropython import const

SERVER_RETRY_DURATION = const(30) # seconds

MONITOR_IDLE_TICK = const(60) # seconds
MONITOR_BUSY_TICK = const(15) # seconds
MONITOR_BUSY_COUNT = const(6)
MONITOR_RETRY_TIMES = const(3)

WORKER_TICK = const(60) # seconds
WORKER_OFFSET = const(120) # seconds

########################################

DEBUG_LOG = True

SERVER_URL = 'ws://127.0.0.1/'
WLAN_SSID = 'wlan-name'
WLAN_KEY = 'wlan-key'
TIME_ZONE = 8
SERVER_TOKEN_KEY = 'the-key-same-as-server'
