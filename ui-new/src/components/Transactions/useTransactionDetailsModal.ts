import { useDisclosure } from '@mantine/hooks';
import { useState } from 'react';
import type { Transaction } from '@/types/api';

export const useTransactionDetailsModal = () => {
  const [opened, { open, close }] = useDisclosure(false);
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);

  const openTransaction = (transaction: Transaction) => {
    setSelectedTransaction(transaction);
    open();
  };

  const closeTransaction = () => {
    close();
    setSelectedTransaction(null);
  };

  return {
    opened,
    selectedTransaction,
    openTransaction,
    closeTransaction,
  };
};
