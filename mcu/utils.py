from machine import RTC
from re import match

import config as C

class CustomEx(Exception):
    pass

rtc = RTC()

_file = open('wom.log', 'a')

def log_dbg(fn, *msg):
    if C.DEBUG:
        (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
        print("DBG %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn), *msg)

def log_info(fn, *msg):
    (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
    prefix = "INFO %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn)
    print(prefix, *msg)
    print(prefix, *msg, file=_file)
    _file.flush()

def log_err(fn, *msg):
    (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
    prefix = "ERR %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn)
    print(prefix, *msg)
    print(prefix, *msg, file=_file)
    _file.flush()

def log_err_if(cond, fn, *msg):
    if C.DEBUG or cond:
        (month, day, _, hour, minute, second) = rtc.datetime()[1:-1]
        prefix = "ERR %02d/%02d %d:%d:%d %s:" % (month, day, hour, minute, second, fn)
        print(prefix, *msg)
        print(prefix, *msg, file=_file)
        _file.flush()

def ip2int(ip):
    res = match(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', ip)
    if not res:
        raise Exception('ip2int', 'invalid ip')
    num = 0
    for idx in range(1, 5):
        byte = int(res.group(idx))
        if byte > 255:
            raise Exception('ip2int', 'invalid ip')
        num = (num << 8) | byte
    return num

def int2ip(num):
    if (num >> 32) > 0:
        raise Exception('int2ip', 'invalid num')
    return "%d.%d.%d.%d" % ((num >> 24) & 0xFF, (num >> 16) & 0xFF, (num >> 8) & 0xFF, num & 0xFF)
