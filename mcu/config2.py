# config received from server

import json
import re

from utils import log_err, log_info

class Config2:
    def __init__(self):
        self.devices = {}
        self.days = {}
        self.version = 0

    def save(self, cfg):
        try:
            self._apply(cfg)
            with open('config2.json', 'w') as file:
                json.dump(cfg, file)
                log_info('Config2.save', self.devices, self.days)
        except Exception as ex:
            log_err('Config2.save', ex)

    def load(self):
        try:
            with open('config2.json', 'r') as file:
                cfg = json.load(file)
                self._apply(cfg)
                log_info('Config2.load', self.devices, self.days)
        except Exception as ex:
            log_err('Config2.load', ex)

    def _apply(self, cfg):
        if not cfg.get('devices'):
            raise Exception('invalid config2 devices')
        devices = {}
        for name, item in cfg.get('devices').items():
            devices[name] = Device(item)

        if not cfg.get('days'):
            raise Exception('invalid config2 days')    
        days = {}
        for item in cfg.get('days'):
            days[item.get('date')] = item.get('type')
        
        self.devices = devices
        self.days = days
        self.version = (self.version + 1) & 0xFFFFFFFF

config2 = Config2()

class Device:
    def __init__(self, device):
        self.name = device.get('name')
        self.ip = device.get('ip')
        self.mac = device.get('mac')
        if not self.name or not self.ip:
            raise Exception('Device.__init__', 'invalid device')
        self.workday = self._parse_times(device.get('workday'))
        self.holiday = self._parse_times(device.get('holiday'))
        self.anyday = self._parse_times(device.get('anyday'))

    def __repr__(self):
        return json.dumps({
            'name': self.name,
            'ip': self.ip,
            'mac': self.mac,
            'workday': self.workday,
            'holiday': self.holiday,
            'anyday': self.anyday,
        })

    def has_schedule(self):
        return self.holiday is not None or self.workday is not None or self.anyday is not None

    def check_startup(self, date, time_prev, time_now):
        if config2.days.get(date) == 'workday' and self.workday:
            return self._check_times(self.workday, '+', time_prev, time_now)
        elif config2.days.get(date) == 'holiday' and self.holiday:
            return self._check_times(self.holiday, '+', time_prev, time_now)
        elif self.anyday:
            return self._check_times(self.anyday, '+', time_prev, time_now)
        else:
            return False

    def check_shutdown(self, date, time_prev, time_now):
        if config2.days.get(date) == 'workday' and self.workday:
            return self._check_times(self.workday, '-', time_prev, time_now)
        elif config2.days.get(date) == 'holiday' and self.holiday:
            return self._check_times(self.holiday, '-', time_prev, time_now)
        elif self.anyday:
            return self._check_times(self.anyday, '-', time_prev, time_now)
        else:
            return False

    def _parse_times(self, str_times):
        if type(str_times) != list:
            return None
        int_times = []
        for range in str_times:
            res = re.match(r'([\-\+])(\d\d?)\:(\d\d)', range)
            if not res:
                raise Exception('invalid time %s' % range)
            sign, hour, minute = res.group(1), res.group(2), res.group(3)
            mins = int(hour) * 60 + int(minute)
            int_times.append((sign, mins))
        return int_times

    def _check_times(self, times, sign, time_prev, time_now):
        for time in times:
            if time[0] == sign and time_prev <= time[1] <= time_now:
                return True
        return False
