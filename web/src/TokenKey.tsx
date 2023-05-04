import { Button, Heading, Input, Stack, useToast } from '@chakra-ui/react'
import React, { useEffect, useState } from 'react';
import { loadTokenKey, saveTokenKey, testToken } from './http';

function TokenKey(props: { onLogin: () => void }) {
  const toast = useToast();
  const [tokenKey, setTokenKey] = useState(loadTokenKey());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      if (await testToken(tokenKey)) {
        props.onLogin();
      } else {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return null;
  }

  const onInput = (event: React.ChangeEvent<HTMLInputElement>) => {
    setTokenKey(event.target.value);
  };

  const onClick = async () => {
    console.log(tokenKey);
    if (await testToken(tokenKey)) {
      saveTokenKey(tokenKey)
      props.onLogin();
    } else {
      toast({
        title: 'Invalid token key',
        description: "The token key is invalid. Please input a valid token key.",
        status: 'error',
        duration: 9000,
        isClosable: true,
      });
    }
  };

  return (
    <Stack direction="column" spacing={5} w="320px">
      <Heading size='md'>Server Token Key:</Heading>
      <Input onInput={onInput} size='md' placeholder="token-key-xxxxxxxx" />
      <Button onClick={onClick} size='md'>Start</Button>
    </Stack>
  );
}

export default TokenKey;
