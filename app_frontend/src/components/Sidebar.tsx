import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { useNavigate, useParams } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import drLogo from '@/assets/DataRobot_white.svg';
import { SidebarMenu, SidebarMenuOptionType } from '@/components/ui-custom/sidebar-menu';
import { WelcomeModal } from './WelcomeModal';
import { AddDataModal } from './AddDataModal';
import { ROUTES, generateChatRoute, generateDataRoute } from '@/pages/routes';
import { Separator } from '@radix-ui/react-separator';
import { NewChatModal } from './NewChatModal';
import loader from '@/assets/loader.svg';
import { useGeneratedDictionaries, getDictionariesMenu } from '@/api/dictionaries';
import { useFetchAllChats, getChatsMenu } from '@/api/chat-messages';
import { Button } from '@/components/ui/button';
import { faCog } from '@fortawesome/free-solid-svg-icons/faCog';
import { SettingsModal } from '@/components/SettingsModal';

const DatasetList = ({ highlight }: { highlight: boolean }) => {
  const { data, isLoading } = useGeneratedDictionaries<SidebarMenuOptionType[]>({
    select: getDictionariesMenu,
  });
  const { t } = useTranslation();
  const params = useParams();
  const navigate = useNavigate();

  return (
    <div className="relative flex flex-col max-h-[300px]">
      <div className="flex justify-between items-center pb-3">
        <div>
          <p className="text-base font-semibold">{t('Datasets')}</p>
        </div>
        <AddDataModal highlight={highlight} />
      </div>
      <div className="flex-1 overflow-y-auto">
        <SidebarMenu
          options={data}
          activeKey={params.dataId}
          onClick={({ name }) => navigate(generateDataRoute(name))}
        />
        {isLoading && (
          <div className="mt-4 flex justify-center">
            <img src={loader} alt={t('Loading')} className="w-4 h-4 animate-spin" />
          </div>
        )}
        {!isLoading && !data?.length && (
          <p className="text-muted-foreground">{t('Add your data here')}</p>
        )}
      </div>
    </div>
  );
};

const ChatList = ({ highlight }: { highlight: boolean }) => {
  const { data, isLoading } = useFetchAllChats<SidebarMenuOptionType[]>({ select: getChatsMenu });
  const navigate = useNavigate();
  const { chatId } = useParams();
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const { t } = useTranslation();

  return (
    <div className="relative flex flex-col h-full min-h-[300px]">
      <div className="flex justify-between items-center pb-3">
        <div>
          <p className="text-base font-semibold">{t('Chats')}</p>
        </div>
        <NewChatModal highlight={highlight} />
      </div>
      <div className="flex-1 overflow-y-auto">
        <SidebarMenu
          options={data}
          activeKey={chatId}
          onClick={({ id }) => {
            navigate(generateChatRoute(id));
          }}
        />
        {isLoading && (
          <div className="mt-4 flex justify-center">
            <img src={loader} alt={t('Loading')} className="w-4 h-4 animate-spin" />
          </div>
        )}
        {!isLoading && !data?.length && (
          <p className="text-muted-foreground">{t('Start your first chart here')}</p>
        )}
      </div>
      <SettingsModal isOpen={settingsModalOpen} onOpenChange={setSettingsModalOpen} />
      <div className="mt-4 flex justify-center">
        <Button
          variant="ghost"
          size="sm"
          className="w-full flex items-center justify-center gap-2"
          onClick={() => setSettingsModalOpen(true)}
        >
          <FontAwesomeIcon icon={faCog} />
          <span>{t('Settings')}</span>
        </Button>
      </div>
    </div>
  );
};

export const Sidebar = () => {
  const { data: datasets, isLoading: isLoadingDatasets } = useGeneratedDictionaries();
  const { data: chats, isLoading: isLoadingChats } = useFetchAllChats();
  const highlightDatasets = !isLoadingDatasets && !datasets?.length;
  const highlightChats = !highlightDatasets && !isLoadingChats && !chats?.length;
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-6 p-6 pr-0 h-full overflow-y-auto">
      <div className="flex flex-col h-full">
        <div className="pr-6">
          <img
            src={drLogo}
            alt="DataRobot"
            className="w-[130px] cursor-pointer mb-4"
            onClick={() => navigate(ROUTES.DATA)}
          />
          <h1 className="text-xl font-bold text-primary-light">{t('Talk to my data')}</h1>
          <p className="text-sm text-muted-foreground">
            {t(
              'Add the data you want to analyze, then ask DataRobot questions to generate insights.'
            )}
          </p>
        </div>
        <Separator className="mt-6 mr-6 border-t" />
        <div className="flex flex-col pt-6 pr-6 gap-2 flex-1 min-h-0 overflow-y-auto">
          <DatasetList highlight={highlightDatasets} />
          <Separator className="my-6 border-t" />
          <ChatList highlight={highlightChats} />
          <WelcomeModal />
        </div>
      </div>
    </div>
  );
};
