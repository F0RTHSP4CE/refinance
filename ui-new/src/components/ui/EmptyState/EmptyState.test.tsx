import { MantineProvider } from '@mantine/core';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EmptyState } from './EmptyState';

describe('EmptyState', () => {
  it('renders a default description when one is not provided', () => {
    render(
      <MantineProvider>
        <EmptyState title="Nothing here" />
      </MantineProvider>
    );

    expect(screen.getByText('Nothing here')).toBeInTheDocument();
    expect(screen.getByText('Nothing to show here yet.')).toBeInTheDocument();
  });
});
