from micropython import const
import binascii
import errno
import gc
import hashlib
import json
import time
import uasyncio as asio

import config as C
import utils as U
import net_utils as N
import websocket as W
from config2 import config2

_SERVER_RETRY_DURATION = const(60) # seconds
_SERVER_TIMEOUT = const(180)

class Server:
    def __init__(self):
        self._ws = None
        self._ready = False
        self._heartbeat = 0

        self._led = None
        self._worker = None

        self._ignores = (
            errno.ETIMEDOUT,
            errno.ECONNABORTED,
            errno.ECONNREFUSED,
            errno.ECONNRESET,
            errno.EHOSTUNREACH,
            errno.ENOTCONN,
            118,
            119,
            -29312,
        )

    async def ready(self, seconds = 0):
        if self._ready:
            return True
        for _ in range(0, seconds):
            await asio.sleep(1)
            if self._ready:
                return True
        else:
            return False

    async def run(self, led, worker):
        self._led = led
        self._worker = worker

        while True:
            await self._connect()
            await self._recv()
            await self._ws.wait_closed()

    async def _connect(self):
        sleep = 0
        self._ws = None

        while not self._ws:
            try:
                gc.collect()

                token = _sign_token()
                self._ws = await W.connect(C.SVR_URL, {
                    'wom-token': token,
                    'wom-ip': N.IP,
                })
                U.log_dbg('Server._connect', 'connect ok')

                self._ready = True
                self._heartbeat = time.time()
                return

            except Exception as ex:
                self._ws = None
                U.log_err('Server._connect', 'connect error', ex)

                self._ready = False
                self._led.duty(50)
                if not isinstance(ex, U.CustomEx) and not (isinstance(ex, OSError) and ex.errno in self._ignores):
                    raise

            sleep = min(sleep + 10, _SERVER_RETRY_DURATION)
            await asio.sleep(sleep)

    async def send(self, pkt):
        try:
            if not self._ws or not self._ws.open:
                U.log_dbg('Server.send', 'connection closed')
                return False

            if time.time() - self._heartbeat > _SERVER_TIMEOUT:
                raise U.CustomEx('heartbeat loss')

            msg = json.dumps(pkt)
            U.log_dbg('Server.send', 'send', msg)
            await self._ws.send(msg)
            return True

        except Exception as ex:
            self._ws.close()
            U.log_err('Server.send', 'send error', ex)

            self._ready = False
            self._led.duty(50)
            if not isinstance(ex, U.CustomEx) and not (isinstance(ex, OSError) and ex.errno in self._ignores):
                raise

        return False
    
    async def _recv(self):
        try:
            while self._ws and self._ws.open:
                msg = await self._ws.recv()

                if not msg:
                    U.log_dbg('Server._recv', 'connection closed')
                    return

                elif type(msg) is str:
                    pkt = json.loads(msg)
                    typ = pkt.get('type')
                    if typ != 'flush':
                        U.log_dbg('Server._recv', 'recv', msg)

                    if typ == 'config':
                        config2.save(pkt.get('data'))
                        self._led.duty(0)

                    elif typ == 'wakeup' or typ == 'shutdown':
                        await self._worker.do(pkt)

                    elif typ == 'heartbeat':
                        self._heartbeat = time.time()

        except Exception as ex:
            self._ws.close()
            U.log_err_if('Server.recv', 'recv error', ex)

            self._ready = False
            self._led.duty(50)
            if not isinstance(ex, U.CustomEx) and not (isinstance(ex, OSError) and ex.errno in self._ignores):
                raise

        U.log_dbg('Server._recv', 'task exit')

def _sign_token():
    now = N.epoch_now()
    raw = b'%d|%s' % (now, C.SVR_KEY)
    buf = hashlib.sha256(raw).digest()
    b64 = binascii.b2a_base64(buf)[:-1].decode('utf-8')
    return '%d|%s' % (now, b64)
