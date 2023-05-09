import binascii
import errno
import hashlib
import json
import uasyncio as asyncio

from config import SERVER_RETRY_DURATION, SERVER_URL, SERVER_TOKEN_KEY
from config2 import config2
from utils import log_dbg, log_err, log_err_if
from net_utils import unix_now
import websocket

_RETRY_ERRS = (
    errno.EAGAIN,
    errno.ETIMEDOUT,
    errno.ECONNABORTED,
    errno.ECONNREFUSED,
    errno.ECONNRESET,
    errno.EHOSTUNREACH,
    errno.EINPROGRESS,
    118,
    119,
)

class Server:
    def __init__(self):
        self._ws = None
        self._ready = False

        self._led = None
        self._worker = None

        self._conn_err = False

    async def ready(self, seconds = 0):
        if self._ready:
            return True
        for _ in range(0, seconds):
            await asyncio.sleep(1)
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

    async def _connect(self):
        sleep = 0
        self._ws = None

        while not self._ws:
            try:
                token = _sign_token()
                self._ws = await websocket.connect(SERVER_URL, token)
                log_dbg('Server._connect', 'connect ok')

                self._conn_err = False
                return

            except Exception as ex:
                self._ws = None

                log_err_if(not self._conn_err, 'Server._connect', 'connect error', ex)
                self._conn_err = True

                if isinstance(ex, OSError) and ex.errno in _RETRY_ERRS:
                    self._ready = False
                    self._led.duty(0)
                else:
                    raise

            sleep = max(sleep + 15, SERVER_RETRY_DURATION)
            await asyncio.sleep(sleep)

    async def send(self, pkt):
        try:
            if not self._ws or not self._ws.open:
                log_dbg('Server.send', 'connection closed')
                return

            msg = json.dumps(pkt)
            log_dbg('Server.send', 'send', msg)
            await self._ws.send(msg)

        except Exception as ex:
            self._ws = None
            log_err('Server.send', 'send error', ex)

            if isinstance(ex, OSError) and ex.errno in _RETRY_ERRS:
                self._ready = False
                self._led.duty(0)
            else:
                raise
    
    async def _recv(self):
        try:
            while self._ws:
                msg = await self._ws.recv()

                if not msg:
                    log_dbg('Server._recv', 'connection closed')
                    return

                elif type(msg) is str:
                    pkt = json.loads(msg)
                    typ = pkt.get('type')
                    if typ != 'flush':
                        log_dbg('Server._recv', 'recv', msg)

                    if typ == 'config':
                        config2.save(pkt.get('data'))
                        self._led.duty(50)

                    elif typ == 'wakeup' or typ == 'shutdown':
                        await self._worker.do(pkt)

        except Exception as ex:
            self._ws = None
            log_err_if('Server.recv', 'recv error', ex)

            if isinstance(ex, OSError) and ex.errno in _RETRY_ERRS:
                self._ready = False
                self._led.duty(0)
            else:
                raise

        log_dbg('Server._recv', 'task exit')

def _sign_token():
    now = unix_now()
    raw = b'%d|%s' % (now, SERVER_TOKEN_KEY)
    buf = hashlib.sha256(raw).digest()
    b64 = binascii.b2a_base64(buf)[:-1].decode('utf-8')
    return '%d|%s' % (now, b64)

server = Server()
