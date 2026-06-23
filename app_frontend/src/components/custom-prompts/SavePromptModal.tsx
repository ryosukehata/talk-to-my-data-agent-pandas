import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useTranslation } from "@/i18n";
import { SavePromptModalProps, SavePromptData } from "./types";
import { useCustomPromptState } from "./hooks";

export const SavePromptModal: React.FC<SavePromptModalProps> = ({
  isOpen,
  onClose,
  onSave,
  initialPromptText,
}) => {
  const { t } = useTranslation();
  const { isSaving } = useCustomPromptState();
  const [formData, setFormData] = useState<SavePromptData>({
    name: "",
    description: "",
    prompt_text_template: initialPromptText,
  });

  // モーダルが開かれたときに初期値をセット
  useEffect(() => {
    if (isOpen) {
      setFormData({
        name: "",
        description: "",
        prompt_text_template: initialPromptText,
      });
    }
  }, [isOpen, initialPromptText]);

  const handleInputChange = (field: keyof SavePromptData, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = () => {
    if (formData.name.trim()) {
      onSave({
        ...formData,
        name: formData.name.trim(),
        description: formData.description?.trim() || undefined,
      });
    }
  };

  const isValid = formData.name.trim().length > 0;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("Save Custom Prompt")}</DialogTitle>
          <DialogDescription>
            {t("Save this prompt as a custom template for future use.")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="prompt-name">{t("Prompt Name")} *</Label>
            <Input
              id="prompt-name"
              value={formData.name}
              onChange={(e) => handleInputChange("name", e.target.value)}
              placeholder={t("Enter prompt name")}
              disabled={isSaving}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="prompt-description">
              {t("Prompt Description")} ({t("Optional")})
            </Label>
            <Input
              id="prompt-description"
              value={formData.description}
              onChange={(e) => handleInputChange("description", e.target.value)}
              placeholder={t("Enter description")}
              disabled={isSaving}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="prompt-text">{t("Prompt Text")}</Label>
            <textarea
              id="prompt-text"
              value={formData.prompt_text_template}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                handleInputChange("prompt_text_template", e.target.value)
              }
              placeholder={t("Enter prompt text")}
              rows={4}
              disabled={isSaving}
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!isValid || isSaving}>
            {isSaving ? t("Saving...") : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
