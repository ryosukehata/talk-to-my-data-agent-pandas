import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useTranslation } from "@/i18n";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useAppState } from "@/state";
import { useDataRobotInfo, useUpdateApiToken } from "@/api/user/hooks";
import { Input } from "./ui/input";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { useReloadTemplates } from "@/api/templates/reloadHooks";
import { toast } from "sonner";
import { Checkbox } from "@/components/ui/checkbox";
import { useTheme } from "@/theme/theme-provider";
import { ExternalLink, RefreshCw } from "lucide-react";

interface SettingsModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onOpenChange,
}) => {
  const { t } = useTranslation();
  const {
    collapsiblePanelDefaultOpen,
    setCollapsiblePanelDefaultOpen,
    enableChartGeneration,
    setEnableChartGeneration,
    enableBusinessInsights,
    setEnableBusinessInsights,
    includeCsvBom,
    setIncludeCsvBom,
  } = useAppState();
  const { theme, setTheme } = useTheme();

  const {
    data: dataRobotInfo,
    isLoading: isLoadingDataRobotInfo,
    refetch: refetchDataRobotInfo,
  } = useDataRobotInfo();
  const updateApiTokenMutation = useUpdateApiToken();
  const reloadTemplatesMutation = useReloadTemplates();
  const [isRefreshingConnection, setIsRefreshingConnection] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [apiToken, setApiToken] = useState<string>("");
  const [tokenUpdateSuccess, setTokenUpdateSuccess] = useState(false);

  const [
    localCollapsiblePanelDefaultOpen,
    setLocalCollapsiblePanelDefaultOpen,
  ] = useState(collapsiblePanelDefaultOpen);
  const [localEnableChartGeneration, setLocalEnableChartGeneration] = useState(
    enableChartGeneration,
  );
  const [localEnableBusinessInsights, setLocalEnableBusinessInsights] =
    useState(enableBusinessInsights);
  const [localIncludeCsvBom, setLocalIncludeCsvBom] = useState(includeCsvBom);
  const accountInfo = dataRobotInfo?.datarobot_account_info;
  const connectedAs = accountInfo
    ? [accountInfo.firstName, accountInfo.lastName].filter(Boolean).join(" ") ||
      accountInfo.username ||
      ""
    : "";
  const appVersion = window.ENV?.APP_VERSION;

  const handleSaveSettings = () => {
    setCollapsiblePanelDefaultOpen(localCollapsiblePanelDefaultOpen);
    setEnableChartGeneration(localEnableChartGeneration);
    setEnableBusinessInsights(localEnableBusinessInsights);
    setIncludeCsvBom(localIncludeCsvBom);
    onOpenChange(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] flex-col overflow-hidden sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="text-center">{t("Settings")}</DialogTitle>
          <DialogDescription className="text-center">
            {t("Customize your chat experience")}
          </DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto pr-2">
          {/* スクロール可能なコンテンツエリア */}
          <div className="flex items-center justify-between gap-4 py-2">
            <Label
              htmlFor="collapsible-default-open"
              className="cursor-pointer"
            >
              {t("Expand data panels by default")}
            </Label>
            <Checkbox
              id="collapsible-default-open"
              checked={localCollapsiblePanelDefaultOpen}
              onCheckedChange={(value) =>
                setLocalCollapsiblePanelDefaultOpen(value === true)
              }
            />
          </div>

          <div className="flex items-center justify-between gap-4 py-2">
            <Label htmlFor="enable-chart-generation" className="cursor-pointer">
              {t("Enable chart generation")}
            </Label>
            <Switch
              id="enable-chart-generation"
              checked={localEnableChartGeneration}
              onCheckedChange={(e) => setLocalEnableChartGeneration(e)}
            />
          </div>
          <div className="flex items-center justify-between gap-4 py-2">
            <Label
              htmlFor="enable-business-insights"
              className="cursor-pointer"
            >
              {t("Enable business insights")}
            </Label>
            <Switch
              id="enable-business-insights"
              checked={localEnableBusinessInsights}
              onCheckedChange={(e) => setLocalEnableBusinessInsights(e)}
            />
          </div>

          <>
            <Separator className="my-2 border-t" />
            <div className="my-4 flex items-center justify-between space-y-4">
              <p className="mn-label">{t("Language")}</p>
              <LanguageSwitcher />
            </div>
            <div className="my-4 flex items-center justify-between space-y-4">
              <p className="mn-label">{t("Dark Theme")}</p>
              <Switch
                id="theme"
                checked={theme === "dark"}
                onCheckedChange={() =>
                  setTheme(theme === "dark" ? "light" : "dark")
                }
              />
            </div>
            <div
              className="flex items-center justify-between gap-4 py-2"
              title={t(
                "Include the byte order mark (BOM) in exported CSVs for better compatibility with international characters.",
              )}
            >
              <Label htmlFor="include-csv-bom" className="cursor-pointer">
                {t("Include BOM")}
              </Label>
              <Switch
                id="include-csv-bom"
                checked={localIncludeCsvBom}
                onCheckedChange={(e) => setLocalIncludeCsvBom(e)}
              />
            </div>
          </>

          <Separator className="my-2 border-t" />

          {/* Template Management Section */}
          <div className="mt-4 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">{t("Template Management")}</h3>
              <Button
                variant="secondary"
                size="sm"
                disabled={reloadTemplatesMutation.isPending}
                onClick={async () => {
                  try {
                    const result = await reloadTemplatesMutation.mutateAsync();
                    toast.success(
                      `${t("Templates reloaded successfully")} (${result.total_templates} ${t("templates")}, ${result.categories} ${t("categories")})`,
                    );
                  } catch (error) {
                    console.error("Failed to reload templates:", error);
                    toast.error(
                      error instanceof Error
                        ? error.message
                        : t("Failed to reload templates"),
                    );
                  }
                }}
              >
                {reloadTemplatesMutation.isPending
                  ? t("Reloading...")
                  : t("Reload Templates")}
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              {t(
                "Reload prompt templates from the data source to get the latest updates.",
              )}
            </p>
          </div>

          <Separator className="my-2 border-t" />

          <div className="mt-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h3 className="mn-label">{t("DataRobot Connection")}</h3>
                {isRefreshingConnection && (
                  <RefreshCw className="size-3 animate-spin" />
                )}
              </div>
              <Button
                data-testid="refresh-connection-button"
                variant="ghost"
                size="sm"
                disabled={isRefreshingConnection}
                onClick={async () => {
                  try {
                    setIsRefreshingConnection(true);
                    setRefreshError(null);
                    await refetchDataRobotInfo();
                  } catch (error) {
                    console.error("Failed to refresh connection:", error);
                    setRefreshError(
                      error instanceof Error
                        ? error.message
                        : t("Failed to connect to DataRobot"),
                    );
                  } finally {
                    setIsRefreshingConnection(false);
                  }
                }}
              >
                {isRefreshingConnection ? t("Refreshing...") : t("Refresh")}
              </Button>
            </div>
            {isLoadingDataRobotInfo || isRefreshingConnection ? (
              <p className="body">{t("Loading DataRobot info...")}</p>
            ) : accountInfo ? (
              <div data-testid="connection-info" className="space-y-1">
                {connectedAs && (
                  <p>
                    <span className="mr-1">{t("Connected as:")}</span>
                    <span data-testid="connected-as-value">{connectedAs}</span>
                  </p>
                )}
                <p>
                  {t("Email")}:{" "}
                  <span data-testid="email-value">{accountInfo.email}</span>
                </p>
                {dataRobotInfo.datarobot_api_token && (
                  <p>
                    <span className="mr-1">{t("API Token:")}</span>
                    <span
                      data-testid="api-key-value"
                      className="rounded py-0.5"
                    >
                      {dataRobotInfo.datarobot_api_token}
                    </span>
                  </p>
                )}
                {dataRobotInfo.datarobot_api_scoped_token && (
                  <p>
                    <span className="mr-1">{t("Scoped Token:")}</span>
                    <span
                      data-testid="own-api-key-value"
                      className="rounded py-0.5"
                    >
                      {dataRobotInfo.datarobot_api_scoped_token}
                    </span>
                  </p>
                )}
                <p>
                  <a
                    data-testid="manage-api-keys-link"
                    href={`/account/developer-tools`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {t("Manage API keys")}
                    <ExternalLink className="ml-1 inline size-3" />
                  </a>
                </p>
              </div>
            ) : refreshError ? (
              <div data-testid="connection-error" className="space-y-2">
                <p className="text-destructive">{t("Connection error")}</p>
                <p>{refreshError}</p>
                <p>{t("Check your DataRobot connection and try again")}</p>
              </div>
            ) : (
              <div data-testid="disconnected-state" className="space-y-2">
                <p>{t("Not connected to DataRobot")}</p>
                <p>
                  {t(
                    "Use the Refresh button to connect if DataRobot is available",
                  )}
                </p>
              </div>
            )}

            <div className="border-t pt-4">
              <h4 className="mb-4 font-medium">{t("Update API Token")}</h4>
              <div className="flex flex-col gap-2">
                <Input
                  type="password"
                  autoComplete="off"
                  value={apiToken}
                  onChange={(e) => {
                    setApiToken(e.target.value);
                    if (updateApiTokenMutation.isError) {
                      updateApiTokenMutation.reset();
                    }
                  }}
                  placeholder={t("Enter DataRobot API token")}
                  disabled={updateApiTokenMutation.isPending}
                />
                <div className="flex justify-end">
                  <Button
                    data-testid="update-api-key-button"
                    variant="ghost"
                    size="sm"
                    disabled={
                      updateApiTokenMutation.isPending || !apiToken.trim()
                    }
                    onClick={() => {
                      if (!apiToken.trim()) {
                        return;
                      }
                      setTokenUpdateSuccess(false);
                      updateApiTokenMutation.mutate(apiToken, {
                        onSuccess: () => {
                          setApiToken("");
                          setTokenUpdateSuccess(true);
                          setTimeout(() => setTokenUpdateSuccess(false), 3000);
                        },
                      });
                    }}
                  >
                    {updateApiTokenMutation.isPending
                      ? t("Updating...")
                      : t("Update Token")}
                  </Button>
                </div>

                {updateApiTokenMutation.isError && (
                  <p
                    data-testid="api-key-error"
                    className="mt-1 text-sm text-destructive"
                  >
                    {updateApiTokenMutation.error instanceof Error
                      ? updateApiTokenMutation.error.message
                      : t("Failed to update API token")}
                  </p>
                )}

                {tokenUpdateSuccess && (
                  <p className="mt-1 text-sm text-success">
                    {t("API token updated successfully!")}
                  </p>
                )}

                <p className="mt-1 body-secondary">
                  {t(
                    "Manually enter your DataRobot API token to authenticate with the service.",
                  )}
                </p>
              </div>
            </div>
          </div>
          {appVersion && (
            <>
              <Separator className="my-2 border-t" />
              <p className="text-xs text-muted-foreground">
                {t("Version")}: {appVersion}
              </p>
            </>
          )}
        </div>
        {/* スクロール可能エリア終了 */}
        <Separator className="mt-2 border-t" />
        <DialogFooter className="mt-4 flex-shrink-0">
          {/* フッター固定 */}
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            {t("Cancel")}
          </Button>
          <Button onClick={handleSaveSettings}>{t("Save changes")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
