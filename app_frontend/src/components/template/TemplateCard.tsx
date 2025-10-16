// Template Card Component

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from '@/i18n';
import { cn } from '@/lib/utils';
import type { PromptTemplate } from '@/api/templates/types';

interface TemplateCardProps {
  template: PromptTemplate;
  onSelect: (template: PromptTemplate) => void;
  variant?: 'default' | 'compact';
  className?: string;
}

export const TemplateCard = ({
  template,
  onSelect,
  variant = 'default',
  className = '',
}: TemplateCardProps) => {
  const { t } = useTranslation();

  const handleSelect = () => {
    onSelect(template);
  };

  if (variant === 'compact') {
    return (
      <div
        className={cn(
          'cursor-pointer hover:shadow-md transition-shadow',
          'border border-border rounded-lg p-4 bg-card',
          className
        )}
        onClick={handleSelect}
      >
        <div className="flex justify-between items-start mb-2">
          <h4 className="font-medium text-sm line-clamp-1">{template.name}</h4>
          <Badge variant="secondary" className="text-xs">
            {template.category}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{template.description}</p>
        <Button size="sm" className="w-full text-xs">
          {t('Use Template')}
        </Button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'hover:shadow-md transition-shadow',
        'border border-border rounded-lg bg-card',
        className
      )}
    >
      <div className="p-4 pb-2">
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-semibold text-base line-clamp-1">{template.name}</h3>
          <Badge variant="secondary">{template.category}</Badge>
        </div>
        <p className="text-sm text-muted-foreground line-clamp-2">{template.description}</p>
      </div>
      <div className="p-4 pt-2">
        <div className="mb-4">
          <p className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-md line-clamp-3">
            {template.prompt_text_template}
          </p>
        </div>
        <Button onClick={handleSelect} className="w-full">
          {t('Use Template')}
        </Button>
      </div>
    </div>
  );
};
