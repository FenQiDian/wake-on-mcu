from collections import deque

from machine import RTC
from re import match
from uasyncio import Event, sleep_ms

from config import DEBUG_LOG

rtc = RTC()

_file = open('wom.log', 'a')

def log_dbg(fn, *msg):
    if DEBUG_LOG:
        (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
        print("DBG %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn), *msg)

def log_info(fn, *msg):
    (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
    prefix = "INFO %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn)
    print(prefix, *msg)
    print(prefix, *msg, file=_file)
    _file.flush()

def log_err(fn, *msg):
    (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
    prefix = "ERR %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn)
    print(prefix, *msg)
    print(prefix, *msg, file=_file)
    _file.flush()

def log_err_if(cond, fn, *msg):
    if DEBUG_LOG or cond:
        (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
        prefix = "ERR %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn)
        print(prefix, *msg)
        print(prefix, *msg, file=_file)
        _file.flush()

class Channel:
    def __init__(self, size):
        self._size = size
        self._event = Event()
        self._queue = deque((), self._size, 1)

    def send(self, data):
        prev_len = len(self._queue)
        if prev_len >= self._size:
            self._queue.popleft()
        self._queue.append(data)
        if prev_len <= 0:
            self._event.set()

    async def recv(self):
        if len(self._queue) <= 0:
            await self._event.wait()
            self._event.clear()
        data = self._queue.popleft()
        return data

class EventEx:
    def __init__(self, tick_ms = 1000):
        self._event = Event()
        self._tick_ms = tick_ms

    def set(self):
        self._event.set()

    async def wait(self, wait_ms):
        for _ in range(0, wait_ms, self._tick_ms):
            await sleep_ms(self._tick_ms)
            if self._event.is_set():
                self._event.clear()
                return True
        return False

def ip2int(ip):
    res = match(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', ip)
    if not res:
        raise Exception('ip2int', 'invalid ip')
    num = 0
    for idx in range(1, 5):
        byte = int(res.group(idx))
        if byte > 255:
            raise Exception('ip2int', 'invalid ip')
        num = (num << 8) | byte
    return num

def int2ip(num):
    if (num >> 32) > 0:
        raise Exception('int2ip', 'invalid num')
    return "%d.%d.%d.%d" % ((num >> 24) & 0xFF, (num >> 16) & 0xFF, (num >> 8) & 0xFF, num & 0xFF)