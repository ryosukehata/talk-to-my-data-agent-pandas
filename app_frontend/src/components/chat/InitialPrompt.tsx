import { useMemo, useState, useRef, useEffect } from "react";
import { PromptInput } from "@/components/ui-custom/prompt-input";
import chatMidnight from "@/assets/chat-midnight.svg";
import chatLight from "@/assets/chat-light.svg";
import { usePostMessage } from "@/api/chat-messages/hooks";
import { useTranslation } from "@/i18n";
import { useAppState } from "@/state/hooks";
import { DATA_SOURCES } from "@/constants/dataSources";
import { TemplateButton } from "@/components/template";
import { RefinerButton } from "@/components/refiner";
import type { IChat } from "@/api/chat-messages/types";
import type { PromptTemplate } from "@/api/templates/types";
import { useTheme } from "@/theme/theme-provider";

export const InitialPrompt = ({
  chatId,
  allowedDataSources,
  testId,
  activeChat,
}: {
  allowedDataSources?: string[];
  chatId?: string;
  testId?: string;
  activeChat?: IChat;
}) => {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const {
    enableChartGeneration,
    enableBusinessInsights,
    dataSource: globalDataSource,
  } = useAppState();
  const { mutate: sendMessage } = usePostMessage();
  const [selectedTemplateText, setSelectedTemplateText] = useState<string>("");
  const promptInputRef = useRef<HTMLTextAreaElement>(null);

  const isDisabled = !allowedDataSources?.[0];

  const chatDataSource = useMemo(() => {
    const dataSource = activeChat?.data_source || globalDataSource;
    // User can only select from the allowed data sources
    return allowedDataSources?.includes(dataSource)
      ? dataSource
      : allowedDataSources?.[0] || DATA_SOURCES.FILE;
  }, [activeChat?.data_source, globalDataSource, allowedDataSources]);

  const handleTemplateSelect = (template: PromptTemplate) => {
    setSelectedTemplateText(template.prompt_text_template);
  };

  const handleSend = (message: string) => {
    sendMessage({
      message,
      chatId,
      enableChartGeneration,
      enableBusinessInsights,
      dataSource: chatDataSource,
    });
    // Clear template text after sending
    setSelectedTemplateText("");
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

  // Focus the input when template is selected
  useEffect(() => {
    if (selectedTemplateText && promptInputRef.current) {
      // Focus the input when template is set
      setTimeout(() => {
        promptInputRef.current?.focus();
      }, 100);
    }
  }, [selectedTemplateText]);

  return (
    <div className="flex flex-1 flex-col p-4" data-testid={testId}>
      <div className="flex flex-1 flex-col items-center justify-center">
        <div className="flex w-[400px] flex-1 flex-col items-center justify-center">
          <img src={theme === "dark" ? chatMidnight : chatLight} alt="" />
          <h4 className="mt-4 mb-2">
            <strong className="text-center font-semibold">
              {t("Type a question about your dataset")}
            </strong>
          </h4>
          <p className="mb-10 text-center">
            {t(
              "Ask specific questions about your datasets to get insights, generate visualizations, and discover patterns. Include column names and the kind of analysis you're looking for to get more accurate results.",
            )}
          </p>

          {/* Template selection area */}
          <div className="mb-4 flex w-full items-center justify-center gap-2">
            <TemplateButton
              onSelectTemplate={handleTemplateSelect}
              onSendDirectly={handleSend}
              mode="send"
              variant="secondary"
              size="sm"
              disabled={isDisabled}
              testId="initial-template-button"
            />
            <RefinerButton
              inputRef={promptInputRef}
              dataSource={chatDataSource}
              onRefineComplete={handleRefineComplete}
              onAutoSend={handleAutoSend}
              disabled={isDisabled}
              testId="initial-refiner-button"
            />
          </div>

          <PromptInput
            key={selectedTemplateText ? "with-template" : "empty"}
            ref={promptInputRef}
            chatId={chatId}
            sendButtonArrangement="append"
            onSend={handleSend}
            initialValue={selectedTemplateText}
            isDisabled={isDisabled}
            testId="initial-prompt-input"
            placeholder={t("Ask another question about your datasets.")}
            autoFocus
          />
        </div>
      </div>
    </div>
  );
};
