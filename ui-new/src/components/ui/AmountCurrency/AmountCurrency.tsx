import { Text } from '@mantine/core';

type AmountItem = { amount: string; currency: string };

type AmountCurrencyProps = {
  amount: string;
  currency: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
};

type AmountsCurrencyProps = {
  amounts: AmountItem[];
  size?: 'xs' | 'sm' | 'md' | 'lg';
};

export const AmountCurrency = ({ amount, currency, size = 'sm' }: AmountCurrencyProps) => (
  <Text size={size}>
    {amount} {currency.toUpperCase()}
  </Text>
);

export const AmountsCurrency = ({ amounts, size = 'sm' }: AmountsCurrencyProps) => (
  <Text size={size}>
    {amounts.map((a) => `${a.amount} ${a.currency.toUpperCase()}`).join(' or ')}
  </Text>
);
