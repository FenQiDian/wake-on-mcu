import machine
import uasyncio as asyncio

from config2 import config2
from utils import log_dbg, log_info, log_err
from net_utils import connect_wlan, sync_ntp_time
from server import server
from monitor import monitor
from worker import worker

async def main():
    try:
        log_info('main', 'starting')

        led_init = machine.PWM(machine.Pin(13, machine.Pin.OUT), freq=500)
        led_init.duty(50)
        led_server = machine.PWM(machine.Pin(12, machine.Pin.OUT), freq=500)
        led_server.duty(50)

        connect_wlan()
        sync_ntp_time()
        config2.load()

        server_task = asyncio.create_task(server.run(led_server, worker))
        log_info('main', 'connect to server')
        connected = await server.ready(30)
        led_init.duty(0)

        log_dbg('main', 'running', 'online' if connected else 'offline')
        await asyncio.gather(
            server_task,
            asyncio.create_task(monitor.run(server)),
            asyncio.create_task(worker.run(monitor)),
        )

    except Exception as ex:
        log_err('main', 'error', ex)
        raise ex

asyncio.run(main())

