import React, { useEffect, useState } from 'react';
import { Box, Button, Flex, Grid, Heading, Spacer, Text, useToast } from "@chakra-ui/react"
import { getInfos, wakeup, shutdown, AllInfos, McuInfo, DeviceInfo } from './http';

const GREY = '#b2bec3';
const RED = '#ef476f';
const YELLOW = '#ffc43d'
const GREEN = '#06d6a0'

const CARD_WIDTH = 280;
const CARD_HEIGHT = 180;
const CARD_GAP = 32;
const MAX_COLUMN = 4;

function Devices() {
  const [allInfos, setAllInfos] = useState<AllInfos>(null);

  useEffect(() => {
    let hInterval: any = null;
    (async () => {
      setAllInfos(await getInfos());
      hInterval = setInterval(async () => setAllInfos(await getInfos()), 30000);
    })();
    return () => hInterval && clearTimeout(hInterval);
  }, []);

  const screenColumn = Math.floor((window.innerWidth - CARD_GAP) / (CARD_WIDTH + CARD_GAP));
  const dataColumn = Math.ceil(Math.sqrt(!allInfos ? 0 : allInfos.devices.length + 1));
  const column = Math.max(1, Math.min(screenColumn, dataColumn, MAX_COLUMN));
  const width = CARD_WIDTH * column + CARD_GAP * (column - 1);

  const devices = (allInfos?.devices || []).sort((a: DeviceInfo, b: DeviceInfo) => {
    if (a.status !== b.status) {
      return a.status === 'running' ? -1 : 1;
    } else {
      if (a.wom !== b.wom) {
        return a.wom ? -1 : 1;
      }
      return a.ip.localeCompare(b.ip);
    }
  });

  return (
    <Flex direction="column" minHeight="100%">
      <Spacer flex="1" minHeight={`${CARD_GAP}px`} />
      <Grid
        width={width}
        templateColumns={`repeat(${column}, 1fr)`}
        gap={`${CARD_GAP}px`}
      >
        { !allInfos ? null : <Mcu info={allInfos?.mcu} /> }
        { devices.map((device, idx) => <Device key={idx} info={device} />) }
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
      <Box p="16px 24px 0">
        <Text>Status: {props.info.status}</Text>
        <Text>IP: {props.info.ip}</Text>
      </Box>
      <Spacer />
    </Flex>
  );
}

function Device(props: { info: DeviceInfo }) {
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
  }

  let color = GREY;
  if (props.info.status === 'running') {
    if (props.info.wom) {
      color = GREEN;
    } else {
      color = YELLOW;
    }
  } else if (props.info.status === 'stopped') {
    color = RED;
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
        color="#fff"
        background={color}
      >{props.info.name}</Heading>
      <Box p="16px 24px 0">
        <Text>Status: {props.info.status}</Text>
        <Text>IP: {props.info.ip}</Text>
      </Box>
      <Spacer />
      <Flex direction="row">
        <Spacer />
        <Button
          variant='ghost'
          borderRadius="0"
          color="#1b9aaa"
          isDisabled={!props.info.wom}
          onClick={!props.info.wom ? undefined : onStartUp.bind(null, props.info.name)}
        >Startup</Button>
        <Button
          variant='ghost'
          borderRadius="0"
          color="#ef476f"
          isDisabled={!props.info.wom}
          onClick={!props.info.wom ? undefined : onShutdown.bind(null, props.info.name)}
        >Shutdown</Button>
      </Flex>
    </Flex>
  );
}

export default Devices;
