// Prompt Template API Requests

import apiClient from '@/api/apiClient';
import type {
  TemplatesResponse,
  CategoriesResponse,
  TemplateSummaryResponse,
  TemplateResponse,
  FetchTemplatesParams,
} from './types';

const TEMPLATES_BASE_URL = '/v1/templates';

export const templatesApi = {
  // Get all templates with optional filtering
  getTemplates: async (params?: FetchTemplatesParams): Promise<TemplatesResponse> => {
    const searchParams = new URLSearchParams();

    if (params?.category && params.category !== 'all') {
      searchParams.append('category', params.category);
    }

    if (params?.search) {
      searchParams.append('search', params.search);
    }

    const url = `${TEMPLATES_BASE_URL}${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    const response = await apiClient.get<TemplatesResponse>(url);
    return response.data;
  },

  // Get all available categories
  getCategories: async (): Promise<CategoriesResponse> => {
    const response = await apiClient.get<CategoriesResponse>(`${TEMPLATES_BASE_URL}/categories`);
    return response.data;
  },

  // Get template statistics
  getSummary: async (): Promise<TemplateSummaryResponse> => {
    const response = await apiClient.get<TemplateSummaryResponse>(
      `${TEMPLATES_BASE_URL}/stats/summary`
    );
    return response.data;
  },

  // Get specific template by name
  getTemplate: async (templateName: string): Promise<TemplateResponse> => {
    const response = await apiClient.get<TemplateResponse>(
      `${TEMPLATES_BASE_URL}/${encodeURIComponent(templateName)}`
    );
    return response.data;
  },
};
