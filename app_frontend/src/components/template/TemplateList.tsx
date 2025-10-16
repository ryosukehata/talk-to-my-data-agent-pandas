// Minimal List Template Component

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/i18n';
import { useFetchFeatureFlags } from '@/api/feature-flag';
import { useDeleteCustomPrompt } from '@/api/custom-prompts/hooks';
import type { PromptTemplate } from '@/api/templates/types';
import { Edit, Send, Trash2 } from 'lucide-react';
import { useState } from 'react';

interface TemplateListItemProps {
  template: PromptTemplate;
  onSelect: (template: PromptTemplate) => void;
  onSendDirectly?: (message: string) => void;
  mode?: 'select' | 'send';
  className?: string;
}

export const TemplateListItem = ({
  template,
  onSelect,
  onSendDirectly,
  className = '',
}: TemplateListItemProps) => {
  const { t } = useTranslation();
  const { data: featureFlags } = useFetchFeatureFlags();
  const [isDeleting, setIsDeleting] = useState(false);
  const deleteCustomPrompt = useDeleteCustomPrompt();
  const templateEditEnabled = featureFlags?.templateEditEnabled ?? false; // Default to false while loading

  // カスタムプロンプトかどうかを判定
  const isCustomPrompt = template.category === 'カスタム';

  // Debug logs (remove in production)
  console.log('Feature flags from API:', featureFlags);
  console.log('templateEditEnabled:', templateEditEnabled);

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
    if (!isCustomPrompt || !confirm(t('Are you sure you want to delete this custom prompt?'))) {
      return;
    }

    setIsDeleting(true);
    try {
      await deleteCustomPrompt.mutateAsync({ name: template.name });
    } catch (error) {
      console.error('Failed to delete custom prompt:', error);
      // エラーハンドリングは必要に応じて追加
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div
      className={cn(
        'group hover:bg-accent/50 transition-colors',
        'border-b border-border last:border-b-0',
        'p-4',
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1">
            <h4 className="font-medium text-sm truncate">{template.name}</h4>
            <Badge variant="outline" className="text-xs shrink-0">
              {template.category}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2">{template.description}</p>
        </div>

        <div className="flex gap-2 shrink-0">
          {isCustomPrompt && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleDelete}
              disabled={isDeleting}
              className="p-2 text-red-600 hover:text-red-700 border-red-200 hover:border-red-300"
              title={t('Delete')}
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
          {templateEditEnabled && (
            <Button variant="outline" size="sm" onClick={handleEdit} className="gap-1.5 text-xs">
              <Edit className="w-3 h-3" />
              {t('Edit')}
            </Button>
          )}
          {onSendDirectly && (
            <Button variant="default" size="sm" onClick={handleSend} className="gap-1.5 text-xs">
              <Send className="w-3 h-3" />
              {t('Send')}
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
  mode?: 'select' | 'send';
  className?: string;
}

export const TemplateList = ({
  templates,
  onSelectTemplate,
  onSendDirectly,
  className = '',
}: TemplateListProps) => {
  return (
    <div
      className={cn(
        'border border-border rounded-lg bg-card max-h-[60vh] overflow-y-auto',
        className
      )}
    >
      {templates.map(template => (
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
