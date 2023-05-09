import Ajv from 'ajv';
import { WebSocketServer, WebSocket } from 'ws';
import { DEVICES } from './config';
import * as log from './log';
import * as token from './token';
import * as svc from './service';

const ajv = new Ajv()

export const wsServer = new WebSocketServer({
  noServer: true,
});

let wsClient: WebSocket | null = null;
let clientIp: string = '';

export function isConnected() {
  return !!wsClient;
}

export function getIpAddress() {
  return clientIp;
}

function setIpAddress(ip: any) {
  if (/\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}/.test(ip)) {
    clientIp = ip;
  }
}

wsServer.on('connection', async function onConnection(ws, req) {
  const ip = req.headers['wake-on-mcu-ip'] as any;
  const mac =req.headers['wake-on-mcu-mac'] as any;
  log.info('websocket.onConnection', 'connection incoming', ip, mac);

  if (!token.verifyToken(req.headers['wake-on-mcu-token'] as any)) {
    log.info('websocket.onConnection', 'verify token failed');
    log.info('websocket.onConnection', 'close connection');
    ws.close();
    return;
  }
  
  if (wsClient) {
    log.info('websocket.onConnection', 'close old connection');
    wsClient.close();
    wsClient = null;
  }
  wsClient = ws;
  log.info('websocket.onConnection', 'accept connection');
  
  wsClient.on('close', function onClose() {
    if (this === wsClient) {
      wsClient = null;
    }
    log.info('websocket.onClose', 'remote closed');
  });

  wsClient.on('message', async function onMessage(pkt, isBinary) {
    try {
      if (!isBinary) {
        const msg = JSON.parse(pkt.toString());
        if (msg?.type === 'report') {
          await onReport(msg);
        } else {
          log.error('websocket.onMessage', `invalid message ${JSON.stringify(msg)}`);
        }
      }

    } catch (err) {
      log.error('websocket.onMessage', err);
    }
  });

  setIpAddress(ip);
  await config();
});

type Arguments<F extends Function> = F extends (...args: infer A) => any ? A : never;
function makeSend<F extends Function>(type: string, times: number, func: F) {
  return async (...arg: Arguments<F>) => {
    if (!wsClient) {
      throw new Error('No connection');
    }
    const msg = {
      type,
      data: await func(...arg),
    };
    for (let i = 0; i < times; i++) {
      await wsClient.send(JSON.stringify(msg));
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    await wsClient.send(`{"type":"flush", "data": "${'0'.repeat(64)}"}`); // flush message
    log.info('websocket.makeSend send ', msg);
  };
}

function makeReceive<F extends Function>(schema: any, func: F) {
  const validate = ajv.compile(schema);
  return async (msg: any) => {
    const { data } = msg;
    log.info('websocket.makeReceive recv', msg);
    if (!validate(data)) {
      throw new Error(`Invalid message ${JSON.stringify(validate.errors)}`);
    }
    await func(data);
  };
}

const config = makeSend('config', 1, async () => {
  return {
    devices: DEVICES,
    days: await svc.queryDays(7),
  };
});

const onReport = makeReceive({
  type: "object",
  additionalProperties: {
    type: "boolean",
  },
}, async (data: any) => {
  for (const [name, running] of Object.entries(data)) {
    await svc.updateDevice(name, running ? 'running' : 'stopped');
  }
});

export const wakeup = makeSend('wakeup', 2, async (name: string) => {
  await svc.updateWakeup(name);
  return {
    name,
    time: svc.nowEpoch(),
  };
});

export const shutdown = makeSend('shutdown', 2, async (name: string) => {
  await svc.updateShutdown(name);
  return {
    name,
    time: svc.nowEpoch(),
  };
});

