// Prompt Template API Types

export interface PromptTemplate {
  name: string;
  category: string;
  description: string;
  prompt_text_template: string;
}

export interface TemplateCategory {
  name: string;
  count?: number;
}

export interface TemplatesResponse {
  templates: PromptTemplate[];
}

export interface CategoriesResponse {
  categories: string[];
}

export interface TemplateSummaryResponse {
  total_templates: number;
  categories: string[];
  category_counts: Record<string, number>;
}

export interface TemplateResponse {
  template: PromptTemplate;
}

export interface FetchTemplatesParams {
  category?: string;
  search?: string;
}
