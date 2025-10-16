// Tab-based Template Selector

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from '@/i18n';
import { cn } from '@/lib/utils';
import type { PromptTemplate } from '@/api/templates/types';

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
    className="group cursor-pointer hover:bg-accent/30 transition-colors p-3 rounded-lg border border-transparent hover:border-border"
    onClick={() => onSelect(template)}
  >
    <h4 className="font-medium text-sm mb-1">{template.name}</h4>
    <p className="text-xs text-muted-foreground line-clamp-1">{template.description}</p>
  </div>
);

export const TemplateTabs = ({
  templates,
  categories,
  onSelectTemplate,
  className = '',
}: TemplateTabsProps) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState(categories[0] || 'all');

  // グループ化されたテンプレート
  const groupedTemplates = templates.reduce(
    (acc, template) => {
      if (!acc[template.category]) {
        acc[template.category] = [];
      }
      acc[template.category].push(template);
      return acc;
    },
    {} as Record<string, PromptTemplate[]>
  );

  return (
    <div className={cn('w-full', className)}>
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        {/* タブリスト */}
        <TabsList className="grid w-full grid-cols-5 mb-6">
          {categories.map(category => (
            <TabsTrigger key={category} value={category} className="text-xs relative">
              {category}
              <Badge variant="secondary" className="ml-1 text-xs min-w-[1.2rem] h-4">
                {groupedTemplates[category]?.length || 0}
              </Badge>
            </TabsTrigger>
          ))}
        </TabsList>

        {/* タブコンテンツ */}
        {categories.map(category => (
          <TabsContent key={category} value={category} className="mt-0">
            <div className="space-y-2">
              {groupedTemplates[category]?.map(template => (
                <SimpleTemplateCard
                  key={template.name}
                  template={template}
                  onSelect={onSelectTemplate}
                />
              )) || (
                <p className="text-sm text-muted-foreground text-center py-8">
                  {t('No templates available in this category.')}
                </p>
              )}
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
};
