export interface CustomPromptCreate {
  name: string;
  description?: string;
  prompt_text_template: string;
}

export interface CustomPromptResponse {
  name: string;
  category: string;
  description?: string;
  prompt_text_template: string;
}

export interface CustomPromptDelete {
  name: string;
}
