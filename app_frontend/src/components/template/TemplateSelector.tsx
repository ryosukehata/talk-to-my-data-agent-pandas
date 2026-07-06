// Template Selector Modal Component

import { useState, useMemo, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useTranslation } from "@/i18n";
import { cn } from "@/lib/utils";
import {
  useFetchTemplates,
  useFetchTemplateCategories,
} from "@/api/templates/hooks";
import { useFetchCustomPrompts } from "@/api/custom-prompts/hooks";
import { useFetchFeatureFlags } from "@/api/feature-flag";
import type { PromptTemplate } from "@/api/templates/types";
import { TemplateList } from "./TemplateList";
import { TemplateCategoryFilter } from "./TemplateCategoryFilter";
import { Loading } from "@/components/ui-custom/loading";
import { convertCustomPromptsToTemplates } from "./utils";
import { useCustomPromptState } from "@/components/custom-prompts";
import { LoaderCircle } from "lucide-react";

interface TemplateSelectorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectTemplate: (template: PromptTemplate) => void;
  onSendDirectly?: (message: string) => void;
  mode?: "select" | "send";
  className?: string;
}

export const TemplateSelector = ({
  open,
  onOpenChange,
  onSelectTemplate,
  onSendDirectly,
  mode = "select",
  className = "",
}: TemplateSelectorProps) => {
  const { t } = useTranslation();
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const { pendingUpdate } = useCustomPromptState();
  const { data: featureFlags } = useFetchFeatureFlags();

  // カスタムプロンプト機能が有効かどうか
  const customPromptsEnabled = featureFlags?.customPromptsEnabled ?? false;

  // Fetch regular templates based on selected category
  const {
    data: templatesResponse,
    isLoading: templatesLoading,
    error: templatesError,
  } = useFetchTemplates({
    category:
      selectedCategory === "all" || selectedCategory === "カスタム"
        ? undefined
        : selectedCategory,
  });

  // Fetch custom prompts when category is 'all' or 'カスタム' AND feature is enabled
  const shouldFetchCustomPrompts =
    customPromptsEnabled &&
    (selectedCategory === "all" || selectedCategory === "カスタム");
  const {
    data: customPromptsResponse,
    isLoading: customPromptsLoading,
    error: customPromptsError,
  } = useFetchCustomPrompts({ enabled: shouldFetchCustomPrompts });

  // Fetch available categories
  const { data: categoriesResponse, isLoading: categoriesLoading } =
    useFetchTemplateCategories();

  // Combine regular templates and custom prompts
  const combinedTemplates = useMemo(() => {
    const regularTemplates = templatesResponse?.templates || [];
    const customPrompts = customPromptsEnabled
      ? customPromptsResponse?.custom_prompts || []
      : [];

    if (selectedCategory === "カスタム") {
      // カスタムカテゴリのみ表示（フィーチャーフラグが有効な場合のみ）
      return customPromptsEnabled
        ? convertCustomPromptsToTemplates(customPrompts)
        : [];
    } else if (selectedCategory === "all") {
      // 全てのテンプレート + カスタムプロンプト（フィーチャーフラグが有効な場合）
      return [
        ...regularTemplates,
        ...(customPromptsEnabled
          ? convertCustomPromptsToTemplates(customPrompts)
          : []),
      ];
    } else {
      // 選択されたカテゴリのテンプレートのみ
      return regularTemplates;
    }
  }, [
    templatesResponse,
    customPromptsResponse,
    selectedCategory,
    customPromptsEnabled,
  ]);

  // Combine categories to include 'カスタム' only if feature is enabled
  const combinedCategories = useMemo(() => {
    const regularCategories = categoriesResponse?.categories || [];
    // カスタムプロンプト機能が有効な場合のみカスタムカテゴリを追加
    if (customPromptsEnabled && !regularCategories.includes("カスタム")) {
      return [...regularCategories, "カスタム"];
    }
    return regularCategories;
  }, [categoriesResponse, customPromptsEnabled]);

  // カスタムプロンプト機能が無効になった場合、カスタムカテゴリが選択されていたら'all'にリセット
  useEffect(() => {
    if (!customPromptsEnabled && selectedCategory === "カスタム") {
      setSelectedCategory("all");
    }
  }, [customPromptsEnabled, selectedCategory]);

  // Loading state - 通常のローディングとカスタムプロンプトローディングを組み合わせ
  const isLoading =
    templatesLoading || (shouldFetchCustomPrompts && customPromptsLoading);

  // Error state
  const hasError =
    templatesError || (shouldFetchCustomPrompts && customPromptsError);

  const handleSelectTemplate = (template: PromptTemplate) => {
    onSelectTemplate(template);
    onOpenChange(false);
  };

  const handleSendDirectly = (message: string) => {
    if (onSendDirectly) {
      onSendDirectly(message);
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn("flex max-h-[85vh] max-w-2xl flex-col", className)}
      >
        <DialogHeader className="shrink-0">
          <DialogTitle>
            {mode === "send"
              ? t("Quick Ask - Select a Template")
              : t("Select Prompt Template")}
          </DialogTitle>
        </DialogHeader>

        {/* Category Filter */}
        <div className="shrink-0 border-b py-4">
          {categoriesLoading ? (
            <div className="flex items-center gap-2">
              <div className="size-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <span className="text-sm text-muted-foreground">
                {t("Loading categories...")}
              </span>
            </div>
          ) : (
            <TemplateCategoryFilter
              categories={combinedCategories}
              selectedCategory={selectedCategory}
              onCategoryChange={setSelectedCategory}
            />
          )}
        </div>

        {/* Templates List - Scrollable Area */}
        <div className="min-h-0 flex-1 overflow-hidden">
          {customPromptsEnabled &&
            pendingUpdate &&
            (selectedCategory === "all" || selectedCategory === "カスタム") && (
              <Alert variant="info" className="mb-4 py-3">
                <LoaderCircle className="animate-spin" />
                <AlertDescription>
                  {t("Custom prompt update in progress, please wait...")}
                </AlertDescription>
              </Alert>
            )}

          {customPromptsEnabled &&
            customPromptsLoading &&
            shouldFetchCustomPrompts &&
            !pendingUpdate && (
              <Alert variant="info" className="mb-4 py-3">
                <LoaderCircle className="animate-spin" />
                <AlertDescription>
                  {t("Loading custom prompts...")}
                </AlertDescription>
              </Alert>
            )}

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loading />
            </div>
          ) : hasError ? (
            <div className="flex items-center justify-center py-8">
              <p className="text-sm text-destructive">
                {t("Failed to load templates. Please try again.")}
              </p>
            </div>
          ) : combinedTemplates.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <p className="text-sm text-muted-foreground">
                {selectedCategory === "all"
                  ? t("No templates available.")
                  : t("No templates found for this category.")}
              </p>
            </div>
          ) : (
            <ScrollArea className="h-full">
              <div className="pr-4">
                <TemplateList
                  templates={combinedTemplates}
                  onSelectTemplate={handleSelectTemplate}
                  onSendDirectly={handleSendDirectly}
                  mode={mode}
                  className="pb-4"
                />
              </div>
            </ScrollArea>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
