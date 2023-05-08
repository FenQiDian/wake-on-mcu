import crypto from 'crypto';
import { EPOCH_OFFSET, SERVER_TOKEN_KEY, SERVER_TOKEN_EXPIRED } from './config';

// export function signToken(key: string) {
//     const now = Math.ceil(Date.now() / 1000) - EPOCH_OFFSET;
//     const raw = `${now}|${key}`;
//     const b64 = crypto.createHash('sha256').update(raw).digest().toString('base64');
//     return `${now}|${b64}`;
// }

export function verifyToken(token: string) {
    if (typeof token !== 'string') {
        return false;
    }
    const [nowX, b64X] = token.split('|');
    const now = Math.ceil(Date.now() / 1000) - EPOCH_OFFSET;
    const nowY = parseInt(nowX || '');
    if (Math.abs(now - nowY) > SERVER_TOKEN_EXPIRED) {
        return false;
    }
    const raw = `${nowX}|${SERVER_TOKEN_KEY}`;
    const b64 = crypto.createHash('sha256').update(raw).digest().toString('base64');
    return b64 === b64X;
}
