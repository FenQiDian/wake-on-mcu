import express from 'express';
import bodyParser from 'body-parser';
import { http } from './http';
import { wsServer } from "./websocket";

const app = express ();

app.use(express.static("../web/build/"));

app.use(bodyParser.json());
app.use(http);

const server = app.listen(3000, () => console.log('server running'));

server.on('upgrade', (request: any, socket: any, head: any) => {
  wsServer.handleUpgrade(request, socket, head, socket => {
    wsServer.emit('connection', socket, request);
  });
});
