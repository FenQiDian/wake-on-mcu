import React, { useState } from 'react';
import { Box, ChakraProvider, Flex, Heading, Spacer } from "@chakra-ui/react"
import TokenKey from './TokenKey';
import Devices from './Devices';

function App() {
  const [login, setLogin] = useState(false);

  return (
    <ChakraProvider>
      <Box
        position="fixed"
        zIndex="1000"
        w="100%"
        p="10px 2em"
        background="#073b4c"
      >
        <Heading as='h1' size='lg' color="#fff">Wake on MCU</Heading>
      </Box>
      <Box w="100vw" h="100vh" background="#e8e8e8">
        <Box h="56px" />
        <Flex direction="column" align="center" h="calc(100% - 56px)" w="100%" overflowY="auto">
          {
            login ? <Devices /> : <LoginPage onLogin={setLogin.bind(null, true)} />
          }
        </Flex>
      </Box>
    </ChakraProvider>
  );
}

function LoginPage(props: { onLogin: () => void }) {
  return (
    <>
      <Spacer flex="2" />
      <TokenKey onLogin={props.onLogin} />
      <Spacer flex="3" />
    </>
  )
}

export default App;
