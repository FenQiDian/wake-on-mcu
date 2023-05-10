from micropython import const
import gc
import time
import uasyncio as asio

import utils as U
import net_utils as N
from config2 import config2

_MONITOR_IDLE_TICK = const(60) # seconds
_MONITOR_BUSY_TICK = const(15) # seconds
_MONITOR_BUSY_COUNT = const(6)
_MONITOR_RETRY_TIMES = const(3)

class Monitor:
    def __init__(self):
        self._version = 0
        self.devices = {}
        self.busy_event = asio.Event()
        self._busy_cnt = 0

        self._server = None
    
    async def run(self, server):
        try:
            self._server = server
            self._sync_config()
            await self._ping_devices()

        except Exception as ex:
            U.log_err('Monitor.run', ex)
            raise

    def _sync_config(self):
        if self._version == config2.version:
            return

        for name in self.devices:
            if not config2.devices.get(name):
                del self.devices[name]

        for name, _ in config2.devices.items():
            if name not in self.devices:
                self.devices[name] = False
    
    async def _ping_devices(self):
        while True:
            begin = time.ticks_ms()
            if self._busy_cnt >= 0:
                self._busy_cnt -= 1

            for name, dev in config2.devices.items():
                self.devices[name] = await N.do_ping(dev.ip)
            U.log_dbg('Monitor.run', 'devices status', self.devices)

            await self._server.send({
                "type": "report",
                "data": self.devices,
            })
            gc.collect()

            while True:
                if self.busy_event.is_set():
                    self.busy_event.clear()
                    self._busy_cnt = _MONITOR_BUSY_COUNT
                tick = _MONITOR_BUSY_TICK if self._busy_cnt > 0 else _MONITOR_IDLE_TICK
                end = time.ticks_ms()
                dura = tick * 1000 - (end - begin)
                if dura <= 0:
                    break
                await asio.sleep(min(dura, _MONITOR_BUSY_TICK))
