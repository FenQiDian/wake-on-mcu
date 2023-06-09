from micropython import const
import gc
import time
import uasyncio as asio

import utils as U
import net_utils as N
from config2 import config2

_WORKER_TICK = const(20) # seconds
_WORKER_OFFSET = const(120) # seconds

class Worker:
    def __init__(self):
        self._monitor = None

    async def run(self, monitor):
        try:
            self._monitor = monitor

            hour, minute = U.rtc.datetime()[4:6]
            time_now = hour * 60 + minute

            while True:
                timestamp = time.time()
                await asio.sleep(max(1, _WORKER_TICK - timestamp % _WORKER_TICK))

                year, month, day, _, hour, minute = U.rtc.datetime()[:6]
                date = "%04d-%02d-%02d" % (year, month, day)
                time_prev = time_now
                time_now = hour * 60 + minute

                change = False
                for name, dev in config2.devices.items():
                        wakeup = dev.check_startup(date, time_prev, time_now)
                        if wakeup and not self._monitor.devices.get(name):
                            U.log_dbg('Worker.run', name, config2.days.get(date), 'wakeup')
                            for _ in range(0, 3):
                                await N.send_wol(dev.mac)
                                await asio.sleep(1)
                            change = True
                            continue

                        shutdown = dev.check_shutdown(date, time_prev, time_now)
                        if shutdown and self._monitor.devices.get(name):
                            U.log_dbg('Worker.run', name, config2.days.get(date), 'shutdown')
                            for _ in range(0, 3):
                                await N.send_shutdown(dev.ip)
                                await asio.sleep(1)
                            change = True
                            continue

                        if dev.has_schedule():
                            U.log_dbg('Worker.run', name, config2.days.get(date), 'ignore')

                if change:
                    self._monitor.busy_event.set()
                    gc.collect()

        except Exception as ex:
            U.log_err('Worker.run', ex)
            raise

    async def do(self, pkt):
        try:
            opt = pkt.get('type')
            data = pkt.get('data')
            if not data:
                return
            name = data.get('name')
            time = data.get('time')
            if abs(N.epoch_now() - time) > _WORKER_OFFSET:
                return

            dev = config2.devices.get(name)
            if not dev:
                U.log_err('Worker._by_remote', 'invalid name', name)
                return

            if opt == 'wakeup':
                U.log_info('Worker._by_remote', 'wakeup', name)
                await N.send_wol(dev.mac)

            elif opt == 'shutdown':
                U.log_info('Worker._by_remote', 'shutdown', name)
                await N.send_shutdown(dev.ip)

            self._monitor.busy_event.set()
            gc.collect()

        except Exception as ex:
            U.log_err('Worker.do', ex)
            raise
