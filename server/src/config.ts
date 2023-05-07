import fs from 'fs';
import yaml from 'yaml';

const file = fs.readFileSync('./data/config.yml', 'utf8');
const C = yaml.parse(file);

export const DEBUG_LOG = !!C.DEBUG_LOG;

export const SERVER_TOKEN_KEY = C.SERVER_TOKEN_KEY || '';
export const SERVER_TOKEN_EXPIRED = C.SERVER_TOKEN_EXPIRED || 300;

export const TIAN_API_KEY = C.TIAN_API_KEY || '';
export const TIME_ZONE = C.TIME_ZONE || '';

export const DEVICES: Record<string, {    
  name: string,
  wom: boolean,
  ip: string,
  mac: string,
  workday?: Array<string>,
  holiday?: Array<string>,
  anyday?: Array<string>,
}> = {};
for (const dev of C.DEVICES || []) {
  if (dev.name && dev.ip) {
    DEVICES[dev.name] = {
      name: dev.name,
      wom: dev.wom === true || dev.wom === undefined,
      ip: dev.ip,
      mac: dev.mac || undefined,
      workday: dev.workday || undefined,
      holiday: dev.holiday || undefined,
      anyday: dev.anyday || undefined,
    };
  }
}
