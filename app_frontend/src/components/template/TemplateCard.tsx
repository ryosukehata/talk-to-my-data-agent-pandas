// Template Card Component

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTranslation } from "@/i18n";
import { cn } from "@/lib/utils";
import type { PromptTemplate } from "@/api/templates/types";

interface TemplateCardProps {
  template: PromptTemplate;
  onSelect: (template: PromptTemplate) => void;
  variant?: "default" | "compact";
  className?: string;
}

export const TemplateCard = ({
  template,
  onSelect,
  variant = "default",
  className = "",
}: TemplateCardProps) => {
  const { t } = useTranslation();

  const handleSelect = () => {
    onSelect(template);
  };

  if (variant === "compact") {
    return (
      <div
        className={cn(
          "cursor-pointer transition-shadow hover:shadow-md",
          "rounded-lg border border-border bg-card p-4",
          className,
        )}
        onClick={handleSelect}
      >
        <div className="mb-2 flex items-start justify-between">
          <h4 className="line-clamp-1 text-sm font-medium">{template.name}</h4>
          <Badge variant="default" className="text-xs">
            {template.category}
          </Badge>
        </div>
        <p className="mb-3 line-clamp-2 text-xs text-muted-foreground">
          {template.description}
        </p>
        <Button size="sm" className="w-full text-xs">
          {t("Use Template")}
        </Button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "transition-shadow hover:shadow-md",
        "rounded-lg border border-border bg-card",
        className,
      )}
    >
      <div className="p-4 pb-2">
        <div className="mb-2 flex items-start justify-between">
          <h3 className="line-clamp-1 text-base font-semibold">
            {template.name}
          </h3>
          <Badge variant="default">{template.category}</Badge>
        </div>
        <p className="line-clamp-2 text-sm text-muted-foreground">
          {template.description}
        </p>
      </div>
      <div className="p-4 pt-2">
        <div className="mb-4">
          <p className="line-clamp-3 rounded-md bg-muted/50 p-3 text-sm text-muted-foreground">
            {template.prompt_text_template}
          </p>
        </div>
        <Button onClick={handleSelect} className="w-full">
          {t("Use Template")}
        </Button>
      </div>
    </div>
  );
};
