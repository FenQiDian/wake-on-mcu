from errno import EAGAIN
import ctypes
import network
import socket
import struct
import random
import time
import uasyncio as asyncio

from config import WLAN_SSID, WLAN_KEY, BOARD_CAST, TIME_ZONE
from utils import rtc, log_dbg, log_info, ip2int, int2ip

EPOCH_YEAR = time.gmtime(0)[0]
EPOCH_OFFSET = 0
if EPOCH_YEAR == 1970:
    EPOCH_OFFSET = 946684800

IP = None
MASK = None
BOARDCAST = None
GATEWAY = None
DNS = None

def connect_wlan():
    log_info('connect_wlan', 'connect to wlan', WLAN_SSID)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.scan()
    
    if not wlan.isconnected():
        wlan.connect(WLAN_SSID, WLAN_KEY)
        log_dbg('connect_wlan', 'wlan connecting', WLAN_SSID)
    while not wlan.isconnected():
        time.sleep(1) # wait wifi ready
    log_info('connect_wlan', 'wlan connected', WLAN_SSID)

    global IP, MASK, BOARDCAST, GATEWAY, DNS
    IP, MASK, GATEWAY, DNS = wlan.ifconfig()
    BOARDCAST = int2ip(ip2int(IP) | (~ip2int(MASK)))

def check_wlan():
    try:
        wlan = network.WLAN(network.STA_IF)
        return wlan.isconnected()
    except:
        return True

def sync_ntp_time():
    log_info('sync_ntp_time', 'start sync time')

    query = bytearray(48)
    query[0] = 0x1B
    addr = socket.getaddrinfo('ntp.aliyun.com', 123)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(15)
        sock.sendto(query, addr)
        msg = sock.recv(48)
    finally:
        sock.close()
    ntp_time = struct.unpack("!I", msg[40:44])[0]

    if EPOCH_YEAR == 2000:
        # (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
        delta = 3155673600
    elif EPOCH_YEAR == 1970:
        # (date(1970, 1, 1) - date(1900, 1, 1)).days * 24*60*60
        delta = 2208988800
    else:
        raise Exception("Unsupported epoch: {}".format(EPOCH_YEAR))

    tm = time.gmtime(ntp_time - delta + TIME_ZONE * 3600)
    rtc.datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))

    log_info('sync_ntp_time', 'sync time done')

async def send_wol(mac):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 1)
        sock.setblocking(False)

        fmt_mac = _format_mac(mac)
        data = 'FFFFFFFFFFFF' + fmt_mac * 16
        buf = b''
        for i in range(0, len(data), 2):
            buf += struct.pack('B', int(data[i: i + 2], 16))

        for _ in range(0, 10): # 1000ms
            try:
                size = sock.sendto(buf, (BOARD_CAST, 9))
                if size != len(buf):
                    raise Exception("bad size")
                else:
                    log_dbg('send_wol', mac, 'wol ok')
                    return True
            except OSError as err:
                if err.errno != EAGAIN:
                    raise
                await asyncio.sleep_ms(100)
        else:
            raise Exception('timeout')

    finally:
        sock.close()

def _format_mac(mac):
    fmt = ''
    for ch in mac:
        if ch != '-' and ch != ':':
            fmt += ch
    if len(fmt) != 12:
        return None
    return fmt

async def send_shutdown(ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 1)
        sock.setblocking(False)

        buf = b'wom_shutdown'
        for _ in range(0, 10): # 1000ms
            try:
                size = sock.sendto(buf, (ip, 40004))
                if size != len(buf):
                    raise Exception("bad size")
                else:
                    log_dbg('send_shutdown', ip, 'shutdown ok')
                    return True
            except OSError as err:
                if err.errno != EAGAIN:
                    raise
                await asyncio.sleep_ms(100)
        else:
            raise Exception('timeout')

    finally:
        sock.close()

PING_SIZE = 64
PING_PACKET = { # packet header descriptor
    "type": ctypes.UINT8 | 0,
    "code": ctypes.UINT8 | 1,
    "checksum": ctypes.UINT16 | 2,
    "id": ctypes.UINT16 | 4,
    "seq": ctypes.INT16 | 6,
    "timestamp": ctypes.UINT64 | 8,
}

async def do_ping(ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, 1)
        sock.setblocking(False)
        sock.connect((ip, 1))

        sbuf = b'Q' * PING_SIZE
        spkt = ctypes.struct(ctypes.addressof(sbuf), PING_PACKET, ctypes.BIG_ENDIAN)
        spkt.type = 8  # ICMP_ECHO_REQUEST
        spkt.code = 0
        spkt.checksum = 0
        spkt.id = random.randint(0, 65535)
        spkt.seq = 1
        spkt.timestamp = time.ticks_us()
        spkt.checksum = _compute_checksum(sbuf)

        # send ping
        for _ in range(0, 10): # 1000ms
            try:
                size = sock.send(sbuf)
                if size == len(sbuf):
                    log_dbg('do_ping', ip, 'send ok')
                    break
                else:
                    raise Exception("bad size")
            except OSError as err:
                if err.errno != EAGAIN:
                    raise
            await asyncio.sleep_ms(100)
        else:
            log_dbg('do_ping', ip, 'send timeout')
            return False

        # recv ping
        for _ in range(0, 30): # 3000ms
            try:
                rbuf = sock.recv(2048)
                view = memoryview(rbuf)
                # 0: ICMP_ECHO_REPLY
                rpkt = ctypes.struct(ctypes.addressof(view[20:]), PING_PACKET, ctypes.BIG_ENDIAN)
                if rpkt.type == 0 and rpkt.id == spkt.id and rpkt.seq == spkt.seq:
                    log_dbg('do_ping', ip, 'recv ok')
                    return True
            except OSError as err:
                if err.errno != EAGAIN:
                    raise
                await asyncio.sleep_ms(100)
        else:
            log_dbg('do_ping', ip, 'recv timeout')
            return False

    finally:
        sock.close()

def _compute_checksum(data):
    if len(data) & 0x1: # Odd number of bytes
        data += b'\0'
    cs = 0
    for pos in range(0, len(data), 2):
        b1 = data[pos]
        b2 = data[pos + 1]
        cs += (b1 << 8) + b2
    while cs >= 0x10000:
        cs = (cs & 0xffff) + (cs >> 16)
    cs = ~cs & 0xffff
    return cs
