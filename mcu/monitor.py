import asyncio
import time

from config import MONITOR_IDLE_TICK, MONITOR_BUSY_TICK, MONITOR_BUSY_COUNT, MONITOR_RETRY_TIMES
from config2 import config2
from utils import log_dbg, log_err
from net_utils import do_ping

class Monitor:
    def __init__(self):
        self._version = 0
        self._counters = {}
        self.devices = {}
        self.busy_event = asyncio.Event()
        self._busy_cnt = 0

        self._server = None
    
    async def run(self, server):
        try:
            self._server = server
            self._sync_config()
            await self._ping_devices()

        except Exception as ex:
            log_err('Monitor.run', ex)
            raise

    def _sync_config(self):
        if self._version == config2.version:
            return
        
        for name in self._counters:
            if not config2.device(name):
                del self._counters[name]
        for name in self.devices:
            if not config2.device(name):
                del self.devices[name]

        for name, _ in config2.devices():
            if name not in self._counters:
                self._counters[name] = 0
            if name not in self.devices:
                self.devices[name] = False
    
    async def _ping_devices(self):
        while True:
            begin = time.ticks_ms()
            if self._busy_cnt >= 0:
                self._busy_cnt -= 1

            for name, dev in config2.devices():
                self._counters[name] = self._counters.get(name) or 0
                ok = await do_ping(dev.ip)
                if ok:
                    self._counters[name] = 0
                else:
                    if self._counters[name] < MONITOR_RETRY_TIMES:
                        self._counters[name] += 1

                self.devices[name] = self._counters[name] < MONITOR_RETRY_TIMES

            log_dbg('Monitor.run', 'devices status', self._counters)

            await self._server.send({
                "type": "report",
                "data": self.devices,
            })

            while True:
                if self.busy_event.is_set():
                    self.busy_event.clear()
                    self._busy_cnt = MONITOR_BUSY_COUNT
                tick = MONITOR_BUSY_TICK if self._busy_cnt > 0 else MONITOR_IDLE_TICK
                end = time.ticks_ms()
                dura = tick * 1000 - (end - begin)
                if dura <= 0:
                    break
                await asyncio.sleep(min(dura, MONITOR_BUSY_TICK))

monitor = Monitor()
