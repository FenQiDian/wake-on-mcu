import express from 'express';
import * as log from './log';
import * as token from './token';
import * as svc from './service';
import * as ws from './websocket';

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
    res.json({
      muc: {
        name: "Micro",
        ip: ws.getIpAddress(),
        status: ws.isConnected() ? "online" : "offline",
      },
      devices: (await svc.listDevices())
        .map((dev) => ({
          ...dev,
          status: ws.isConnected() ? dev.status : "unknown",
        })),
    });
    log.info('/infos');

  } catch (err) {
    res.status(500);
    res.json({ error: 'Server inner error' });
    log.error('/test/token', err);
  }
});

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
  
    await ws.wakeup(name);
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

    await ws.shutdown(name);
    log.info('/command/shutdown', name);
    res.json({ error: null });;

  } catch (err) {
    res.status(500);
    res.json({ error: 'Server inner error' });
    log.error('/command/shutdown', err);
  }
});
