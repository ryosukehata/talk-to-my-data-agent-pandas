// Template Category Filter Component

import { Button } from "@/components/ui/button";
import { useTranslation } from "@/i18n";
import { cn } from "@/lib/utils";

interface TemplateCategoryFilterProps {
  categories: string[];
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
  className?: string;
}

export const TemplateCategoryFilter = ({
  categories,
  selectedCategory,
  onCategoryChange,
  className = "",
}: TemplateCategoryFilterProps) => {
  const { t } = useTranslation();

  const allCategories = ["all", ...categories];

  const getCategoryLabel = (category: string) => {
    if (category === "all") {
      return t("All Categories");
    }
    return category;
  };

  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {allCategories.map((category) => (
        <Button
          key={category}
          variant={selectedCategory === category ? "primary" : "secondary"}
          size="sm"
          onClick={() => onCategoryChange(category)}
          className="text-sm"
        >
          {getCategoryLabel(category)}
        </Button>
      ))}
    </div>
  );
};
