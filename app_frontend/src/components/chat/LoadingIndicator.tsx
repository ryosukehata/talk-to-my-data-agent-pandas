import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCheck } from '@fortawesome/free-solid-svg-icons/faCheck';
import { faExclamationTriangle } from '@fortawesome/free-solid-svg-icons/faExclamationTriangle';
import loader from '@/assets/loader.svg';
import { useTranslation } from '@/i18n';

interface LoadingIndicatorProps {
  isLoading?: boolean;
  hasError?: boolean;
  successTestId?: string;
}

export const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({
  isLoading = true,
  hasError = false,
  successTestId = 'data-loading-success',
}) => {
  const { t } = useTranslation();

  if (hasError) {
    return (
      <FontAwesomeIcon
        className="mr-2 w-4 h-4 text-destructive"
        icon={faExclamationTriangle}
        title={t('Error occurred during processing')}
      />
    );
  }

  return isLoading ? (
    <img src={loader} alt={t('processing')} className="mr-2 w-4 h-4 animate-spin" />
  ) : (
    <FontAwesomeIcon
      className="mr-2 w-4 h-4 text-success"
      data-testid={successTestId}
      icon={faCheck}
    />
  );
};
