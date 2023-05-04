from collections import deque
from machine import RTC
from uasyncio import Event

from config import DEBUG_LOG

rtc = RTC()

def log_dbg(fn, *msg):
    if DEBUG_LOG:
        (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
        print("DBG %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn), *msg)

def log_info(fn, *msg):
    (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
    print("INFO %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn), *msg)

def log_err(fn, *msg):
    (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
    print("ERR %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn), *msg)

def log_err_if(cond, fn, *msg):
    if DEBUG_LOG or cond:
        (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
        print("ERR %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn), *msg)

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

def ip2int(ip):
    return reduce(lambda x, y: (x << 8) + y, map(int, ip.split('.')))

def int2ip(num):
    return "%d.%d.%d.%d" % (num >> 24, (num >> 16) & 0xff, (num >> 8) & 0xff, num & 0xff)
