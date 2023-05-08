import re
import time
import uasyncio as asyncio

from consts import WORKER_TICK, WORKER_OFFSET
from config2 import config2
from utils import rtc, Channel, log_dbg, log_info, log_err, log_err_if
from monitor import monitor
from net_utils import send_wol, send_shutdown, unix_now

class Worker:
    def __init__(self):
        self._chan = Channel(6)
        self._time_err = 0

        self._workday = None
        self._holiday = None
        self._anyday = None

        self._monitor_event = None

    def get_chan(self):
        return self._chan
    
    async def run(self, monitor_event):
        self._monitor_event = monitor_event
        await asyncio.gather(self._by_time(), self._by_remote())

    async def _by_time(self):
        hour, minute = rtc.datetime()[4:6]
        time_now = hour * 60 + minute

        while True:
            timestamp = time.time()
            await asyncio.sleep(timestamp % WORKER_TICK)

            year, month, day, _, hour, minute = rtc.datetime()[:6]
            date = "%04d-%02d-%02d" % (year, month, day)
            time_prev = time_now
            time_now = hour * 60 + minute

            change = False
            for name, dev in config2.devices():
                try:
                    wakeup = dev.check_startup(date, time_prev, time_now)
                    if wakeup and not monitor.is_running(name):
                        log_dbg('Worker._by_time', name, config2.day(date), 'wakeup')
                        await send_wol(dev.mac)
                        change = True
                        continue

                    shutdown = dev.check_shutdown(date, time_prev, time_now)
                    if shutdown and monitor.is_running(name):
                        log_dbg('Worker._by_time', name, config2.day(date), 'shutdown')
                        await send_shutdown(dev.ip)
                        change = True
                        continue

                    if dev.has_schedule():
                        log_dbg('Worker._by_time', name, config2.day(date), 'ignore')

                except Exception as ex:
                    now = time.time()
                    log_err_if(self._time_err + 300 < now, 'Worker._by_time', name, ex)
                    self._conn_err = now

            if change:
                self._monitor_event.set()

    async def _by_remote(self):
        while True:
            try:
                pkt = await self._chan.recv()
                opt = pkt.get('type')
                data = pkt.get('data')
                if not data:
                    continue
                name = data.get('name')
                time = data.get('time')
                if abs(unix_now() - time) > WORKER_OFFSET:
                    continue

                dev = config2.device(name)
                if not dev:
                    log_err('Worker._by_remote', 'invalid name', name)
                    continue

                if opt == 'wakeup':
                    log_info('Worker._by_remote', 'wakeup', name)
                    await send_wol(dev.mac)

                elif opt == 'shutdown':
                    log_info('Worker._by_remote', 'stutdown', name)
                    await send_shutdown(dev.ip)

            except Exception as ex:
                log_err('Worker._by_remote', ex)

worker = Worker()