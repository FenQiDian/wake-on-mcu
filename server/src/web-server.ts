import express from 'express';
import * as uuid from 'uuid';
import { WebSocketServer, WebSocket } from 'ws';
import * as log from './log';
import * as token from './token';
import * as svc from './service';
import * as csvr from './client-server';

export const http = express.Router();

http.use((req, res, next) => {
  if (token.verifyToken(req.headers['wake-on-mcu-token'] as any)) {
    next();
  } else {
    res.status(401);
    res.json({ error: 'Unauthorized' });
  }
});

http.get('/test/token', async (_req, res) => {
  try {
    res.json({});
    log.info('/test/token');

  } catch (err) {
    res.status(500);
    res.json({ error: 'Server inner error' });
    log.error('/test/token', err);
  }
});

http.get('/infos', async (_req, res) => {
  try {
    res.json(await makeInfos());
    log.info('/infos');

  } catch (err) {
    res.status(500);
    res.json({ error: 'Server inner error' });
    log.error('/test/token', err);
  }
});

async function makeInfos() {
  return {
    muc: {
      name: "Micro",
      ip: csvr.getIpAddress(),
      status: csvr.isConnected() ? "online" : "offline",
      last: csvr.getLastTime(),
    },
    devices: (await svc.listDevices())
      .map((dev) => ({
        ...dev,
        status: csvr.isConnected() ? dev.status : "unknown",
      })),
  };
}

http.post('/command/wakeup', async (req, res) => {
  try {
    const name = req.query['name'] as any;
    if (typeof name !== 'string') {
      res.status(401);
      res.json({ error: 'Invalid request' });
      log.error('/command/wakeup', 401);
      return;
    }
  
    if (!await svc.existDevice(name)) {
      res.status(404);
      res.json({ error: 'Device not found' });
      log.error('/command/wakeup', 404, name);
      return
    }
  
    await csvr.wakeup(name);
    res.json({ error: null });
    log.info('/command/wakeup', name);

  } catch (err) {
    res.status(500);
    res.json({ error: 'Server inner error' });
    log.error('/command/wakeup', err);
  }
});

http.post('/command/shutdown', async (req, res) => {
  try {
    const name = req.query['name'] as any;
    if (typeof name !== 'string') {
      res.status(401);
      res.json({ error: 'Invalid request' });
      log.error('/command/shutdown', 401);
      return;
    }
  
    if (!await svc.existDevice(name)) {
      res.status(404);
      res.json({ error: 'Device not found' });
      log.error('/command/shutdown', 401);
      return
    }

    await csvr.shutdown(name);
    log.info('/command/shutdown', name);
    res.json({ error: null });;

  } catch (err) {
    res.status(500);
    res.json({ error: 'Server inner error' });
    log.error('/command/shutdown', err);
  }
});

export const wsServer = new WebSocketServer({
  noServer: true,
});

export const wsClients = new Map<string, WebSocket>();

wsServer.on('connection', async function onConnection(ws, req) {
  if (!token.verifyToken(atob(req.headers['sec-websocket-protocol'] as any))) {
    log.info('web-ws.onConnection', 'verify token failed');
    log.info('web-ws.onConnection', 'close connection');
    ws.close();
    return;
  }
  log.info('web-ws.onConnection', 'web');

  const id = uuid.v4();
  wsClients.set(id, ws);

  ws.on('close', function onClose() {
    wsClients.delete(id);
    log.info('web-ws.onClose', 'remote closed');
  });

  ws.send(JSON.stringify({
    type: 'infos',
    data: await makeInfos(),    
  }));
});

export async function sendInfos() {
  const msg = JSON.stringify({
    type: 'infos',
    data: await makeInfos(),    
  });
  for (const ws of wsClients.values()) {
    ws.send(msg);
  }
}
