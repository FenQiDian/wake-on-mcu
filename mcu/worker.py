import time
import uasyncio as asyncio

from config import WORKER_TICK, WORKER_OFFSET
from config2 import config2
from utils import rtc, log_dbg, log_info, log_err
from net_utils import send_wol, send_shutdown, unix_now

class Worker:
    def __init__(self):
        self._monitor = None

    async def run(self, monitor):
        try:
            self._monitor = monitor

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
                for name, dev in config2.devices.items():
                        wakeup = dev.check_startup(date, time_prev, time_now)
                        if wakeup and not self._monitor.devices.get(name):
                            log_dbg('Worker._by_time', name, config2.day.get(date), 'wakeup')
                            await send_wol(dev.mac)
                            change = True
                            continue

                        shutdown = dev.check_shutdown(date, time_prev, time_now)
                        if shutdown and self._monitor.devices.get(name):
                            log_dbg('Worker._by_time', name, config2.day.get(date), 'shutdown')
                            await send_shutdown(dev.ip)
                            change = True
                            continue

                        if dev.has_schedule():
                            log_dbg('Worker._by_time', name, config2.day.get(date), 'ignore')

                if change:
                    self._monitor.busy_event.set()

        except Exception as ex:
            log_err('Worker.run', ex)
            raise

    async def do(self, pkt):
        try:
            opt = pkt.get('type')
            data = pkt.get('data')
            if not data:
                return
            name = data.get('name')
            time = data.get('time')
            if abs(unix_now() - time) > WORKER_OFFSET:
                return

            dev = config2.devices.get(name)
            if not dev:
                log_err('Worker._by_remote', 'invalid name', name)
                return

            if opt == 'wakeup':
                log_info('Worker._by_remote', 'wakeup', name)
                await send_wol(dev.mac)

            elif opt == 'shutdown':
                log_info('Worker._by_remote', 'shutdown', name)
                await send_shutdown(dev.ip)

            self._monitor.busy_event.set()

        except Exception as ex:
            log_err('Worker.do', ex)
            raise

worker = Worker()
