import express from 'express';
import bodyParser from 'body-parser';
import { http } from './http';
import "./websocket";

const app = express ();

app.use(express.static("../web/build/"));

app.use(bodyParser.json());
app.use(http);
app.listen(3000, () => console.log('server running'));
