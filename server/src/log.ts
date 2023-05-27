import { DateTime } from 'luxon';
import { DEBUG_LOG, TIME_ZONE } from './config'

export function debug(where: string, ...args: Array<any>) {
    if (DEBUG_LOG) {
        const now = DateTime.now().setZone(TIME_ZONE).toFormat('yyyy-MM-ddThh:mm:ss') + 'Z';
        console.log(now, where, ...args);
    }
}

export function info(where: string, ...args: Array<any>) {
    const now = DateTime.now().setZone(TIME_ZONE).toFormat('yyyy-MM-ddThh:mm:ss') + 'Z';
    console.log(now, where, ...args);
}

export function error(where: string, ...args: Array<any>) {
    const now = DateTime.now().setZone(TIME_ZONE).toFormat('yyyy-MM-ddThh:mm:ss') + 'Z';
    console.error(now, where, ...args);
}
