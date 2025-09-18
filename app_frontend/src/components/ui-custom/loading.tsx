import loader from '@/assets/loader.svg';
import { useTranslation } from '@/i18n';

export const Loading = () => {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col flex-1 items-center justify-center h-full">
      <img src={loader} alt="processing" className="mr-2 w-4 h-4 animate-spin" />
      <span className="ml-2">{t('Loading...')}</span>
    </div>
  );
};
