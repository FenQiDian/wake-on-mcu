import React, { useEffect, useState } from 'react';
import { Box, Button, Flex, Grid, Heading, Spacer, Text, useToast } from "@chakra-ui/react"
import { getInfos, recvInfos, wakeup, shutdown, AllInfos, McuInfo, DeviceInfo } from './http';
import './Device.css';

const GREY = '#b2bec3';
const GREY2 = '#7e929a';
const RED = '#ef476f';
const YELLOW = '#ffc43d'
const GREEN = '#06d6a0'

const CARD_WIDTH = 280;
const CARD_HEIGHT = 180;
const CARD_GAP = 32;
const MAX_COLUMN = 4;

function Devices() {
  const [winWidth, setWinWidth] = useState(window.innerWidth);
  const [allInfos, setAllInfos] = useState<AllInfos>(null);

  useEffect(() => {
    window.onresize = () => setWinWidth(window.innerWidth);

    let last = Date.now();

    const ws = recvInfos((infos) => {
      setAllInfos(infos);
      last = Date.now();
    });

    const hInterval = setInterval(async () => {
      if (Date.now() - last > 70 * 1000) {
        setAllInfos(await getInfos());
        last = Date.now();
      }
    }, 10000);

    return () => {
      window.onresize = null;
      ws.close();
      hInterval && clearTimeout(hInterval);
    };
  }, []);

  const screenColumn = Math.floor((winWidth - CARD_GAP) / (CARD_WIDTH + CARD_GAP));
  const dataColumn = Math.ceil(Math.sqrt(!allInfos ? 0 : allInfos.devices.length + 1));
  const column = Math.max(1, Math.min(screenColumn, dataColumn, MAX_COLUMN));
  const width = CARD_WIDTH * column + CARD_GAP * (column - 1);

  const devices = (allInfos?.devices || []).sort((a: DeviceInfo, b: DeviceInfo) => {
    if (a.wom !== b.wom) {
      return a.wom ? -1 : 1;
    }
    return a.ip.localeCompare(b.ip);
  });

  async function refresh() {
    setAllInfos(await getInfos());
  }

  return (
    <Flex direction="column" minHeight="100%">
      <Spacer flex="1" minHeight={`${CARD_GAP}px`} />
      <Grid
        width={width}
        templateColumns={`repeat(${column}, 1fr)`}
        gap={`${CARD_GAP}px`}
        fontSize="16px"
        fontWeight="500"
      >
        { !allInfos ? null : <Mcu info={allInfos?.mcu} /> }
        { devices.map((device, idx) => <Device key={idx} info={device} refresh={refresh} />) }
      </Grid>
      <Spacer flex="2" minHeight={`${CARD_GAP * 2}px`} />
    </Flex>
  );
}

function Mcu(props: { info: McuInfo }) {
  return (
    <Flex
      direction="column"
      w={`${CARD_WIDTH}px`}
      h={`${CARD_HEIGHT}px`}
      background="#fff"
      color="#073b4c"
    >
      <Heading
        size='md'
        p="8px 24px"
        color="#fff"
        background={props.info.status === 'online' ? GREEN : RED}
      >{props.info.name}</Heading>
      <Box p="16px 24px 0" color={GREY2}>
        <Line
          label={<Point color={props.info.status === 'online' ? GREEN : RED} />}
          content={props.info.status === 'online' ? 'Online' : 'Offline'}
        />
        <Line label="IP" content={props.info.ip || 'x.x.x.x'} />
        <Line label="T" content={
          !props.info.last ? '--' :
            <HeartbeatTimer time={props.info.last} />
          }
        />
      </Box>
      <Spacer />
    </Flex>
  );
}

function Device(props: {
  info: DeviceInfo,
  refresh: () => Promise<void>,
}) {
  const toast = useToast();

  async function onStartUp(name: string) {
    if (await wakeup(name)) {
      toast({
        title: `Success`,
        description: `Send wakeup to ${name} done.`,
        status: 'success',
        duration: 6000,
        isClosable: true,
      });
    } else {
      toast({
        title: `Failure`,
        description: `Send wakeup to ${name} failed.`,
        status: 'error',
        duration: 6000,
        isClosable: true,
      });
    }
    await props.refresh();
  }
  
  async function onShutdown(name: string) {
    if (await shutdown(name)) {
      toast({
        title: `Success`,
        description: `Send shutdown to ${name} done.`,
        status: 'success',
        duration: 6000,
        isClosable: true,
      });
    } else {
      toast({
        title: `Failure`,
        description: `Send shutdown to ${name} failed.`,
        status: 'error',
        duration: 6000,
        isClosable: true,
      });
    }
    await props.refresh();
  }

  let barColor = GREY;
  let titleColor = '#FFF';
  let pointColor = GREY;
  let status = "Unknown";
  
  if (props.info.status === 'running') {
    barColor = props.info.wom ? GREEN : YELLOW;
    pointColor = props.info.wom ? GREEN : YELLOW;
    status = "Running";
  } else if (props.info.status === 'stopped') {
    barColor = RED;
    pointColor = RED;
    status = "Stopped";
  }

  let waveColor = "";
  if (props.info.command === 'wakeup') {
    status = "Waking up";
    waveColor = GREEN;
  } else if (props.info.command === 'shutdown') {
    status = "Shutting down";
    waveColor = RED;
  }

  return (
    <Flex
      direction="column"
      w={`${CARD_WIDTH}px`}
      h={`${CARD_HEIGHT}px`}
      background="#fff"
      color="#073b4c"
    >
      <Heading
        size='md'
        p="8px 24px"
        color={titleColor}
        background={barColor}
      >{props.info.name}</Heading>
      <Box p="16px 24px 0" color={GREY2}>
        <Line
          label={props.info.command ? <PointWave color={waveColor} /> : <Point color={pointColor} />}
          content={status}
        />
        <Line label="IP" content={props.info.ip} />
        {!props.info.commandAt ? null : <Line label="D" content={
          <DurationTimer at={props.info.commandAt} />
        } />}
      </Box>
      <Spacer />
      <Flex direction="row">
        <Spacer />
        <Button
          variant='ghost'
          borderRadius="0"
          color={GREEN}
          isDisabled={!props.info.wom}
          onClick={!props.info.wom ? undefined : onStartUp.bind(null, props.info.name)}
        >ON</Button>
        <Button
          variant='ghost'
          borderRadius="0"
          color={RED}
          isDisabled={!props.info.wom}
          onClick={!props.info.wom ? undefined : onShutdown.bind(null, props.info.name)}
        >OFF</Button>
      </Flex>
    </Flex>
  );
}

function Line(props: {
  label: any,
  content: any,
}) {
  return (
    <Flex direction="row" align="center" justify="flex-start">
      <Box minWidth="28px">{props.label}</Box>
      <Box>{props.content}</Box>
    </Flex>
  );
}

function Point(props: { color: string }) {
  return (
    <Box
      display="inline-block"
      width="12px"
      height="12px"
      borderRadius="12px"
      mr="12px"
      background={props.color}
    />
  );
}

function PointWave(props: { color: string }) {
  return (
    <Box
      position="relative"
      display="inline-block"
      width="12px"
      height="12px"
      borderRadius="12px"
      mr="12px"
      background={props.color}
    >
      {
        [1,2,3,4].map(idx => (
          <Flex
            key={idx}
            position="absolute"
            width="112px"
            height="112px"
            left="-50px"
            top="-50px"
            align="center"
            justify="center"
          >
            <Box borderColor={props.color} borderRadius="112px" className={`wave${idx}`} />
          </Flex>
        ))
      }
    </Box>
  );
}

function HeartbeatTimer(props: {
  time: number
}) {
  return (<Text>{
    new Date(props.time * 1000)
    .toISOString()
    .slice(5, 19)
    .replace('T', ' ')
    .replace('-', '/')
  }</Text>);
}

function DurationTimer(props: {
  at: number
}) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const timer = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const dura = Math.max(now - props.at * 1000, 0);
  const h = Math.floor(dura / 3600000);
  const m = Math.floor((dura % 3600000) / 60000);
  const s = Math.floor((dura % 60000) / 1000);
  const hh = h < 10 ? `0${h}` : h;
  const mm = m < 10 ? `0${m}` : m;
  const ss = s < 10 ? `0${s}` : s;

  return (<Text>{
    `${hh}:${mm}:${ss}`
  }</Text>);
}

export default Devices;
