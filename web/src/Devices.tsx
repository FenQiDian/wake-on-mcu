import React, { useEffect, useState } from 'react';
import { Box, Button, Flex, Grid, Heading, Spacer, useToast } from "@chakra-ui/react"
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
      await props.refresh();
    }
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

  if (props.info.command === 'wakeup') {
    status = "Waking up";
  } else if (props.info.command === 'shutdown') {
    status = "Shutting down";
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
          label={props.info.command ? <PointWave /> : <Point color={pointColor} />}
          content={status}
        />
        <Line label="IP" content={props.info.ip} />
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
      <Box minWidth="24px">{props.label}</Box>
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

function PointWave() {
  return (
    <Box
      position="relative"
      display="inline-block"
      width="12px"
      height="12px"
      borderRadius="12px"
      mr="12px"
      // background={props.color}
      className='ani'
    />
  );
}

export default Devices;
