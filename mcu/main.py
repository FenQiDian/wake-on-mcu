from machine import RTC, Pin
import time
import uasyncio as asyncio

from config2 import config2
from utils import log_dbg, log_info
from net_utils import connect_wlan, check_wlan, sync_ntp_time
from server import server
from monitor import monitor
from worker import worker

async def main():
    log_info('main', 'starting')

    connect_wlan()
    sync_ntp_time()
    config2.load()
    show_led()

    server_task = asyncio.create_task(server.run(worker.get_chan()))
    log_info('main', 'connect to server')
    connected = await server.ready(30)

    log_dbg('main', 'running', 'online' if connected else 'offline')
    await asyncio.gather(
        #asyncio.create_task(show_led()),
        server_task,
        asyncio.create_task(monitor.run(server.get_chan())),
        asyncio.create_task(worker.run()),
    )

def show_led():
    led1 = Pin(12, Pin.OUT)
    led1.off()
    led2 = Pin(13, Pin.OUT)
    led2.off()

    # while True:
    #     if check_wlan():
    #         led1.off()
    #         led2.off()
    #     else:
    #         led1.on()
    #         led2.on()
    #     await asyncio.sleep(30)

asyncio.run(main())

