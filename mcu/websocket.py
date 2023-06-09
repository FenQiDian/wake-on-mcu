from micropython import const
import binascii
import errno
import random
import re
import socket
import ssl
import struct
import uasyncio.core
import uasyncio.stream

import utils as U

# Opcodes
_OP_CONT = const(0x0)
_OP_TEXT = const(0x1)
_OP_BYTES = const(0x2)
_OP_CLOSE = const(0x8)
_OP_PING = const(0x9)
_OP_PONG = const(0xA)

# Close codes
_CLOSE_OK = const(1000)
_CLOSE_GOING_AWAY = const(1001)
_CLOSE_PROTOCOL_ERROR = const(1002)
_CLOSE_DATA_NOT_SUPPORTED = const(1003)
_CLOSE_BAD_DATA = const(1007)
_CLOSE_POLICY_VIOLATION = const(1008)
_CLOSE_TOO_BIG = const(1009)
_CLOSE_MISSING_EXTN = const(1010)
_CLOSE_BAD_CONDITION = const(1011)

async def connect(url, headers=None):
    match = re.match(r'(wss?)://([A-Za-z0-9-\.]+)(?:\:([0-9]+))?(/.*)?', url)
    if not match:
        raise ValueError('Invalid url %s' % url)

    protocol = match.group(1)
    if protocol not in ['ws', 'wss']:
        raise ValueError('Invalid scheme %s' % protocol)

    port = match.group(3)
    if port is None:
        port = 80 if protocol == 'ws' else 443
    port = int(port)
    
    host = match.group(2)
    path = match.group(4)

    U.log_dbg('websocket.connect', 'start %s' % url)

    stream = await _open_connection(host, port, protocol == 'wss')

    # Sec-WebSocket-Key is 16 bytes of random base64 encoded
    key = binascii.b2a_base64(bytes(random.getrandbits(8) for _ in range(16)))[:-1]

    stream.write(b'GET %s HTTP/1.1\r\n' % (path or '/'))
    stream.write(b'Host: %s:%d\r\n' % (host, port))
    stream.write(b'Connection: Upgrade\r\n')
    stream.write(b'Upgrade: websocket\r\n')
    stream.write(b'Sec-WebSocket-Key: %s\r\n' % key)
    stream.write(b'Sec-WebSocket-Version: 13\r\n')
    stream.write(b'Origin: %s\r\n' % url)
    if headers:
        for k, v in headers.items():
            stream.write(b'%s: %s\r\n' % (k, v))
    stream.write(b'\r\n')

    await stream.drain()

    header = (await stream.readline())
    if not header.startswith(b'HTTP/1.1 101 '):
        raise U.CustomEx('Invalid protocol header')

    # We don't (currently) need these headers
    # FIXME: should we check the return key?
    while header:
        header = await stream.readline()
        if header == b"\r\n":
            break
    U.log_dbg('websocket.connect', 'connected', url)
    
    return WebsocketClient(stream)

# open_connection with ssl support
def _open_connection(host, port, wss=False):
    sock = None
    try:
        ai = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0]
        sock = socket.socket(ai[0], ai[1], ai[2])
        sock.setblocking(False)
        try:
            sock.connect(ai[-1])
        except OSError as err:
            if err.errno != errno.EINPROGRESS:
                raise

        if wss:
            sock = ssl.wrap_socket(sock, server_hostname=host)

        stream = uasyncio.stream.Stream(sock)
        yield uasyncio.core._io_queue.queue_write(sock)
        U.log_info('_open_connection', 'yield & return')
        return stream

    except Exception:
        if sock:
            sock.close()
        raise

class WebsocketClient:
    def __init__(self, stream):
        self._stream = stream
        self.open = True

    async def recv(self):
        popcode = None # previos op code
        buf = bytearray(0)

        while self.open:
            try:
                fin, opcode, data = await self._read_frame()
            except EOFError:
                self.open = False
                return

            # if it's a continuation frame, it's the same data-type
            if opcode == _OP_CONT:
                opcode = popcode
            else:
                buf = bytearray(0)
                popcode = opcode

            if opcode == _OP_TEXT or opcode == _OP_BYTES:
                buf += data

            elif opcode == _OP_CLOSE:
                self.close()
                await self.wait_closed()
                return

            elif opcode == _OP_PONG:
                # Ignore this frame, keep waiting for a data frame
                # note that we are still connected, yah?
                # if we dont get a pong, we aren't connected.
                continue

            elif opcode == _OP_PING:
                # We need to send a pong frame
                self._write_frame(_OP_PONG, data)
                await self._stream.drain()
                continue

            else:
                # unknown opcode
                raise ValueError(opcode)

            if fin:
                # gonna leak a bit since im not clearing the buffer on exit.
                if opcode == _OP_TEXT:
                    return buf.decode('utf-8')
                elif opcode == _OP_BYTES:
                    return buf

    async def _read_frame(self):
        # Frame header
        byte1, byte2 = struct.unpack('!BB', await self._stream.readexactly(2))

        # Byte 1: FIN(1) _(1) _(1) _(1) OPCODE(4)
        fin = bool(byte1 & 0x80)
        opcode = byte1 & 0x0f

        # Byte 2: MASK(1) LENGTH(7)
        mask = bool(byte2 & (1 << 7))
        length = byte2 & 0x7f

        if length == 126:  # Magic number, length header is 2 bytes
            length, = struct.unpack('!H', await self._stream.readexactly(2))
        elif length == 127:  # Magic number, length header is 8 bytes
            length, = struct.unpack('!Q', await self._stream.readexactly(8))

        if mask:  # Mask is 4 bytes
            mask_bits = await self._stream.readexactly(4)

        try:
            data = await self._stream.readexactly(length)
        except MemoryError:
            # We can't receive this many bytes, close the socket
            self.close(code=_CLOSE_TOO_BIG)
            await self._stream.drain()
            return True, _OP_CLOSE, None

        if mask:
            data = bytes(b ^ mask_bits[i % 4] for i, b in enumerate(data))

        return fin, opcode, data

    async def send(self, buf):
        if not self.open:
            return

        if isinstance(buf, str):
            opcode = _OP_TEXT
            buf = buf.encode('utf-8')
        elif isinstance(buf, bytes):
            opcode = _OP_BYTES
        else:
            raise TypeError('invalid buf type')

        self._write_frame(opcode, buf)
        await self._stream.drain()

    def _write_frame(self, opcode, data=b''):
        fin = True
        mask = True
        length = len(data)

        # Frame header
        # Byte 1: FIN(1) _(1) _(1) _(1) OPCODE(4)
        byte1 = 0x80 if fin else 0
        byte1 |= opcode

        # Byte 2: MASK(1) LENGTH(7)
        byte2 = 0x80 if mask else 0

        if length < 126:  # 126 is magic value to use 2-byte length header
            byte2 |= length
            self._stream.write(struct.pack('!BB', byte1, byte2))

        elif length < (1 << 16):  # Length fits in 2-bytes
            byte2 |= 126  # Magic code
            self._stream.write(struct.pack('!BBH', byte1, byte2, length))

        elif length < (1 << 64):
            byte2 |= 127  # Magic code
            self._stream.write(struct.pack('!BBQ', byte1, byte2, length))

        else:
            raise ValueError('invalid length')

        if mask:  # Mask is 4 bytes
            mask_bits = struct.pack('!I', random.getrandbits(32))
            self._stream.write(mask_bits)
            data = bytes(b ^ mask_bits[i % 4] for i, b in enumerate(data))

        self._stream.write(data)

    def close(self, code=_CLOSE_OK, reason=''):
        '''Close the websocket.  Must call await websocket.wait_closed after'''
        if not self.open:
            return

        buf = struct.pack('!H', code) + reason.encode('utf-8')

        self._write_frame(_OP_CLOSE, buf)
        self.open = False

    async def wait_closed(self):
        # drain stream to send off any final frames
        # close the stream (and underlying connection)
        await self._stream.drain()
        await self._stream.wait_closed()
