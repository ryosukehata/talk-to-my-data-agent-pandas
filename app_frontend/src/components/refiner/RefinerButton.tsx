/**
 * RefinerButton Component
 *
 * ユーザーの質問をAIで洗練するためのボタンコンポーネント
 */

import React from "react";
import { Button } from "@/components/ui/button";
import { Sparkles, Loader2 } from "lucide-react";
import { useRefineQuestions } from "@/api/refiner";
import { useFetchFeatureFlags } from "@/api/feature-flag";
import { useTranslation } from "@/i18n";
import { RefinedQuestion } from "@/api/refiner/types";

interface RefinerButtonProps {
  /** 現在の入力テキストを取得するためのref */
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  /** データソース（file, database など） */
  dataSource: string;
  /** 洗練された質問を受け取るコールバック */
  onRefineComplete: (refinedMessage: string) => void;
  /** 洗練後に自動送信するコールバック（autoSend時のみ使用） */
  onAutoSend?: (message: string) => void;
  /** ボタンを無効化するかどうか */
  disabled?: boolean;
  /** テスト用ID */
  testId?: string;
}

/**
 * 洗練された質問をフォーマットされたメッセージに変換
 */
const createFormatRefinedMessage =
  (t: (key: string) => string) =>
  (question: RefinedQuestion): string => {
    const parts = [
      `${t("Question")}: ${question.refined_question}`,
      "",
      `${t("Reasoning")}: ${question.reasoning}`,
    ];

    if (question.relevant_columns && question.relevant_columns.length > 0) {
      parts.push("");
      parts.push(
        `${t("Relevant Columns")}: ${question.relevant_columns.join(", ")}`,
      );
    }

    return parts.join("\n");
  };

export const RefinerButton: React.FC<RefinerButtonProps> = ({
  inputRef,
  dataSource,
  onRefineComplete,
  onAutoSend,
  disabled = false,
  testId,
}) => {
  const { t } = useTranslation();
  const { data: featureFlags } = useFetchFeatureFlags();

  const formatRefinedMessage = createFormatRefinedMessage(t);

  const { mutate: refineQuestions, isPending } = useRefineQuestions({
    onSuccess: (data) => {
      if (data.success && data.refined_questions.length > 0) {
        const formattedMessage = formatRefinedMessage(
          data.refined_questions[0],
        );

        // autoSendが有効な場合は直接送信、そうでなければ入力欄に表示
        if (featureFlags?.refinerAutoSend && onAutoSend) {
          onAutoSend(formattedMessage);
        } else {
          onRefineComplete(formattedMessage);
        }
      }
    },
    onError: (error) => {
      console.error("Failed to refine question:", error);
    },
  });

  // Feature flagが無効な場合は表示しない
  if (!featureFlags?.refinerEnabled) {
    return null;
  }

  const getCurrentInput = (): string => {
    return inputRef.current?.value?.trim() || "";
  };

  const handleClick = () => {
    const currentInput = getCurrentInput();
    if (!currentInput) {
      return;
    }

    refineQuestions({
      user_direction: currentInput,
      data_source: dataSource,
    });
  };

  const isDisabled = disabled || isPending;

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={handleClick}
      disabled={isDisabled}
      data-testid={testId}
      className="gap-2"
    >
      {isPending ? (
        <>
          <Loader2 className="size-4 animate-spin" />
          {t("Refining...")}
        </>
      ) : (
        <>
          <Sparkles className="size-4" />
          {t("Refine Question")}
        </>
      )}
    </Button>
  );
};
