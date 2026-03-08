import { Container, Grid, Paper, Stack, Text, ThemeIcon, Title } from '@mantine/core';
import { IconArrowUpRight, IconReceipt2, IconWallet } from '@tabler/icons-react';
import { SignInForm } from '@/components/SignInForm';
import { APP_BRAND } from '@/content/uiVocabulary';
import logo from '@/assets/logo.png';

export const SignIn = () => {
  return (
    <div
      className="flex min-h-screen flex-col justify-center py-12 sm:px-6 lg:px-8"
      style={{
        background:
          'radial-gradient(circle at top left, rgba(155, 227, 65, 0.16), transparent 26%), radial-gradient(circle at top right, rgba(88, 181, 255, 0.14), transparent 24%), linear-gradient(180deg, rgba(9,11,14,0.98), rgba(17,19,22,0.98))',
      }}
    >
      <Container size="lg" w="100%">
        <Grid gutter="xl" align="center">
          <Grid.Col span={{ base: 12, lg: 6 }}>
            <Stack gap="xl" pr={{ lg: 'xl' }}>
              <div>
                <img src={logo} alt={APP_BRAND.logoAlt} className="h-auto w-full max-w-[190px]" />
              </div>
              <Stack gap="md">
                <Text className="app-kicker">{APP_BRAND.name}</Text>
                <Title order={1} className="app-page-title" maw={560}>
                  Keep F0RTHSP4CE funded, dues moving, and shared supplies accounted for.
                </Title>
                <Text size="md" maw={520} className="app-muted-copy">
                  Sign in with Telegram when it is available. Username recovery stays here for local
                  testing, widget failures, or accounts that still need to be linked.
                </Text>
              </Stack>

              <Stack gap="sm">
                {[
                  {
                    icon: <IconWallet size={18} />,
                    title: 'Track the space cashflow',
                    description: 'See what is available now, what is reserved in drafts, and what is about to settle.',
                  },
                  {
                    icon: <IconReceipt2 size={18} />,
                    title: 'Stay ahead of dues',
                    description: 'Pending invoices, dues runs, and requests surface before they turn into surprise debt.',
                  },
                  {
                    icon: <IconArrowUpRight size={18} />,
                    title: 'Move money with context',
                    description: 'Transfers, exchanges, and shared-supplies flows stay attached to the right members, actors, and funds.',
                  },
                ].map((item) => (
                  <Paper
                    key={item.title}
                    withBorder
                    radius="xl"
                    p="md"
                    style={{
                      background: 'rgba(255, 255, 255, 0.04)',
                      borderColor: 'var(--app-border-subtle)',
                    }}
                  >
                    <Stack gap={6}>
                      <ThemeIcon
                        size={38}
                        radius="xl"
                        variant="light"
                        style={{
                          background: 'rgba(155, 227, 65, 0.14)',
                          color: 'var(--app-accent)',
                        }}
                      >
                        {item.icon}
                      </ThemeIcon>
                      <Text fw={700}>{item.title}</Text>
                      <Text size="sm" className="app-muted-copy">
                        {item.description}
                      </Text>
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            </Stack>
          </Grid.Col>

          <Grid.Col span={{ base: 12, lg: 6 }}>
            <Paper
              withBorder
              shadow="md"
              p={{ base: 20, sm: 30 }}
              radius="xl"
              style={{
                background: 'linear-gradient(180deg, rgba(28,32,38,0.98), rgba(16,18,22,0.98))',
                borderColor: 'var(--app-border-subtle)',
              }}
            >
              <Stack gap="lg">
                <Stack gap={8}>
                  <Title order={2} fw={900} c="white">
                    Enter {APP_BRAND.shortName}
                  </Title>
                  <Text size="sm" className="app-muted-copy">
                    Telegram is the main path. Username recovery stays available when the widget
                    cannot run in this environment or the account is not linked yet.
                  </Text>
                </Stack>
                <SignInForm />
              </Stack>
            </Paper>
          </Grid.Col>
        </Grid>
      </Container>
    </div>
  );
};
