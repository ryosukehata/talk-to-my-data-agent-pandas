import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { SavePromptButton } from '@/components/custom-prompts/SavePromptButton';
import { TemplateSelector } from '@/components/template/TemplateSelector';
import { renderWithProviders } from '../test-utils';

vi.mock('@/api/feature-flag', () => ({
  useFetchFeatureFlags: () => ({
    data: {
      templateEditEnabled: true,
      customPromptsEnabled: true,
      refinerEnabled: true,
      refinerAutoSend: false,
      reportBuilderEnabled: true,
    },
  }),
}));

vi.mock('@/api/templates/hooks', () => ({
  useFetchTemplates: () => ({
    data: {
      templates: [
        {
          name: 'Standard analysis',
          category: '分析',
          description: 'Built-in template',
          prompt_text_template: 'Analyze sales',
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
  useFetchTemplateCategories: () => ({
    data: {
      categories: ['分析'],
    },
    isLoading: false,
  }),
}));

vi.mock('@/api/custom-prompts/hooks', () => ({
  useFetchCustomPrompts: () => ({
    data: {
      custom_prompts: [
        {
          name: 'Saved custom prompt',
          prompt_text: 'Use my saved prompt',
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
  useDeleteCustomPrompt: () => ({
    mutateAsync: vi.fn(),
  }),
}));

describe('custom feature entrypoints', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('shows the save prompt entrypoint when custom prompts are enabled', () => {
    renderWithProviders(<SavePromptButton promptText="Summarize sales" />);

    expect(screen.getByRole('button', { name: 'Save as custom prompt' })).toHaveAttribute(
      'title',
      'Save as custom prompt'
    );
  });

  test('keeps the template selector and custom prompt category available', () => {
    renderWithProviders(
      <TemplateSelector open onOpenChange={() => {}} onSelectTemplate={() => {}} />
    );

    expect(screen.getByText('Select Prompt Template')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'All Categories' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'カスタム' })).toBeInTheDocument();
    expect(screen.getByText('Standard analysis')).toBeInTheDocument();
    expect(screen.getByText('Saved custom prompt')).toBeInTheDocument();
  });
});
