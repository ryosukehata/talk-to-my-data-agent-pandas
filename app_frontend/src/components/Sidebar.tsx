import { useState } from "react";
import { Loader2, Plus, Settings } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { useFetchAllChats, getChatsMenu } from "@/api/chat-messages";
import {
  useGeneratedDictionaries,
  getDictionariesMenu,
} from "@/api/dictionaries";
import { useFetchFeatureFlags } from "@/api/feature-flag";
import { useReports } from "@/api/reports";
import drLogoDark from "@/assets/DataRobot_black.svg";
import drLogoLight from "@/assets/DataRobot_white.svg";
import { AddDataModal } from "@/components/AddDataModal";
import { NewChatModal } from "@/components/NewChatModal";
import { SettingsModal } from "@/components/SettingsModal";
import {
  SidebarMenu,
  SidebarMenuOptionType,
} from "@/components/ui-custom/sidebar-menu";
import { Button } from "@/components/ui/button";
import {
  Sidebar as SidebarUI,
  SidebarProvider,
  SidebarHeader,
  SidebarContent,
  SidebarGroup,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { WelcomeModal } from "@/components/WelcomeModal";
import { useTranslation } from "@/i18n";
import {
  ROUTES,
  generateChatRoute,
  generateDataRoute,
  generateReportRoute,
} from "@/pages/routes";
import { useTheme } from "@/theme/theme-provider";

const DatasetList = ({ highlight }: { highlight: boolean }) => {
  const { data, isLoading } = useGeneratedDictionaries<SidebarMenuOptionType[]>(
    {
      select: getDictionariesMenu,
    },
  );
  const { t } = useTranslation();
  const params = useParams();
  const navigate = useNavigate();

  return (
    <div className="relative flex max-h-[160px] min-h-0 flex-none flex-col">
      <div className="flex items-center justify-between pb-3 pl-2">
        <div>
          <p className="mn-label-large">{t("Datasets")}</p>
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
            <Loader2 className="size-4 animate-spin" />
          </div>
        )}
        {!isLoading && !data?.length && (
          <p className="pl-2 text-muted-foreground">
            {t("Add your data here")}
          </p>
        )}
      </div>
    </div>
  );
};

const ChatList = ({ highlight }: { highlight: boolean }) => {
  const { data, isLoading } = useFetchAllChats<SidebarMenuOptionType[]>({
    select: getChatsMenu,
  });
  const navigate = useNavigate();
  const { chatId } = useParams();
  const { t } = useTranslation();

  return (
    <div
      className="relative flex min-h-0 flex-1 flex-col"
      data-testid="sidebar-chats-section"
    >
      <div className="flex items-center justify-between pb-3 pl-2">
        <div>
          <p className="mn-label-large">{t("Chats")}</p>
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
            <Loader2 className="size-4 animate-spin" />
          </div>
        )}
        {!isLoading && !data?.length && (
          <p className="pl-2 text-muted-foreground">
            {t("Start your first chat here")}
          </p>
        )}
      </div>
    </div>
  );
};

const ReportList = () => {
  const { data, isLoading } = useReports();
  const navigate = useNavigate();
  const { reportId } = useParams();
  const { t } = useTranslation();

  const reportMenuOptions: SidebarMenuOptionType[] =
    data?.reports?.map((report) => ({
      key: report.report_id,
      id: report.report_id,
      name: report.title,
    })) || [];

  return (
    <div
      className="relative flex max-h-[200px] min-h-[92px] flex-none flex-col"
      data-testid="sidebar-reports-section"
    >
      <div className="flex items-center justify-between pb-3 pl-2">
        <div>
          <p className="mn-label-large">{t("Reports")}</p>
        </div>
        <Button
          className="mr-2"
          variant="secondary"
          onClick={() =>
            navigate({
              pathname: ROUTES.REPORTS,
              search: "?new=1",
            })
          }
        >
          <Plus />
          {t("New Report")}
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <SidebarMenu
          options={reportMenuOptions}
          activeKey={reportId}
          onClick={({ id }) => navigate(generateReportRoute(id))}
        />
        {isLoading && (
          <div className="mt-4 flex justify-center">
            <Loader2 className="size-4 animate-spin" />
          </div>
        )}
        {!isLoading && !reportMenuOptions.length && (
          <p className="pl-2 text-sm text-muted-foreground">
            {t("No reports yet")}
          </p>
        )}
      </div>
    </div>
  );
};

export const Sidebar = () => {
  const { data: datasets, isLoading: isLoadingDatasets } =
    useGeneratedDictionaries();
  const { data: chats, isLoading: isLoadingChats } = useFetchAllChats();
  const { data: featureFlags } = useFetchFeatureFlags();
  const highlightDatasets = !isLoadingDatasets && !datasets?.length;
  const highlightChats =
    !highlightDatasets && !isLoadingChats && !chats?.length;
  const showReportBuilder = featureFlags?.reportBuilderEnabled === true;
  const navigate = useNavigate();
  const { theme } = useTheme();
  const drLogo = theme === "dark" ? drLogoLight : drLogoDark;
  const { t } = useTranslation();
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);

  return (
    <SidebarProvider defaultOpen={true}>
      <SidebarUI>
        <SidebarHeader>
          <img
            src={drLogo}
            alt="DataRobot"
            className="mb-4 w-[130px] cursor-pointer"
            onClick={() => navigate(ROUTES.DATA)}
          />
          <h1 className="mb-1 heading-04">{t("Talk to my data")}</h1>
          <p className="body-secondary">
            {t(
              "Add the data you want to analyze, then ask DataRobot questions to generate insights.",
            )}
          </p>
        </SidebarHeader>
        <SidebarContent className="overflow-hidden">
          <SidebarGroup className="h-full min-h-0">
            <DatasetList highlight={highlightDatasets} />
            <Separator className="my-6" />
            <ChatList highlight={highlightChats} />
            {showReportBuilder && (
              <>
                <Separator className="my-6" />
                <ReportList />
              </>
            )}
            <WelcomeModal />
          </SidebarGroup>
        </SidebarContent>
        <SidebarFooter>
          <SettingsModal
            isOpen={settingsModalOpen}
            onOpenChange={setSettingsModalOpen}
          />
          <div className="mt-4 flex justify-center">
            <Button
              variant="ghost"
              size="sm"
              className="flex w-full items-center justify-center gap-2"
              onClick={() => setSettingsModalOpen(true)}
            >
              <Settings />
              <span>{t("Settings")}</span>
            </Button>
          </div>
        </SidebarFooter>
      </SidebarUI>
    </SidebarProvider>
  );
};
