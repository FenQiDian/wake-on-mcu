import * as fs from 'fs';
import sqlite3 from 'sqlite3';
import { DEVICES } from '../config';
import { db } from './db';

const OFFLINE_TIMEOUT = 180;

let LIST_ALL: sqlite3.Statement;
let EXIST_DEVICE: sqlite3.Statement;
let UPDATE_RUNNING: sqlite3.Statement;
let UPDATE_STOPPED: sqlite3.Statement;
let UPDATE_WAKEUP: sqlite3.Statement;
let UPDATE_SHUTDOWN: sqlite3.Statement;

(async () => {
  await new Promise((resolve, reject) => {
    db.run(`
      CREATE TABLE IF NOT EXISTS devices (
        name VARCHAR(32) PRIMARY KEY,
        ip VARCHAR(12) DEFAULT '' NOT NULL,
        lastRunning INTEGER DEFAULT 0 NOT NULL,
        lastStopped INTEGER DEFAULT 0 NOT NULL,
        wakeupAt INTEGER DEFAULT 0 NOT NULL,
        shutdownAt INTEGER DEFAULT 0 NOT NULL
      )
    `, (err) => err ? reject(err) : resolve(null));
  });

  LIST_ALL = db.prepare("SELECT * FROM devices");
  EXIST_DEVICE = db.prepare("SELECT COUNT(*) AS count FROM devices WHERE name = ? LIMIT 1");
  UPDATE_RUNNING = db.prepare('UPDATE devices SET lastRunning = ?, wakeupAt = 0 WHERE name = ?');
  UPDATE_STOPPED = db.prepare('UPDATE devices SET lastStopped = ?, shutdownAt = 0 WHERE name = ?');
  UPDATE_WAKEUP = db.prepare(`UPDATE devices SET wakeupAt = ?, shutdownAt = 0 WHERE name = ? AND wakeupAt = 0`);
  UPDATE_SHUTDOWN = db.prepare(`UPDATE devices SET shutdownAt = ?, wakeupAt = 0 WHERE name = ? AND shutdownAt = 0`);

  await initDevices(Object.values(DEVICES));
})();

async function initDevices(devices: Array<{name: string, ip: string}>) {
  for (const {name, ip} of devices) {
    await new Promise((resolve, reject) => {
      db
        .run('INSERT OR IGNORE INTO devices (name) VALUES (?)', name)
        .run('UPDATE devices SET ip = ? WHERE name = ?', ip, name)
        .wait((err) => err ? reject(err) : resolve(null));
    });
  }
  await new Promise((resolve, reject) => {
    const placeholder = devices.map(() => '?').join(',');
    db.run(
      `DELETE FROM devices WHERE ip NOT IN (${placeholder})`,
      devices.map(({ip}) => ip),
      (err) => err ? reject(err) : resolve(null),
    );
  });
}

export function listDevices(): Promise<Array<any>> {
  return new Promise((resolve, reject) => {
    const now = nowUnix();
    const devices: Array<any> = [];
    LIST_ALL.each((err, row: any) => {
      if (err) {
        reject(err);
      }

      const status = row.lastRunning > row.lastStopped && row.lastRunning > now - OFFLINE_TIMEOUT ?
        'running' : 'stopped';
      let command = '';
      let commandAt = 0;
      if (row.shutdownAt) {
        command = 'shutdown';
        commandAt = row.shutdownAt;
      }
      if (row.wakeupAt) {
        command = 'wakeup';
        commandAt = row.wakeupAt;
      }

      devices.push({
        name: row.name,
        wom: !!DEVICES[row.name]?.wom,
        ip: row.ip,
        mac: DEVICES[row.name]?.mac || '',
        status,
        command,
        commandAt,
      });
    }, (err) => err ? reject(err) : resolve(devices));
  });
}

export function existDevice(name: string) {
  return new Promise((resolve, reject) => {
    EXIST_DEVICE.each([name], (err, row: any) => err ? reject(err) : resolve(row.count > 0));
  });
}

export function updateDevice(name: string, status: 'running' | 'stopped') {
  return new Promise((resolve, reject) => {
    if (status === 'running') {
      UPDATE_RUNNING.run([nowUnix(), name], (err) => err ? reject(err) : resolve(undefined));
    } else if (status === 'stopped') {
      UPDATE_STOPPED.run([nowUnix(), name], (err) => err ? reject(err) : resolve(undefined));
    }
  });
}

export function updateWakeup(name: string) {
  return new Promise((resolve, reject) => {
    UPDATE_WAKEUP.run([nowUnix(), name], (err) => err ? reject(err) : resolve(undefined));
  });
}

export function updateShutdown(name: string) {
  return new Promise((resolve, reject) => {
    UPDATE_SHUTDOWN.run([nowUnix(), name], (err) => err ? reject(err) : resolve(undefined));
  });
}

function nowUnix() {
  return Math.floor(Date.now() / 1000);
}

////////////////////////////

export function getDays(): Promise<Record<string, 'holiday' | 'workday'>> {
  return new Promise((resolve, reject) => {
    fs.readFile('./data/days.json', 'utf8', (err, data) => {
      if (err) {
        reject(err);
      }
      resolve(JSON.parse(data));
    });
  });
}

export function setDays(days: Record<string, 'holiday' | 'workday'>) {
  return new Promise((resolve, reject) => {
    fs.writeFile('./data/days.json', JSON.stringify(days), (err) => {
      if (err) {
        reject(err);
      }
      resolve(null);
    });
  });
}
