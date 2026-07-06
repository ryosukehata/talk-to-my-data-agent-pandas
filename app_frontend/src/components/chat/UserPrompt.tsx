import { useMemo, useState, useRef, useEffect } from "react";
import { PromptInput } from "@/components/ui-custom/prompt-input";
import { Button } from "@/components/ui/button";
import { usePostMessage } from "@/api/chat-messages/hooks";
import { useAppState } from "@/state";
import { useTranslation } from "@/i18n";
import { DATA_SOURCES } from "@/constants/dataSources";
import { TemplateButton } from "@/components/template";
import { RefinerButton } from "@/components/refiner";
import type { IChat } from "@/api/chat-messages/types";
import type { PromptTemplate } from "@/api/templates/types";

export const UserPrompt = ({
  chatId,
  allowedDataSources,
  hasInProgressMessages,
  testId,
  activeChat,
}: {
  chatId?: string;
  allowedDataSources?: string[];
  hasInProgressMessages: boolean;
  testId?: string;
  activeChat?: IChat;
}) => {
  const { t } = useTranslation();

  const {
    enableChartGeneration,
    enableBusinessInsights,
    dataSource: globalDataSource,
  } = useAppState();
  const { mutate: postMessage } = usePostMessage();
  const [selectedTemplateText, setSelectedTemplateText] = useState<string>("");
  const promptInputRef = useRef<HTMLTextAreaElement>(null);

  const isDataUploadRequired = !allowedDataSources?.[0];
  const chatDataSource = useMemo(() => {
    const dataSource = activeChat?.data_source || globalDataSource;
    // User can only select from the allowed data sources
    return allowedDataSources?.includes(dataSource)
      ? dataSource
      : allowedDataSources?.[0] || DATA_SOURCES.FILE;
  }, [activeChat?.data_source, globalDataSource, allowedDataSources]);

  const handleTemplateSelect = (template: PromptTemplate) => {
    setSelectedTemplateText(template.prompt_text_template);
    // Focus the input after template selection
    setTimeout(() => {
      promptInputRef.current?.focus();
    }, 100);
  };

  const handleSend = (message: string) => {
    postMessage({
      message,
      chatId,
      enableChartGeneration,
      enableBusinessInsights,
      dataSource: chatDataSource,
    });
    // Clear template text after sending
    setSelectedTemplateText("");
  };

  const handleClearTemplate = () => {
    setSelectedTemplateText("");
    promptInputRef.current?.focus();
  };

  const handleRefineComplete = (refinedMessage: string) => {
    setSelectedTemplateText(refinedMessage);
    // Focus the input after refining
    setTimeout(() => {
      promptInputRef.current?.focus();
    }, 100);
  };

  const handleAutoSend = (message: string) => {
    handleSend(message);
    // Clear the input field after auto-send
    if (promptInputRef.current) {
      promptInputRef.current.value = "";
    }
  };

  // Update the input value when template is selected
  useEffect(() => {
    if (selectedTemplateText && promptInputRef.current) {
      // Set the value and trigger change event for proper state sync
      const event = new Event("input", { bubbles: true });
      promptInputRef.current.value = selectedTemplateText;
      promptInputRef.current.dispatchEvent(event);
    }
  }, [selectedTemplateText]);

  return (
    <div className="w-full max-w-3xl">
      {/* Template selection area */}
      <div className="mb-4 flex w-full items-center justify-between">
        <div className="flex gap-2">
          <TemplateButton
            onSelectTemplate={handleTemplateSelect}
            onSendDirectly={handleSend}
            mode="send"
            variant="secondary"
            size="sm"
            disabled={isDataUploadRequired || hasInProgressMessages}
            testId="user-prompt-template-button"
          />
          <RefinerButton
            inputRef={promptInputRef}
            dataSource={chatDataSource}
            onRefineComplete={handleRefineComplete}
            onAutoSend={handleAutoSend}
            disabled={isDataUploadRequired || hasInProgressMessages}
            testId="user-prompt-refiner-button"
          />
        </div>
        {selectedTemplateText && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearTemplate}
            className="text-xs text-muted-foreground"
          >
            {t("Clear Template")}
          </Button>
        )}
      </div>

      {/* Prompt input */}
      <PromptInput
        ref={promptInputRef}
        chatId={chatId}
        sendButtonArrangement="append"
        onSend={handleSend}
        initialValue={selectedTemplateText}
        isProcessing={hasInProgressMessages}
        placeholder={
          isDataUploadRequired
            ? t(
                "Please upload and process data using the sidebar before starting the chat",
              )
            : t("Ask another question about your datasets.")
        }
        isDisabled={isDataUploadRequired}
        testId={testId}
      />
    </div>
  );
};
