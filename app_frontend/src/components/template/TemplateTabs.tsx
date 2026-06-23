// Tab-based Template Selector

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useTranslation } from "@/i18n";
import { cn } from "@/lib/utils";
import type { PromptTemplate } from "@/api/templates/types";

interface TemplateTabsProps {
  templates: PromptTemplate[];
  categories: string[];
  onSelectTemplate: (template: PromptTemplate) => void;
  className?: string;
}

const SimpleTemplateCard = ({
  template,
  onSelect,
}: {
  template: PromptTemplate;
  onSelect: (template: PromptTemplate) => void;
}) => (
  <div
    className="group cursor-pointer rounded-lg border border-transparent p-3 transition-colors hover:border-border hover:bg-accent/30"
    onClick={() => onSelect(template)}
  >
    <h4 className="mb-1 text-sm font-medium">{template.name}</h4>
    <p className="line-clamp-1 text-xs text-muted-foreground">
      {template.description}
    </p>
  </div>
);

export const TemplateTabs = ({
  templates,
  categories,
  onSelectTemplate,
  className = "",
}: TemplateTabsProps) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState(categories[0] || "all");

  // グループ化されたテンプレート
  const groupedTemplates = templates.reduce(
    (acc, template) => {
      if (!acc[template.category]) {
        acc[template.category] = [];
      }
      acc[template.category].push(template);
      return acc;
    },
    {} as Record<string, PromptTemplate[]>,
  );

  return (
    <div className={cn("w-full", className)}>
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        {/* タブリスト */}
        <TabsList className="mb-6 grid w-full grid-cols-5">
          {categories.map((category) => (
            <TabsTrigger
              key={category}
              value={category}
              className="relative text-xs"
            >
              {category}
              <Badge
                variant="default"
                className="ml-1 h-4 min-w-[1.2rem] text-xs"
              >
                {groupedTemplates[category]?.length || 0}
              </Badge>
            </TabsTrigger>
          ))}
        </TabsList>

        {/* タブコンテンツ */}
        {categories.map((category) => (
          <TabsContent key={category} value={category} className="mt-0">
            <div className="space-y-2">
              {groupedTemplates[category]?.map((template) => (
                <SimpleTemplateCard
                  key={template.name}
                  template={template}
                  onSelect={onSelectTemplate}
                />
              )) || (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  {t("No templates available in this category.")}
                </p>
              )}
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
};
