import { useAuthStore } from '@/stores/auth';
import { MoneyActionModal } from '@/components/MoneyActionModal/MoneyActionModal';

type RequestMoneyModalProps = {
  opened: boolean;
  onClose: () => void;
};

export const RequestMoneyModal = ({ opened, onClose }: RequestMoneyModalProps) => {
  const actorEntity = useAuthStore((s) => s.actorEntity);
  return (
    <MoneyActionModal
      opened={opened}
      mode="request"
      onClose={onClose}
      initialToEntityId={actorEntity?.id}
      title="Request money"
      description="Create a pending invoice from the right-side request flow and review it before it is issued."
    />
  );
};
