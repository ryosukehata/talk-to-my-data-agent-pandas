import { useMemo, useState, useRef, useEffect } from 'react';
import { PromptInput } from '@/components/ui-custom/prompt-input';
import chatMidnight from '@/assets/chat-midnight.svg';
import { usePostMessage } from '@/api/chat-messages/hooks';
import { useTranslation } from '@/i18n';
import { useAppState } from '@/state/hooks';
import { DATA_SOURCES } from '@/constants/dataSources';
import { TemplateButton } from '@/components/template';
import type { IChat } from '@/api/chat-messages/types';
import type { PromptTemplate } from '@/api/templates/types';

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
  const {
    enableChartGeneration,
    enableBusinessInsights,
    dataSource: globalDataSource,
  } = useAppState();
  const { mutate: sendMessage } = usePostMessage();
  const [selectedTemplateText, setSelectedTemplateText] = useState<string>('');
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
    setSelectedTemplateText('');
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
    <div className="flex-1 flex flex-col p-4" data-testid={testId}>
      <div className="flex flex-col flex-1 items-center justify-center">
        <div className="w-[400px] flex flex-col flex-1 items-center justify-center">
          <img src={chatMidnight} alt="" />
          <h4 className="mb-2 mt-4">
            <strong className=" text-center font-semibold">
              {t('Type a question about your dataset')}
            </strong>
          </h4>
          <p className="text-center mb-6">
            {t(
              "Ask specific questions about your datasets to get insights, generate visualizations, and discover patterns. Include column names and the kind of analysis you're looking for to get more accurate results."
            )}
          </p>

          {/* Template selection area */}
          <div className="w-full flex justify-center items-center mb-4">
            <TemplateButton
              onSelectTemplate={handleTemplateSelect}
              onSendDirectly={handleSend}
              mode="send"
              variant="outline"
              size="sm"
              disabled={isDisabled}
              testId="initial-template-button"
            />
          </div>

          <PromptInput
            key={selectedTemplateText ? 'with-template' : 'empty'}
            ref={promptInputRef}
            sendButtonArrangement="append"
            onSend={handleSend}
            initialValue={selectedTemplateText}
            isDisabled={isDisabled}
            testId="initial-prompt-input"
            placeholder={t('Ask another question about your datasets.')}
          />
        </div>
      </div>
    </div>
  );
};
