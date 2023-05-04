import Ajv from 'ajv';
import { WebSocketServer, WebSocket } from 'ws';
import { DEVICES } from './config';
import * as log from './log';
import * as token from './token';
import * as svc from './service';

const ajv = new Ajv()

const server = new WebSocketServer({
  port: 22548,
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

server.on('connection', async function onConnection(ws, req) {
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
    wsClient = null;
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
function makeSend<F extends Function>(type: string, func: F) {
  return async (...arg: Arguments<F>) => {
    if (!wsClient) {
      throw new Error('No connection');
    }
    await wsClient.send(JSON.stringify({
      type,
      data: await func(...arg),
    }));
  };
}

function makeReceive<F extends Function>(schema: any, func: F) {
  const validate = ajv.compile(schema);
  return async (msg: any) => {
    const { data } = msg;
    if (!validate(data)) {
      throw new Error(`Invalid message ${JSON.stringify(validate.errors)}`);
    }
    await func(data);
  };
}

const config = makeSend('config', async () => {
  return {
    devices: DEVICES,
    days: await svc.queryDays(7),
  };
});

const onReport = makeReceive({
  type: "object",
  additionalProperties: {
    type: "integer",
  },
}, async (data: any) => {
  for (const [name, failed] of Object.entries(data)) {
    await svc.updateDevice(name, !failed ? 'running' : 'stopped');
  }
});

export const startup = makeSend('startup', async (name: string) => name);

export const shutdown = makeSend('shutdown', async (name: string) => name);
