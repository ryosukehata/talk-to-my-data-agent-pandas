export const customPromptsKeys = {
  all: ['customPrompts'] as const,
  lists: () => [...customPromptsKeys.all, 'list'] as const,
  list: (filters: string) => [...customPromptsKeys.lists(), { filters }] as const,
  details: () => [...customPromptsKeys.all, 'detail'] as const,
  detail: (name: string) => [...customPromptsKeys.details(), name] as const,
  names: () => [...customPromptsKeys.all, 'names'] as const,
};
