import axios from 'axios';
import { DateTime } from 'luxon';
import sqlite3 from 'sqlite3';
import { EPOCH_OFFSET, TIAN_API_KEY, TIME_ZONE } from '../config';
import { db } from './db';

//////////////////// Model ////////////////////

let LIST_ALL_DAYS: sqlite3.Statement;
let UPDATE_DAYS: sqlite3.Statement;
let CLEAN_DAYS: sqlite3.Statement;

(async () => {
  await new Promise((resolve, reject) => {
    db.run(`
      CREATE TABLE IF NOT EXISTS days (
        timestamp BIGINT PRIMARY KEY,
        date CHAR(10) NOT NULL,
        holiday INT(1) NOT NULL DEFAULT 0
      )
    `, (err) => err ? reject(err) : resolve(null));
  });

  LIST_ALL_DAYS = db.prepare("SELECT * FROM days ORDER BY timestamp ASC");
  UPDATE_DAYS = db.prepare("INSERT OR REPLACE INTO days (timestamp, date, holiday) VALUES (?, ?, ?)");
  CLEAN_DAYS = db.prepare("DELETE FROM days WHERE timestamp < ?");
})();

type DayType = 'holiday' | 'workday';

function listDays(): Promise<Array<{ date: string, type: DayType }>> {
  return new Promise((resolve, reject) => {
    const days: Array<any> = [];
    LIST_ALL_DAYS.each((err, row: any) => {
      if (err) {
        reject(err);
      }
      days.push({
        date: row.date,
        type: row.holiday ? 'holiday' : 'workday',
      });
    }, (err) => err ? reject(err) : resolve(days));
  });
}

async function updateDay(timestamp: number, date: string, type: DayType) {
  await new Promise((resolve, reject) => {
    UPDATE_DAYS.run([
      timestamp,
      date,
      type == 'holiday',
    ], (err) => err ? reject(err) : resolve(undefined));
  });
}

async function cleanDay(timestamp: number) {
  await new Promise((resolve, reject) => {
    CLEAN_DAYS.run([timestamp], (err) => err ? reject(err) : resolve(undefined));
  });
}

//////////////////// API ////////////////////

async function queryDaysType(first: string, last: string): Promise<Array<{ date: string, type: DayType }>> {
  const url = `https://apis.tianapi.com/jiejiari/index?key=${TIAN_API_KEY}&type=3&date=${first}~${last}`;
  const res = await axios.get(url, {
    headers: {
      "Content-Type": "application/json",
      "apikey": "d9c9b9f6c3e8b3f6d3f1e3e3f1e3f1e3"
    }
  });
  const { data } = res;
  if (data?.code !== 200 || !Array.isArray(data?.result?.list)) {
    throw new Error("Acquire holiday failed");
  }
  return data.result.list.map((item: any) => ({
    date: item.date,
    type: item.isnotwork ? 'holiday' : 'workday',
  }));
}

//////////////////// Service ////////////////////

export async function queryDays(count: number) {
  const now = DateTime.local().setZone(TIME_ZONE).startOf('day');
  const first = now.toFormat('yyyy-MM-dd');
  const last = now.plus({ days: Math.max(count - 1, 1) }).toFormat('yyyy-MM-dd');

  let days = await listDays();
  if (days.length < 0 || days[0]?.date !== first) {
    days = await queryDaysType(first, last);
    for (const day of days) {
      await updateDay(DateTime.fromSQL(day.date).toUnixInteger(), day.date, day.type);
    }
    await cleanDay(now.toUnixInteger());
  }
  
  return days;
}

export function nowEpoch() {
  return Math.round(Date.now() / 1000) - EPOCH_OFFSET;
}
