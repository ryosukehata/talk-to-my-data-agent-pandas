import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { Sidebar } from '@/components/Sidebar';
import { renderWithProviders } from '../test-utils';

vi.mock('@/components/WelcomeModal', () => ({
  WelcomeModal: () => null,
}));

vi.mock('@/components/AddDataModal', () => ({
  AddDataModal: () => null,
}));

vi.mock('@/components/NewChatModal', () => ({
  NewChatModal: () => null,
}));

vi.mock('@/components/SettingsModal', () => ({
  SettingsModal: () => null,
}));

vi.mock('@/api/dictionaries', () => ({
  useGeneratedDictionaries: vi.fn(),
  getDictionariesMenu: vi.fn(data => data),
}));

vi.mock('@/api/chat-messages', () => ({
  useFetchAllChats: vi.fn(),
  getChatsMenu: vi.fn(data => data),
}));

vi.mock('@/api/reports', () => ({
  useReports: vi.fn(),
}));

vi.mock('@/api/feature-flag', () => ({
  useFetchFeatureFlags: vi.fn(),
}));

import { useGeneratedDictionaries } from '@/api/dictionaries';
import { useFetchAllChats } from '@/api/chat-messages';
import { useFetchFeatureFlags } from '@/api/feature-flag';
import { useReports } from '@/api/reports';

const mockUseGeneratedDictionaries = vi.mocked(useGeneratedDictionaries);
const mockUseFetchAllChats = vi.mocked(useFetchAllChats);
const mockUseFetchFeatureFlags = vi.mocked(useFetchFeatureFlags);
const mockUseReports = vi.mocked(useReports);

const featureFlags = {
  templateEditEnabled: false,
  customPromptsEnabled: false,
  refinerEnabled: true,
  refinerAutoSend: false,
};

describe('Sidebar Report Builder feature flag', () => {
  beforeEach(() => {
    mockUseGeneratedDictionaries.mockReturnValue({
      data: [],
      isLoading: false,
    } as any);
    mockUseFetchAllChats.mockReturnValue({
      data: [],
      isLoading: false,
    } as any);
    mockUseReports.mockReturnValue({
      data: { reports: [], total: 0 },
      isLoading: false,
    } as any);
  });

  test('hides Report Builder navigation when the flag is disabled', () => {
    mockUseFetchFeatureFlags.mockReturnValue({
      data: { ...featureFlags, reportBuilderEnabled: false },
    } as any);

    renderWithProviders(<Sidebar />);

    expect(screen.queryByText('Reports')).not.toBeInTheDocument();
  });

  test('shows Report Builder navigation when the flag is enabled', () => {
    mockUseFetchFeatureFlags.mockReturnValue({
      data: { ...featureFlags, reportBuilderEnabled: true },
    } as any);

    renderWithProviders(<Sidebar />);

    expect(screen.getByText('Reports')).toBeInTheDocument();
  });
});
