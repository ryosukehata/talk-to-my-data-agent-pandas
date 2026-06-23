// Icon-based Template Card Component

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTranslation } from "@/i18n";
import { cn } from "@/lib/utils";
import type { PromptTemplate } from "@/api/templates/types";
import {
  TrendingUp,
  Users,
  DollarSign,
  Target,
  Cog,
  BarChart3,
  PieChart,
  LineChart,
} from "lucide-react";

interface TemplateCardIconProps {
  template: PromptTemplate;
  onSelect: (template: PromptTemplate) => void;
  className?: string;
}

// カテゴリごとのアイコンマッピング
const getCategoryIcon = (category: string) => {
  switch (category.toLowerCase()) {
    case "営業":
    case "sales":
      return TrendingUp;
    case "人事":
    case "hr":
      return Users;
    case "財務":
    case "finance":
      return DollarSign;
    case "マーケティング":
    case "marketing":
      return Target;
    case "オペレーション":
    case "operations":
      return Cog;
    default:
      return BarChart3;
  }
};

// テンプレート内容から適切なアイコンを推測
const getContentIcon = (template: PromptTemplate) => {
  const content = template.prompt_text_template.toLowerCase();
  if (content.includes("売上") || content.includes("revenue"))
    return TrendingUp;
  if (content.includes("割合") || content.includes("比率")) return PieChart;
  if (content.includes("推移") || content.includes("トレンド"))
    return LineChart;
  return BarChart3;
};

export const TemplateCardIcon = ({
  template,
  onSelect,
  className = "",
}: TemplateCardIconProps) => {
  const { t } = useTranslation();
  const CategoryIcon = getCategoryIcon(template.category);
  const ContentIcon = getContentIcon(template);

  const handleSelect = () => {
    onSelect(template);
  };

  return (
    <div
      className={cn(
        "group cursor-pointer transition-all duration-200 hover:shadow-lg",
        "rounded-xl border border-border bg-card hover:bg-accent/5",
        "p-6 text-center",
        className,
      )}
      onClick={handleSelect}
    >
      {/* アイコンエリア */}
      <div className="mb-4 flex justify-center">
        <div className="relative">
          <div className="flex size-16 items-center justify-center rounded-full bg-primary/10 transition-colors group-hover:bg-primary/20">
            <CategoryIcon className="size-8 text-primary" />
          </div>
          <div className="absolute -right-1 -bottom-1 flex size-6 items-center justify-center rounded-full border-2 border-background bg-background">
            <ContentIcon className="size-3 text-muted-foreground" />
          </div>
        </div>
      </div>

      {/* テンプレート名 */}
      <h3 className="mb-2 line-clamp-2 min-h-[2.5rem] text-sm font-semibold">
        {template.name}
      </h3>

      {/* カテゴリバッジ */}
      <Badge variant="default" className="mb-3 text-xs">
        {template.category}
      </Badge>

      {/* 簡潔な説明 */}
      <p className="mb-4 line-clamp-2 min-h-[2rem] text-xs text-muted-foreground">
        {template.description}
      </p>

      {/* 選択ボタン */}
      <Button
        size="sm"
        className="w-full text-xs opacity-0 transition-opacity group-hover:opacity-100"
      >
        {t("Use Template")}
      </Button>
    </div>
  );
};
