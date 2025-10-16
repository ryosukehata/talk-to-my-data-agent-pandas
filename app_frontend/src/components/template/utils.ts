import { PromptTemplate } from '@/api/templates/types';
import { CustomPromptResponse } from '@/api/custom-prompts/types';

/**
 * カスタムプロンプトをテンプレート形式に変換
 */
export const convertCustomPromptsToTemplates = (
  customPrompts: CustomPromptResponse[]
): PromptTemplate[] => {
  return customPrompts.map(prompt => ({
    name: prompt.name,
    category: prompt.category, // APIレスポンスのcategoryをそのまま使用
    description: prompt.description || '',
    prompt_text_template: prompt.prompt_text_template,
  }));
};

/**
 * テンプレートがカスタムプロンプトかどうかを判定
 */
export const isCustomTemplate = (template: PromptTemplate): boolean => {
  return template.category === 'カスタム';
};
