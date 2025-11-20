// Icon-based Template Card Component

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from '@/i18n';
import { cn } from '@/lib/utils';
import type { PromptTemplate } from '@/api/templates/types';
import {
  TrendingUp,
  Users,
  DollarSign,
  Target,
  Cog,
  BarChart3,
  PieChart,
  LineChart,
} from 'lucide-react';

interface TemplateCardIconProps {
  template: PromptTemplate;
  onSelect: (template: PromptTemplate) => void;
  className?: string;
}

// カテゴリごとのアイコンマッピング
const getCategoryIcon = (category: string) => {
  switch (category.toLowerCase()) {
    case '営業':
    case 'sales':
      return TrendingUp;
    case '人事':
    case 'hr':
      return Users;
    case '財務':
    case 'finance':
      return DollarSign;
    case 'マーケティング':
    case 'marketing':
      return Target;
    case 'オペレーション':
    case 'operations':
      return Cog;
    default:
      return BarChart3;
  }
};

// テンプレート内容から適切なアイコンを推測
const getContentIcon = (template: PromptTemplate) => {
  const content = template.prompt_text_template.toLowerCase();
  if (content.includes('売上') || content.includes('revenue')) return TrendingUp;
  if (content.includes('割合') || content.includes('比率')) return PieChart;
  if (content.includes('推移') || content.includes('トレンド')) return LineChart;
  return BarChart3;
};

export const TemplateCardIcon = ({ template, onSelect, className = '' }: TemplateCardIconProps) => {
  const { t } = useTranslation();
  const CategoryIcon = getCategoryIcon(template.category);
  const ContentIcon = getContentIcon(template);

  const handleSelect = () => {
    onSelect(template);
  };

  return (
    <div
      className={cn(
        'group cursor-pointer hover:shadow-lg transition-all duration-200',
        'border border-border rounded-xl bg-card hover:bg-accent/5',
        'p-6 text-center',
        className
      )}
      onClick={handleSelect}
    >
      {/* アイコンエリア */}
      <div className="flex justify-center mb-4">
        <div className="relative">
          <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <CategoryIcon className="w-8 h-8 text-primary" />
          </div>
          <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-background border-2 border-background rounded-full flex items-center justify-center">
            <ContentIcon className="w-3 h-3 text-muted-foreground" />
          </div>
        </div>
      </div>

      {/* テンプレート名 */}
      <h3 className="font-semibold text-sm mb-2 line-clamp-2 min-h-[2.5rem]">{template.name}</h3>

      {/* カテゴリバッジ */}
      <Badge variant="secondary" className="mb-3 text-xs">
        {template.category}
      </Badge>

      {/* 簡潔な説明 */}
      <p className="text-xs text-muted-foreground line-clamp-2 mb-4 min-h-[2rem]">
        {template.description}
      </p>

      {/* 選択ボタン */}
      <Button
        size="sm"
        className="w-full text-xs opacity-0 group-hover:opacity-100 transition-opacity"
      >
        {t('Use Template')}
      </Button>
    </div>
  );
};
