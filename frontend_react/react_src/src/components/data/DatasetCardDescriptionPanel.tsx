import React from "react";
import { DictionaryTable as DT } from "@/api-state/dictionaries/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  useDeleteGeneratedDictionary,
  useUpdateDictionaryCell,
  useDownloadDictionary,
} from "@/api-state/dictionaries/hooks";
import { useDatasetMetadata } from "@/api-state/cleansed-datasets/hooks";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCheck } from "@fortawesome/free-solid-svg-icons/faCheck";
import { faDownload } from "@fortawesome/free-solid-svg-icons/faDownload";
import { faTrash } from "@fortawesome/free-solid-svg-icons/faTrash";
import loader from "@/assets/loader.svg";
import { DictionaryTable } from "./DictionaryTable";
import { CleansedDataTable } from "./CleansedDataTable";
import { ValueOf } from "@/state/types";
import { DATA_TABS } from "@/state/constants";
import { cn } from "@/lib/utils";
import { useTranslation } from "react-i18next";

interface DatasetCardDescriptionPanelProps {
  dictionary: DT;
  isProcessing?: boolean;
  viewMode: ValueOf<typeof DATA_TABS>;
}

export const DatasetCardDescriptionPanel: React.FC<
  DatasetCardDescriptionPanelProps
> = ({ dictionary, isProcessing = true, viewMode = "description" }) => {
  const { mutate: deleteDictionary } = useDeleteGeneratedDictionary();
  const { mutate: updateCell } = useUpdateDictionaryCell();
  const { mutate: downloadDictionary, isPending: isDownloading } = useDownloadDictionary();
  const { data: metadata, isLoading: isLoadingMetadata } = useDatasetMetadata(dictionary.name);
  const { t } = useTranslation();

  // Format file size from bytes to KB/MB/GB as appropriate
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";

    const k = 1024;
    const sizes = [t("file_size_bytes", "Bytes"), t("file_size_kb", "KB"), t("file_size_mb", "MB"), t("file_size_gb", "GB"), t("file_size_tb", "TB")];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const size = metadata?.file_size ? formatFileSize(metadata.file_size) : "0 MB"

  return (
    <div
      className={cn("flex flex-col w-full bg-card p-4", {
        "h-[400px]": isProcessing,
      })}
    >
      <div>
        <h3 className="text-lg">
          <strong>{dictionary.name}</strong>
        </h3>
        <div className="flex justify-between pt-1">
          <div className="flex gap-2 my-1">
            <Badge variant="secondary" className="leading-tight text-sm">
              {isLoadingMetadata ? (
                t("loading")
              ) : (
                `${metadata?.columns?.length || 0} ${t("features")}`
              )}
            </Badge>
            <Badge variant="secondary" className="leading-tight text-sm">
              {isLoadingMetadata ? (
                t("loading")
              ) : (
                `${metadata?.row_count?.toLocaleString() || 0} ${t("rows")}`
              )}
            </Badge>
            <Badge variant="secondary" className="leading-tight text-sm">
              {isLoadingMetadata ? t("loading") : size}
            </Badge>
            <Badge variant="secondary" className="leading-tight text-sm">
              {metadata?.data_source || t("file")}
            </Badge>
            {isProcessing ? (
              <Badge variant="outline" className="leading-tight text-sm">
                <img
                  src={loader}
                  alt={t("processing")}
                  className="mr-2 w-4 h-4 animate-spin"
                />
                {t("processing")}
              </Badge>
            ) : (
              <Badge variant="success" className="leading-tight text-sm">
                <FontAwesomeIcon className="mr-2 w-4 h-4 " icon={faCheck} />
                {t("processed")}
              </Badge>
            )}
          </div>
          <div className="flex gap-2 px-2">
            <Button
              variant="link"
              onClick={() => {
                downloadDictionary({ name: dictionary.name });
              }}
              title={t("download_dictionary_csv")}
              disabled={isProcessing || isDownloading}
            >
              {isDownloading ? (
                <img src={loader} alt={t("loading")} className="w-4 h-4 animate-spin" />
              ) : (
                <FontAwesomeIcon icon={faDownload} />
              )}
            </Button>
            <Button
              variant="link"
              onClick={() => {
                deleteDictionary({ name: dictionary.name });
              }}
              title={t("delete_dictionary")}
            >
              <FontAwesomeIcon icon={faTrash} />
            </Button>
          </div>
        </div>
      </div>
      <div className="flex flex-col flex-1 text-lg">
        {isProcessing ? (
          <div className="flex flex-col flex-1 items-center justify-center">
            {t("processing_dataset")}
          </div>
        ) : (
          <ScrollArea className="mt-4 h-96">
            {viewMode === DATA_TABS.DESCRIPTION ? (
              <DictionaryTable
                data={dictionary}
                onUpdateCell={(rowIndex, field, value) => {
                  updateCell(
                    {
                      name: dictionary.name,
                      rowIndex,
                      field,
                      value,
                    },
                    {
                      onError: () => {
                        // Error handling is managed by React Query's
                        // automatic cache restoration
                      },
                    }
                  );
                }}
              />
            ) : (
              <CleansedDataTable
                datasetName={dictionary.name}
                rowsPerPage={50}
              />
            )}
          </ScrollArea>
        )}
      </div>
    </div>
  );
};
