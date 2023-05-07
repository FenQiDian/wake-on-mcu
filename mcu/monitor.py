import time
import uasyncio as asyncio

from consts import MONITOR_TICK, MONITOR_RETRY_TIMES
from config2 import config2
from utils import log_dbg, log_err_if
from net_utils import do_ping

class Monitor:
    def __init__(self):
        self._version = 0
        self._devices = {}
        self._errors = {}
        self._server_chan = None
    
    async def run(self, server_chan):
        self._server_chan = server_chan

        self._sync_change()
        while True:
            begin = time.ticks_ms()

            for name, dev in config2.devices():
                try:
                    self._devices[name] = self._devices.get(name) or 0
                    ok = await do_ping(dev.ip)
                    if ok:
                        self._devices[name] = 0
                    else:
                        if self._devices[name] < MONITOR_RETRY_TIMES:
                            self._devices[name] += 1

                    self._errors[name] = False

                except Exception as ex:
                    if self._devices[name] < MONITOR_RETRY_TIMES:
                        self._devices[name] += 1

                    log_err_if(not self._errors[name], 'Monitor.run', name, ex)
                    self._errors[name] = True

            log_dbg('Monitor.run', 'devices status', self._devices)
            report = {name: count == 0 for name, count in self._devices.items()}
            self._server_chan.send(('report', report))

            end = time.ticks_ms()
            sleep = max(MONITOR_TICK * 1000 - (end - begin), 0)
            await asyncio.sleep_ms(sleep)

    def is_running(self, name):
        failed_times = self._devices.get(name)
        return failed_times != None and failed_times < MONITOR_RETRY_TIMES

    def _sync_change(self):
        if self._version == config2.version:
            return

        old_devices = self._devices
        old_errors = self._errors
        self._devices = {}
        self._errors = {}
        for name, dev in config2.devices():
            self._devices[name] = old_devices.get(name) or 0
            self._errors[name] = old_errors.get(name) or False

monitor = Monitor()

