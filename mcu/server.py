import binascii
import hashlib
import json
import time
import uasyncio as asyncio

from consts import SERVER_RETRY_DURATION
from config import SERVER_URL, SERVER_TOKEN_KEY, TIME_ZONE
from config2 import config2
from utils import Channel, log_dbg, log_err, log_err_if
from net_utils import EPOCH_OFFSET
import websocket

class Server:
    def __init__(self):
        self._ready = asyncio.Event()
        self._ws = None
        self._chan = Channel(10)
        self._worker_chan = None
        self._streams = {}

        self._conn_err = False
        self._loop_err = 0

    def get_chan(self):
        return self._chan

    async def ready(self, seconds):
        for _ in range(0, seconds):
            if self._ready.is_set():
                return True
            await asyncio.sleep(1)
        else:
            return False

    async def run(self, waker_chan):
        self._worker_chan = waker_chan

        while True:
            await self._connect_ws()

            try:
                t1 = asyncio.create_task(self._send_ws())
                t2 = asyncio.create_task(self._recv_ws())
                await asyncio.gather(t1, t2)
            except Exception as ex:
                now = time.time()
                log_err_if(self._loop_err + 300 < now, 'Server.run', 'loop error', ex)
                self._conn_err = now
            self._ready.clear()

            try:
                t1.cancel()
                t2.cancel()
            except Exception as ex:
                log_err('Server.run', 'cancel error', ex)

    async def _connect_ws(self):
        sleep = 0
        self._ws = None
        while not self._ws:
            try:
                token = _sign_token()
                self._ws = await websocket.connect(SERVER_URL, token)
                log_dbg('Server._connect_ws', 'connect ok')

                self._conn_err = False
                return

            except Exception as ex:
                log_err_if(not self._conn_err, 'Server._connect_ws', 'connect error', ex)
                self._conn_err = True

            sleep = max(sleep + 15, SERVER_RETRY_DURATION)
            await asyncio.sleep(sleep)

    async def _send_ws(self):
        try:
            while True:
                (typ, data) = await self._chan.recv()

                if not self._ws or not self._ws.open:
                    log_dbg('Server._send_ws', 'connection closed')
                    return

                msg = json.dumps({
                    "type": typ,
                    "data": data,
                })
                log_dbg('Server._send_ws', 'send', msg)
                await self._ws.send(msg)

        except asyncio.CancelledError:
            pass
        log_dbg('Server._send_ws', 'task exit')
    
    async def _recv_ws(self):
        try:
            while self._ws and self._ws.open:
                msg = await self._ws.recv()

                if not msg:
                    log_dbg('Server._recv_ws', 'connection closed')
                    return

                elif type(msg) is str:
                    log_dbg('Server._recv_ws', 'recv', msg)
                    pkt = json.loads(msg)

                    if pkt.get('type') == 'config':
                        config2.save(pkt.get('data'))
                        self._ready.set()

                    elif pkt.get('type') == 'wakeup':
                        self._worker_chan.send(pkt)

                    elif pkt.get('type') == 'shutdown':
                        self._worker_chan.send(pkt)

                else:
                    pass

        except asyncio.CancelledError:
            pass
        log_dbg('Server._recv_ws', 'task exit')

def _sign_token():
    now = time.time() - EPOCH_OFFSET - TIME_ZONE * 3600
    raw = b'%d|%s' % (now, SERVER_TOKEN_KEY)
    buf = hashlib.sha256(raw).digest()
    b64 = binascii.b2a_base64(buf)[:-1].decode('utf-8')
    return '%d|%s' % (now, b64)

server = Server()
