import express from 'express';
import bodyParser from 'body-parser';
import * as url from 'url';
import * as wsvr from './web-server';
import * as csvr from "./client-server";

const app = express ();

app.use(express.static("../web/build/"));

app.use(bodyParser.json());
app.use(wsvr.http);

const server = app.listen(3000, () => console.log('server running'));

server.on('upgrade', (request: any, socket: any, head: any) => {
  const { pathname } = url.parse(request.url);
  if (pathname === '/client') {
    csvr.wsServer.handleUpgrade(request, socket, head, socket => {
      csvr.wsServer.emit('connection', socket, request);
    });
  } else if (pathname === '/web') {
    wsvr.wsServer.handleUpgrade(request, socket, head, socket => {
      wsvr.wsServer.emit('connection', socket, request);
    });
  } else {
    socket.destroy();
  }
});
