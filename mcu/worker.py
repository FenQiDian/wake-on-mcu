import re
import time
import uasyncio as asyncio

from consts import WAKER_TICK
from config2 import config2
from utils import rtc, Channel, log_dbg, log_info, log_err, log_err_if
from monitor import monitor
from net_utils import send_wol, send_shutdown

class Worker:
    def __init__(self):
        self._chan = Channel(6)
        self._time_err = 0

        self._workday = None
        self._holiday = None
        self._anyday = None

    def get_chan(self):
        return self._chan
    
    async def run(self):
        await asyncio.gather(self._by_time(), self._by_remote())

    async def _by_time(self):
        hour, minute = rtc.datetime()[4:6]
        time_now = hour * 60 + minute

        while True:
            timestamp = time.time()
            await asyncio.sleep(timestamp % WAKER_TICK)

            year, month, day, _, hour, minute = rtc.datetime()[:6]
            date = "%04d-%02d-%02d" % (year, month, day)
            time_prev = time_now
            time_now = hour * 60 + minute

            for name, dev in config2.devices():
                try:
                    startup = dev.check_startup(date, time_prev, time_now)
                    if startup and not monitor.is_running(name):
                        log_dbg('Worker._by_time', name, config2.day(date), 'startup')
                        await send_wol(dev.mac)
                        continue

                    shutdown = dev.check_shutdown(date, time_prev, time_now)
                    if shutdown and monitor.is_running(name):
                        log_dbg('Worker._by_time', name, config2.day(date), 'shutdown')
                        await send_shutdown(dev.ip)
                        continue

                    log_dbg('Worker._by_time', name, config2.day(date), 'ignore')

                except Exception as ex:
                    now = time.time()
                    log_err_if(self._time_err + 300 < now, 'Worker._by_time', name, ex)
                    self._conn_err = now

    async def _by_remote(self):
        while True:
            try:
                opt, name = await self._chan.recv()

                dev = config2.device(name)
                if not dev:
                    log_err('Worker._by_remote', 'invalid name', name)
                    continue

                if opt == 'startup':
                    log_info('Worker._by_remote', 'startup', name)
                    await send_wol(dev.mac)

                elif opt == 'shutdown':
                    log_info('Worker._by_remote', 'stutdown', name)
                    await send_shutdown(dev.ip)

            except Exception as ex:
                log_err('Worker._by_remote', ex)

worker = Worker()
