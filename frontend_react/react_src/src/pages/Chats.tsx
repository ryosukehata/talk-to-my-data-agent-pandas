import React, { Suspense, lazy, useMemo, useRef, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@radix-ui/react-separator";
import { Button } from "@/components/ui/button";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTrash } from "@fortawesome/free-solid-svg-icons/faTrash";
import {
  useFetchAllMessages,
  useDeleteChat,
  useFetchAllChats,
} from "@/api-state/chat-messages/hooks";
import { InitialPrompt, UserMessage, UserPrompt } from "@/components/chat";
import { ROUTES } from "./routes";
import { Loading } from "@/components/ui-custom/loading";
import { RenameChatModal } from "@/components/RenameChatModal";
import { DataSourceToggle } from "@/components/DataSourceToggle";
import { IChatMessage } from "@/api-state/chat-messages/types";
import { useGeneratedDictionaries } from "@/api-state/dictionaries/hooks";
import { useMultipleDatasetMetadata } from "@/api-state/cleansed-datasets/hooks";
import { DATA_SOURCES } from "@/constants/dataSources";
import { useTranslation } from "react-i18next";

// Lazy load ResponseMessage for better performance
const ResponseMessage = lazy(() =>
  import("../components/chat/ResponseMessage").then((module) => ({
    default: module.ResponseMessage,
  }))
);

const ComponentLoading = () => (
  <div className="p-4 text-sm">Loading component...</div>
);

const ChatMessageItem = ({
  message,
  messages,
  chatId,
  index,
}: {
  message: IChatMessage;
  messages: IChatMessage[];
  chatId?: string;
  index: number;
}) => {
  const responseId = messages[index + 1]?.id;

  return (
    <div className="table table-fixed w-full">
      {message.role === "user" ? (
        <>
          <UserMessage
            id={message.id}
            responseId={responseId}
            message={message.content}
            timestamp={message.created_at}
            chatId={chatId}
          />
          {message.in_progress && (
            <Suspense fallback={<ComponentLoading />}>
              <ResponseMessage
                message={message}
                isLoading={true}
                chatId={chatId}
              />
            </Suspense>
          )}
        </>
      ) : (
        <Suspense fallback={<ComponentLoading />}>
          <ResponseMessage
            message={message}
            isLoading={false}
            chatId={chatId}
          />
        </Suspense>
      )}
    </div>
  );
};

export const Chats: React.FC = () => {
  const { chatId } = useParams<{ chatId?: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();

  // API data hooks
  const { data: messages = [], status: messagesStatus } = useFetchAllMessages({
    chatId,
  });
  const { data: chats } = useFetchAllChats();
  const { mutate: deleteChat } = useDeleteChat();
  const allowSend = !messages?.some((message) => message.in_progress);
  const { data: dictionaries } = useGeneratedDictionaries();
  const { data: multipleMetadata } = useMultipleDatasetMetadata(
    dictionaries?.map((d) => d.name) || []
  );

  const { hasMixedSources, allowedDataSources } = useMemo(() => {
    if (!multipleMetadata)
      return { allowedDataSources: [], hasMixedSources: false };

    const dataSourcesSet = new Set<string>();

    multipleMetadata.forEach(({ metadata }) => {
      const { data_source } = metadata;

      if (
        data_source === DATA_SOURCES.FILE ||
        data_source === DATA_SOURCES.CATALOG
      ) {
        dataSourcesSet.add(DATA_SOURCES.FILE);
      } else if (data_source === DATA_SOURCES.DATABASE) {
        dataSourcesSet.add(DATA_SOURCES.DATABASE);
      }
    });

    return {
      // Users can only select data sources that are present in the metadata
      allowedDataSources: Array.from(dataSourcesSet),
      hasMixedSources:
        dataSourcesSet.has(DATA_SOURCES.FILE) &&
        dataSourcesSet.has(DATA_SOURCES.DATABASE),
    };
  }, [multipleMetadata]);

  // Find the active chat based on chatId param
  const activeChat = chats
    ? chats.find((chat) => chat.id === chatId)
    : undefined;

  // Handler for deleting the current chat
  const handleDeleteChat = () => {
    if (activeChat?.id) {
      // Find another chat to navigate to after deletion
      const otherChats =
        chats?.filter((chat) => chat.id !== activeChat.id) || [];

      deleteChat({ chatId: activeChat.id });

      // If there are other chats, navigate to the most recently created one
      // Otherwise, go to the main chats page
      if (otherChats.length > 0) {
        // Sort by creation date descending (newest first) to get the most recent chat
        const sortedChats = [...otherChats].sort((a, b) => {
          const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
          const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
          return dateB - dateA; // Descending order (newest first)
        });

        // Navigate to the most recent chat
        navigate(`/chats/${sortedChats[0].id}`);
      } else {
        // If no other chats, go to the main chats page
        navigate(ROUTES.CHATS);
      }
    }
  };

  // scroll area viewport ref
  // const scrollAreaViewportRef = useRef<HTMLDivElement>(null);
  const lastAIMessageRef = useRef<HTMLDivElement>(null);

  // Scroll the last AI message to the top of the scroll area (aligns the top of the message with the top of the viewport)
  useEffect(() => {
    // Use the actual Radix scroll area viewport for scrolling
    const viewport = document.querySelector('[data-slot="scroll-area-viewport"]');
    if (lastAIMessageRef.current && viewport) {
      // Delay scroll to ensure charts/images inside the AI message are rendered before scrolling
      setTimeout(() => {
        if (lastAIMessageRef.current && viewport) {
          // This ensures the top of the last AI message is exactly at the top of the scroll area
          viewport.scrollTop = lastAIMessageRef.current.offsetTop;
        }
      }, 100);
    }
  }, [messages]);

  // Render chat messages
  const renderMessages = () => {
    if (!messages || messages.length === 0) {
      return (
        <Suspense fallback={<ComponentLoading />}>
          <InitialPrompt
            allowedDataSources={allowedDataSources}
            chatId={activeChat?.id}
          />
        </Suspense>
      );
    }

    // find the index of the last AI reply
    const lastAIIndex = (() => {
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === "assistant") return i;
      }
      return -1;
    })();

    return (
      <>
        <ScrollArea className="flex flex-1 flex-col overflow-y-hidden pr-2 pb-4">
          <Separator className="my-4 border-t" />
          {messages.map((message, index, array) => {
            // render user message
            if (message.role === "user") {
              return (
                <ChatMessageItem
                  key={index}
                  message={message}
                  messages={array}
                  chatId={activeChat?.id}
                  index={index}
                />
              );
            }
            // render AI reply, add ref to the last one
            if (message.role === "assistant") {
              const isLastAI = index === lastAIIndex;
              return (
                <div key={index} ref={isLastAI ? lastAIMessageRef : undefined}>
                  <Suspense fallback={<ComponentLoading />}>
                    <ResponseMessage
                      message={message}
                      isLoading={!!message.in_progress}
                      chatId={activeChat?.id}
                    />
                  </Suspense>
                </div>
              );
            }
            return null;
          })}
        </ScrollArea>
        <Suspense fallback={<ComponentLoading />}>
          <UserPrompt
            allowedDataSources={allowedDataSources}
            chatId={activeChat?.id}
            allowSend={allowSend}
          />
        </Suspense>
      </>
    );
  };

  // Render the header with chat title and actions
  const renderChatHeader = () => {
    if (!activeChat) return null;

    return (
      <>
        <h2 className="text-xl flex-1">
          <strong>{activeChat.name || t("new_chat")}</strong>
          <RenameChatModal
            chatId={activeChat.id}
            currentName={activeChat.name}
          />
        </h2>
        <div>
          {hasMixedSources && (
            <DataSourceToggle multipleMetadata={multipleMetadata} />
          )}
        </div>
        <Button variant="ghost" onClick={handleDeleteChat}>
          <FontAwesomeIcon icon={faTrash} />
          <span className="ml-2">{t("delete_chat")}</span>
        </Button>
      </>
    );
  };

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex justify-between items-center gap-2 h-9">
        {renderChatHeader()}
      </div>
      <Separator className="my-4 border-t" />

      {messagesStatus === "pending" && !messages?.length ? (
        <div className="flex items-center justify-center h-[calc(100vh-200px)]">
          <Loading />
        </div>
      ) : (
        renderMessages()
      )}
    </div>
  );
};
