import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTrash } from '@fortawesome/free-solid-svg-icons/faTrash';
import { useDeleteAllDatasets } from '@/api/datasets/hooks';
import { useTranslation } from '@/i18n';
import { ConfirmDialog } from '../ui-custom/confirm-dialog';

export const ClearDatasetsButton = () => {
  const { t } = useTranslation();

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const { mutate, isPending } = useDeleteAllDatasets({
    onSuccess: () => setIsDeleteDialogOpen(false),
  });

  const handleClick = () => {
    setIsDeleteDialogOpen(true);
  };

  return (
    <>
      <ConfirmDialog
        open={isDeleteDialogOpen}
        isLoading={isPending}
        onOpenChange={setIsDeleteDialogOpen}
        title={t('Clear all datasets')}
        confirmText={t('Clear')}
        cancelText={t('Cancel')}
        description={t('Are you sure you want to clear all datasets?')}
        onConfirm={mutate}
        variant="destructive"
      />
      <Button testId="clear-datasets-button" variant="ghost" onClick={handleClick}>
        <FontAwesomeIcon icon={faTrash} />
        {t('Clear all datasets')}
      </Button>
    </>
  );
};
