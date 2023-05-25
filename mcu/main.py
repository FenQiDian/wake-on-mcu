import gc
import machine
import uasyncio as asyncio

import utils as U
import net_utils as N
from config2 import config2
from server import Server
from monitor import Monitor
from worker import Worker

async def main():
    led_init = machine.PWM(machine.Pin(12, machine.Pin.OUT), freq=500)
    led_server = machine.PWM(machine.Pin(13, machine.Pin.OUT), freq=500)

    try:
        U.log_info('main', 'starting')

        server = Server()
        monitor = Monitor()
        worker = Worker()

        gc.enable()
        led_init.duty(50)
        led_server.duty(50)

        N.connect_wlan()
        N.sync_ntp_time()
        config2.load()

        server_task = asyncio.create_task(server.run(led_server, worker))
        U.log_info('main', 'connect to server')
        connected = await server.ready(15)
        led_init.duty(0)

        U.log_dbg('main', 'running', 'online' if connected else 'offline')
        await asyncio.gather(
            server_task,
            asyncio.create_task(monitor.run(server)),
            asyncio.create_task(worker.run(monitor)),
        )

    except Exception as ex:
        U.log_err('main', 'error', ex)
        led_init.duty(50)
        led_server.duty(50)
        await asyncio.sleep(30)
        machine.reset()

asyncio.run(main())

