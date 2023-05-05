import machine
import time
import uasyncio as asyncio

from config2 import config2
from utils import log_dbg, log_info, log_err
from net_utils import connect_wlan, check_wlan, sync_ntp_time
from server import server
from monitor import monitor
from worker import worker

async def main():
    try:
        log_info('main', 'starting')

        connect_wlan()
        sync_ntp_time()
        config2.load()

        server_task = asyncio.create_task(server.run(worker.get_chan()))
        log_info('main', 'connect to server')
        connected = await server.ready(30)

        log_dbg('main', 'running', 'online' if connected else 'offline')
        await asyncio.gather(
            asyncio.create_task(change_led()),
            server_task,
            asyncio.create_task(monitor.run(server.get_chan())),
            asyncio.create_task(worker.run()),
        )

    except Exception as ex:
        log_err('main', 'error', ex)
        time.sleep(60)
        machine.reset()

async def change_led():
    led_wlan = machine.Pin(12, machine.Pin.OUT)
    led_server = machine.Pin(13, machine.Pin.OUT)

    while True:
        if check_wlan():
            led_wlan.off()
        else:
            led_wlan.on()

        if server.is_connected():
            led_server.off()
        else:
            led_server.on()

        await asyncio.sleep(30)

asyncio.run(main())

