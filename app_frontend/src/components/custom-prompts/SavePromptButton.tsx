import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Bookmark } from "lucide-react";
import { useTranslation } from "@/i18n";
import { SavePromptModal } from "./SavePromptModal";
import { SavePromptButtonProps, SavePromptData } from "./types";
import { useCustomPromptState } from "./hooks";
import { useFetchFeatureFlags } from "@/api/feature-flag";

export const SavePromptButton: React.FC<SavePromptButtonProps> = ({
  promptText,
  onSave,
  disabled = false,
}) => {
  const { t } = useTranslation();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { setSaving } = useCustomPromptState();
  const { data: featureFlags } = useFetchFeatureFlags();

  // カスタムプロンプト機能が無効の場合は何も表示しない
  if (!featureFlags?.customPromptsEnabled) {
    return null;
  }

  const handleSave = async (data: SavePromptData) => {
    setSaving(true);
    try {
      if (onSave) {
        await onSave(data);
      }
      setIsModalOpen(false);

      // 保存成功後、しばらく待ってから状態をリセット
      setTimeout(() => {
        setSaving(false);
      }, 3000); // 3秒後にリセット
    } catch (error) {
      console.error("Failed to save prompt:", error);
      setSaving(false);
      // エラーハンドリングは親コンポーネントで行う
    }
  };

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsModalOpen(true)}
        title={t("Save as custom prompt")}
        disabled={disabled || !promptText.trim()}
      >
        <Bookmark />
      </Button>

      <SavePromptModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSave}
        initialPromptText={promptText}
      />
    </>
  );
};
