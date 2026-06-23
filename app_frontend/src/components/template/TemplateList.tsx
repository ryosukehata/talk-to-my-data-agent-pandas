// Minimal List Template Component

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/i18n";
import { useFetchFeatureFlags } from "@/api/feature-flag";
import { useDeleteCustomPrompt } from "@/api/custom-prompts/hooks";
import type { PromptTemplate } from "@/api/templates/types";
import { Edit, Send, Trash2 } from "lucide-react";
import { useState } from "react";

interface TemplateListItemProps {
  template: PromptTemplate;
  onSelect: (template: PromptTemplate) => void;
  onSendDirectly?: (message: string) => void;
  mode?: "select" | "send";
  className?: string;
}

export const TemplateListItem = ({
  template,
  onSelect,
  onSendDirectly,
  className = "",
}: TemplateListItemProps) => {
  const { t } = useTranslation();
  const { data: featureFlags } = useFetchFeatureFlags();
  const [isDeleting, setIsDeleting] = useState(false);
  const deleteCustomPrompt = useDeleteCustomPrompt();
  const templateEditEnabled = featureFlags?.templateEditEnabled ?? false; // Default to false while loading

  // カスタムプロンプトかどうかを判定
  const isCustomPrompt = template.category === "カスタム";

  // Debug logs (remove in production)
  console.log("Feature flags from API:", featureFlags);
  console.log("templateEditEnabled:", templateEditEnabled);

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect(template);
  };

  const handleSend = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onSendDirectly) {
      onSendDirectly(template.prompt_text_template);
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (
      !isCustomPrompt ||
      !confirm(t("Are you sure you want to delete this custom prompt?"))
    ) {
      return;
    }

    setIsDeleting(true);
    try {
      await deleteCustomPrompt.mutateAsync({ name: template.name });
    } catch (error) {
      console.error("Failed to delete custom prompt:", error);
      // エラーハンドリングは必要に応じて追加
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div
      className={cn(
        "group transition-colors hover:bg-accent/50",
        "border-b border-border last:border-b-0",
        "p-4",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-3">
            <h4 className="truncate text-sm font-medium">{template.name}</h4>
            <Badge type="outline" className="shrink-0 text-xs">
              {template.category}
            </Badge>
          </div>
          <p className="line-clamp-2 text-xs text-muted-foreground">
            {template.description}
          </p>
        </div>

        <div className="flex shrink-0 gap-2">
          {isCustomPrompt && (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleDelete}
              disabled={isDeleting}
              className="border-red-200 p-2 text-red-600 hover:border-red-300 hover:text-red-700"
              title={t("Delete")}
            >
              <Trash2 className="size-3" />
            </Button>
          )}
          {templateEditEnabled && (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleEdit}
              className="gap-1.5 text-xs"
            >
              <Edit className="size-3" />
              {t("Edit")}
            </Button>
          )}
          {onSendDirectly && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleSend}
              className="gap-1.5 text-xs"
            >
              <Send className="size-3" />
              {t("Send")}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

interface TemplateListProps {
  templates: PromptTemplate[];
  onSelectTemplate: (template: PromptTemplate) => void;
  onSendDirectly?: (message: string) => void;
  mode?: "select" | "send";
  className?: string;
}

export const TemplateList = ({
  templates,
  onSelectTemplate,
  onSendDirectly,
  className = "",
}: TemplateListProps) => {
  return (
    <div
      className={cn(
        "max-h-[60vh] overflow-y-auto rounded-lg border border-border bg-card",
        className,
      )}
    >
      {templates.map((template) => (
        <TemplateListItem
          key={template.name}
          template={template}
          onSelect={onSelectTemplate}
          onSendDirectly={onSendDirectly}
        />
      ))}
    </div>
  );
};
