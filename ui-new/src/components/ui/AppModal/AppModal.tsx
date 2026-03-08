import { Box, Drawer, Group, ScrollArea, Stack, Text, type DrawerProps } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import type { ReactNode } from 'react';

export type AppModalVariant = 'compact' | 'form' | 'detail';

type AppModalProps = Omit<DrawerProps, 'size' | 'styles' | 'title' | 'position'> & {
  variant?: AppModalVariant;
  title?: ReactNode;
  subtitle?: ReactNode;
  eyebrow?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
};

const DESKTOP_WIDTH: Record<AppModalVariant, string> = {
  compact: '30rem',
  form: '42rem',
  detail: '58rem',
};

export const AppModal = ({
  variant = 'form',
  title,
  subtitle,
  eyebrow,
  footer,
  children,
  padding = 0,
  closeOnClickOutside = true,
  closeOnEscape = true,
  withCloseButton = true,
  ...props
}: AppModalProps) => {
  const isMobile = useMediaQuery('(max-width: 47.99em)', true, {
    getInitialValueInEffect: false,
  });

  return (
    <Drawer
      padding={padding}
      position="right"
      size={isMobile ? '100%' : DESKTOP_WIDTH[variant]}
      closeOnClickOutside={closeOnClickOutside}
      closeOnEscape={closeOnEscape}
      withCloseButton={withCloseButton}
      styles={{
        body: {
          padding: 0,
        },
        content: {
          background:
            'linear-gradient(180deg, rgba(18, 22, 28, 0.98), rgba(11, 14, 18, 0.99) 100%)',
          boxShadow: 'var(--app-shadow-soft)',
          overflow: 'hidden',
        },
        header: {
          display: 'none',
        },
      }}
      {...props}
    >
      <Stack gap={0} className="app-modal-shell">
        {title || subtitle || eyebrow ? (
          <Box className="app-modal-header">
            <Stack gap={8}>
              {eyebrow ? <Text className="app-kicker">{eyebrow}</Text> : null}
              {typeof title === 'string' ? (
                <Text className="app-section-title">{title}</Text>
              ) : (
                title
              )}
              {subtitle ? (
                <Text size="sm" className="app-muted-copy">
                  {subtitle}
                </Text>
              ) : null}
            </Stack>
          </Box>
        ) : null}

        <ScrollArea.Autosize mah={isMobile ? 'calc(100dvh - 11rem)' : '75dvh'}>
          <Box className="app-modal-body">{children}</Box>
        </ScrollArea.Autosize>

        {footer ? <Box className="app-modal-footer">{footer}</Box> : null}
      </Stack>
    </Drawer>
  );
};

type AppModalFooterProps = {
  primary?: ReactNode;
  secondary?: ReactNode;
  aside?: ReactNode;
};

export const AppModalFooter = ({ primary, secondary, aside }: AppModalFooterProps) => {
  if (!primary && !secondary && !aside) {
    return null;
  }

  return (
    <Group justify="space-between" align="center" wrap="wrap" gap="sm">
      <Box>{aside}</Box>
      <Group gap="xs" wrap="wrap">
        {secondary}
        {primary}
      </Group>
    </Group>
  );
};
