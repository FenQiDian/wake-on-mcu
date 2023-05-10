from errno import EAGAIN
import ctypes
import network
import socket
import struct
import random
import time
import uasyncio as asio

import config as C
import utils as U

class CustomEx(Exception):
    pass

EPOCH = 0
if time.gmtime(0)[0] == 1970:
    EPOCH = 946684800

IP = None
MASK = None
BOARDCAST = None

def connect_wlan():
    U.log_info('connect_wlan', 'connect to wlan', C.WLAN_SSID)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.scan()
    
    if not wlan.isconnected():
        wlan.connect(C.WLAN_SSID, C.WLAN_KEY)
        U.log_dbg('connect_wlan', 'wlan connecting', C.WLAN_SSID)
    while not wlan.isconnected():
        time.sleep(1) # wait wifi ready
    U.log_info('connect_wlan', 'wlan connected', C.WLAN_SSID)

    global IP, MASK, BOARDCAST
    IP, MASK = wlan.ifconfig()[0:2]
    BOARDCAST = U.int2ip(U.ip2int(IP) | (~U.ip2int(MASK)))

def sync_ntp_time():
    U.log_info('sync_ntp_time', 'start sync time')

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

    epoch_year = time.gmtime(0)[0]
    if epoch_year == 2000:
        # (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
        delta = 3155673600
    elif epoch_year == 1970:
        # (date(1970, 1, 1) - date(1900, 1, 1)).days * 24*60*60
        delta = 2208988800
    else:
        raise Exception("Unsupported epoch: {}".format(epoch_year))

    tm = time.gmtime(ntp_time - delta + C.TIME_ZONE * 3600)
    U.rtc.datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))

    U.log_info('sync_ntp_time', 'sync time done')

def epoch_now():
    return time.time() - EPOCH - C.TIME_ZONE * 3600

async def send_wol(mac):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 1)
        sock.setblocking(False)

        buf = bytearray(6 + 16 * 6)
        struct.pack_into('6B', buf, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF)

        if len(mac) != 17:
            raise CustomEx('bad mac')
        mac_num = [0, 0, 0, 0, 0, 0]
        for idx in range(0, 6):
            mac_num[idx] = int(mac[idx * 3:idx * 3 + 2], 16)
        print(mac, mac_num)
        for i in range(0, 16):
            struct.pack_into('6B', buf, 6 + i * 6, *mac_num)
        print(buf)

        for _ in range(0, 10): # 1000ms
            try:
                size = sock.sendto(buf, (BOARDCAST, 9))
                if size != len(buf):
                    raise CustomEx("bad size")
                else:
                    U.log_dbg('send_wol', mac, 'wol ok')
                    return True
            except OSError as err:
                if err.errno != EAGAIN:
                    raise
                await asio.sleep_ms(100)
        else:
            raise CustomEx('timeout')

    except CustomEx as cex:
        U.log_info('send_wol', mac, cex)

    finally:
        sock.close()

async def send_shutdown(ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 1)
        sock.setblocking(False)

        buf = b'wom_shutdown'
        for _ in range(0, 10): # 1000ms
            try:
                size = sock.sendto(buf, (ip, 40004))
                if size != len(buf):
                    raise CustomEx("bad size")
                else:
                    U.log_dbg('send_shutdown', ip, 'shutdown ok')
                    return True
            except OSError as err:
                if err.errno != EAGAIN:
                    raise
                await asio.sleep_ms(100)
        else:
            raise CustomEx('timeout')

    except CustomEx as cex:
        U.log_info('send_shutdown', ip, cex)

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
                    U.log_dbg('do_ping', ip, 'send ok')
                    break
                else:
                    raise CustomEx("bad size")
            except OSError as err:
                if err.errno != EAGAIN:
                    raise
            await asio.sleep_ms(100)
        else:
            raise CustomEx("send timeout")

        # recv ping
        for _ in range(0, 30): # 3000ms
            try:
                rbuf = sock.recv(256)
                view = memoryview(rbuf)
                # 0: ICMP_ECHO_REPLY
                rpkt = ctypes.struct(ctypes.addressof(view[20:]), PING_PACKET, ctypes.BIG_ENDIAN)
                if rpkt.type == 0 and rpkt.id == spkt.id and rpkt.seq == spkt.seq:
                    U.log_dbg('do_ping', ip, 'recv ok')
                    return True
            except OSError as err:
                if err.errno != EAGAIN:
                    raise
                await asio.sleep_ms(100)
        else:
            raise CustomEx("recv timeout")

    except CustomEx as cex:
        U.log_dbg('do_ping', ip, cex)
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
