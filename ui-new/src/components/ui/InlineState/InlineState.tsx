import type { ReactNode } from 'react';
import { EmptyState } from '../EmptyState';
import { ErrorState } from '../ErrorState';
import { LoadingState } from '../LoadingState';

type InlineStateProps =
  | {
      kind: 'loading';
      cards?: number;
      lines?: number;
    }
  | {
      kind: 'empty';
      title: string;
      description?: ReactNode;
      action?: ReactNode;
      compact?: boolean;
    }
  | {
      kind: 'error';
      title: string;
      description?: ReactNode;
      retryLabel?: string;
      onRetry?: () => void;
      compact?: boolean;
    };

export const InlineState = (props: InlineStateProps) => {
  if (props.kind === 'loading') {
    return <LoadingState cards={props.cards ?? 1} lines={props.lines ?? 4} />;
  }

  if (props.kind === 'error') {
    return (
      <ErrorState
        compact={props.compact ?? true}
        title={props.title}
        description={props.description}
        retryLabel={props.retryLabel}
        onRetry={props.onRetry}
      />
    );
  }

  return (
    <EmptyState
      compact={props.compact ?? true}
      title={props.title}
      description={props.description}
      action={props.action}
    />
  );
};
