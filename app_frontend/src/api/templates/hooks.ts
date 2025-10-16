// Prompt Template React Query Hooks

import { useQuery } from '@tanstack/react-query';
import { templatesApi } from './requests';
import type { FetchTemplatesParams } from './types';

// Template query keys for cache management
export const templateQueryKeys = {
  all: ['templates'] as const,
  templates: (params?: FetchTemplatesParams) => [...templateQueryKeys.all, 'list', params] as const,
  categories: () => [...templateQueryKeys.all, 'categories'] as const,
  summary: () => [...templateQueryKeys.all, 'summary'] as const,
  template: (name: string) => [...templateQueryKeys.all, 'detail', name] as const,
};

// Fetch templates with optional filtering
export const useFetchTemplates = (params?: FetchTemplatesParams) => {
  return useQuery({
    queryKey: templateQueryKeys.templates(params),
    queryFn: () => templatesApi.getTemplates(params),
    staleTime: 5 * 60 * 1000, // 5 minutes cache
    gcTime: 10 * 60 * 1000, // 10 minutes garbage collection
  });
};

// Fetch template categories
export const useFetchTemplateCategories = () => {
  return useQuery({
    queryKey: templateQueryKeys.categories(),
    queryFn: templatesApi.getCategories,
    staleTime: 10 * 60 * 1000, // 10 minutes cache
    gcTime: 30 * 60 * 1000, // 30 minutes garbage collection
  });
};

// Fetch template summary/statistics
export const useFetchTemplateSummary = () => {
  return useQuery({
    queryKey: templateQueryKeys.summary(),
    queryFn: templatesApi.getSummary,
    staleTime: 10 * 60 * 1000, // 10 minutes cache
    gcTime: 30 * 60 * 1000, // 30 minutes garbage collection
  });
};

// Fetch specific template by name
export const useFetchTemplate = (templateName: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: templateQueryKeys.template(templateName),
    queryFn: () => templatesApi.getTemplate(templateName),
    enabled: enabled && !!templateName,
    staleTime: 15 * 60 * 1000, // 15 minutes cache
    gcTime: 30 * 60 * 1000, // 30 minutes garbage collection
  });
};
