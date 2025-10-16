// Compact Dropdown Template Selector

import { useState } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuPortal,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from '@/i18n';
import { cn } from '@/lib/utils';
import { ChevronDown, Sparkles } from 'lucide-react';
import type { PromptTemplate } from '@/api/templates/types';

interface TemplateDropdownProps {
  templates: PromptTemplate[];
  categories: string[];
  onSelectTemplate: (template: PromptTemplate) => void;
  disabled?: boolean;
  className?: string;
}

export const TemplateDropdown = ({
  templates,
  categories,
  onSelectTemplate,
  disabled = false,
  className = '',
}: TemplateDropdownProps) => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

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

  const handleSelect = (template: PromptTemplate) => {
    onSelectTemplate(template);
    setOpen(false);
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" disabled={disabled} className={cn('gap-2', className)}>
          <Sparkles className="w-4 h-4" />
          {t('Templates')}
          <ChevronDown className="w-3 h-3" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent className="w-80 max-h-96 overflow-y-auto" align="start">
        <DropdownMenuLabel className="flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          {t('Prompt Templates')}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {categories.map(category => {
          const categoryTemplates = groupedTemplates[category] || [];

          if (categoryTemplates.length === 0) return null;

          return (
            <DropdownMenuSub key={category}>
              <DropdownMenuSubTrigger className="flex items-center justify-between">
                <span>{category}</span>
                <Badge variant="secondary" className="text-xs">
                  {categoryTemplates.length}
                </Badge>
              </DropdownMenuSubTrigger>

              <DropdownMenuPortal>
                <DropdownMenuSubContent className="w-72 max-h-80 overflow-y-auto">
                  {categoryTemplates.map(template => (
                    <DropdownMenuItem
                      key={template.name}
                      onClick={() => handleSelect(template)}
                      className="flex-col items-start p-3 cursor-pointer"
                    >
                      <div className="font-medium text-sm mb-1 line-clamp-1">{template.name}</div>
                      <div className="text-xs text-muted-foreground line-clamp-2">
                        {template.description}
                      </div>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuSubContent>
              </DropdownMenuPortal>
            </DropdownMenuSub>
          );
        })}

        {/* 全テンプレートが空の場合 */}
        {templates.length === 0 && (
          <DropdownMenuItem disabled className="text-center py-4">
            {t('No templates available')}
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
