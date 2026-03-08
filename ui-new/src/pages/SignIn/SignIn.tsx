import { Container, Paper, Text, Title } from '@mantine/core';
import { SignInForm } from '@/components/SignInForm';
import logo from '@/assets/logo.png';

export const SignIn = () => {
  return (
    <div
      className="flex min-h-screen flex-col justify-center py-12 sm:px-6 lg:px-8"
      style={{
        background:
          'linear-gradient(120deg, rgba(14, 165, 233, 0.08), rgba(34, 197, 94, 0.08)), var(--mantine-color-body)',
      }}
    >
      <Container size="xs" w="100%">
        <div className="mb-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="mb-8 flex justify-center">
            <img src={logo} alt="Refinance" className="h-auto w-full max-w-[190px]" />
          </div>
          <Title order={2} ta="center" fw={900} c="white">
            Sign in
          </Title>
          <Text c="gray.4" size="sm" ta="center" mt={5}>
            Continue with Telegram, or fall back to your username if the widget is unavailable.
          </Text>
        </div>

        <Paper
          withBorder
          shadow="md"
          p={30}
          radius="md"
          style={{
            background: 'var(--mantine-color-body)',
            borderColor: 'rgba(255,255,255,0.08)',
          }}
        >
          <SignInForm />
        </Paper>
      </Container>
    </div>
  );
};
