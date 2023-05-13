import axios from 'axios';
import Base64 from 'crypto-js/enc-base64';
import sha256 from 'crypto-js/sha256';

export function loadTokenKey() {
  return localStorage.getItem('SERVER_TOKEN_KEY') || '';
}

export function saveTokenKey(tokenKey: string) {
  localStorage.setItem('SERVER_TOKEN_KEY', tokenKey);
}

export function signToken(tokenKey: string = '') {
  tokenKey = tokenKey || loadTokenKey();
  if (!tokenKey) {
    return null;
  }
  const now = Math.ceil(Date.now() / 1000) - 946684800;
  const raw = `${now}|${tokenKey}`;
  const b64 = Base64.stringify(sha256(raw));
  return `${now}|${b64}`;
}

export async function testToken(tokenKey: string = '') {
  // return true;
  try {
    const res = await axios({
      method: 'GET',
      url: '/test/token',
      headers: { 'wake-on-mcu-token': signToken(tokenKey) },
    });
    return res.status === 200;
  } catch (err) {
    return false;
  }
}

export type McuInfo = {
  name: string,
  ip: string,
  status: string,
  last: number,
};

export type DeviceInfo = {
  name: string,
  wom: boolean,
  ip: string,
  mac: string,
  status: string,
  command: string,
  commandAt: number,
};

export type AllInfos = {
  mcu: McuInfo,
  devices: Array<DeviceInfo>,
} | null;

export async function getInfos(): Promise<AllInfos> {
  // return {
  //   mcu: {
  //     name: "MCU",
  //     ip: '192.168.0.4',
  //     status: 'online',
  //   },
  //   devices: [
  //     {
  //       name: 'Mini',
  //       wom: true,
  //       ip: '192.168.0.3',
  //       mac: '',
  //       status: 'running',
  //       command: '',
  //     },
  //     {
  //       name: 'Desktop',
  //       wom: true,
  //       ip: '192.168.0.5',
  //       mac: '',
  //       status: 'stopped',
  //       command: '',
  //     },
  //     {
  //       name: 'TV1',
  //       wom: false,
  //       ip: '192.168.0.50',
  //       mac: '',
  //       status: 'running',
  //       command: 'wakeup-DOING',
  //     },
  //     {
  //       name: 'TV2',
  //       wom: false,
  //       ip: '192.168.0.50',
  //       mac: '',
  //       status: 'stopped',
  //       command: 'wakeup-ERROR',
  //     },
  //     {
  //       name: 'TV3',
  //       wom: false,
  //       ip: '192.168.0.50',
  //       mac: '',
  //       status: 'stopped',
  //       command: 'shutdown-DOING',
  //     },
  //   ],
  // };
  const res = await axios({
    method: 'GET',
    url: '/infos',
    headers: { 'wake-on-mcu-token': signToken() },
  });
  if (res.status !== 200) {
    return null;
  }
  return {
    mcu: {
      name: "MCU",
      ip: res.data.muc.ip,
      status: res.data.muc.status,
      last: res.data.muc.last,
    },
    devices: Object.values(res.data.devices)
      .map((dev: any) => ({
        name: dev.name,
        wom: dev.wom,
        ip: dev.ip,
        mac: dev.mac,
        status: dev.status,
        command: dev.command,
        commandAt: dev.commandAt,
      })),
  };
}

export function recvInfos(callback: (infos: AllInfos) => void) {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = window.location.host;
  const ws = new WebSocket(`${protocol}://${host}/web`, btoa(signToken()!));
  ws.onmessage = ((ev) => {
    const pkt = JSON.parse(ev.data);
    if (pkt.type === 'infos') {
      callback({
        mcu: {
          name: "MCU",
          ip: pkt.data.muc.ip,
          status: pkt.data.muc.status,
          last: pkt.data.muc.last,
        },
        devices: Object.values(pkt.data.devices)
          .map((dev: any) => ({
            name: dev.name,
            wom: dev.wom,
            ip: dev.ip,
            mac: dev.mac,
            status: dev.status,
            command: dev.command,
            commandAt: dev.commandAt,
          })),
      });
    }
  });
  return ws;
}

export async function wakeup(name: string) {
  try {
    const res = await axios({
      method: 'POST',
      url: '/command/wakeup',
      params: { name },
      headers: { 'wake-on-mcu-token': signToken() },
    });
    return res.status === 200;
  } catch (err) {
    return false;
  }
}

export async function shutdown(name: string) {
  try {
    const res = await axios({
      method: 'POST',
      url: '/command/shutdown',
      params: { name },
      headers: { 'wake-on-mcu-token': signToken() },
    });
    return res.status === 200;
  } catch (err) {
    return false;
  }
}
