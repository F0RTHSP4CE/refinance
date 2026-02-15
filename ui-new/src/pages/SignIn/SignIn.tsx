import { Container, Paper, Text, Title } from '@mantine/core';
import { SignInForm } from '@/components/SignInForm';

export const SignIn = () => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-zinc-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="absolute top-6 left-6">
        <Title order={3} fw={900}>
          Refinance
        </Title>
      </div>

      <Container size="xs" w="100%">
        <div className="sm:mx-auto sm:w-full sm:max-w-md mb-8">
          <Title order={2} ta="center" fw={900}>
            Sign in
          </Title>
          <Text c="dimmed" size="sm" ta="center" mt={5}>
            Enter your username to continue
          </Text>
        </div>

        <Paper withBorder shadow="md" p={30} radius="md">
          <SignInForm />
        </Paper>
      </Container>
    </div>
  );
};
