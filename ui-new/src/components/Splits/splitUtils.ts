import { SPLIT_PARTICIPANT_COLORS, colorByStableIndex } from '@/constants/uiPalette';
import type { Split, SplitParticipant } from '@/types/api';

export const getSplitDisplayName = (split: Pick<Split, 'id' | 'comment'>) =>
  split.comment || `Split #${split.id}`;

export const getSplitParticipantColor = (entityId: number) =>
  colorByStableIndex(entityId, SPLIT_PARTICIPANT_COLORS);

export const getSplitParticipantShare = (participant: SplitParticipant, split: Split) =>
  participant.fixed_amount ?? split.share_preview.current_share;

export const formatSplitMoney = (value: number | string) => {
  const numeric = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return numeric.toFixed(2);
};

export const getDisplayedCollectedAmount = (split: Split) =>
  formatSplitMoney(
    split.participants.reduce(
      (sum, participant) => sum + Number(getSplitParticipantShare(participant, split)),
      0
    )
  );

export const splitHasFixedAmounts = (split: Split) =>
  split.participants.some((participant) => participant.fixed_amount);

export const getSplitStatsLabel = (split: Split) => {
  if (splitHasFixedAmounts(split)) {
    return `average ${formatSplitMoney(split.share_preview.average_share)} ${split.currency.toUpperCase()}`;
  }

  if (split.participants.length > 0) {
    return `${formatSplitMoney(split.share_preview.current_share)} ${split.currency.toUpperCase()} each`;
  }

  return '';
};
