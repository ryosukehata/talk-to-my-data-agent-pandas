/**
 * Template reload API functions
 */

import apiClient from "@/api/apiClient";

export interface TemplateReloadResponse {
  message: string;
  total_templates: string;
  categories: string;
}

/**
 * Reload templates from data source
 */
export const reloadTemplates = async (): Promise<TemplateReloadResponse> => {
  const response = await apiClient.post("/v1/templates/reload");
  return response.data;
};
