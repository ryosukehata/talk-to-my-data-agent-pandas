import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { AddDataModal } from '@/components/AddDataModal';
import { renderWithProviders } from '../test-utils';

const mockUploadMutate = vi.fn();
const mockLoadFromDatabase = vi.fn();
const mockSelectDataSources = vi.fn();

vi.mock('@/api/datasets/hooks', () => ({
  useFetchDatasets: () => ({
    data: {
      local: [{ id: 'local-1', name: 'sales.csv', size: '12 KB' }],
      remote: [{ id: 'remote-1', name: 'catalog-sales.csv', size: '3 MB' }],
    },
    isLoading: false,
  }),
  useFileUploadMutation: () => ({
    mutate: mockUploadMutate,
    progress: 0,
  }),
  useGetSupportedDataSourceTypes: () => ({
    isLoading: false,
  }),
}));

vi.mock('@/api/database/hooks', () => ({
  useGetDatabaseSchemas: () => ({
    data: {
      public: 'Public schema',
      finance: 'Finance schema',
    },
  }),
  useGetDefaultSchema: () => ({
    data: 'public',
  }),
  useGetDatabaseTables: () => ({
    data: {
      orders: 'Orders table',
      customers: 'Customers table',
    },
    isLoading: false,
  }),
  useLoadFromDatabaseMutation: () => ({
    mutate: mockLoadFromDatabase,
  }),
}));

vi.mock('@/api/datasources/hooks', () => ({
  useListAvailableDataStores: () => ({
    data: [
      {
        id: 'store-1',
        canonical_name: 'Postgres store',
        defined_data_sources: [
          {
            schema: 'public',
            table: 'orders',
          },
        ],
      },
    ],
    isLoading: false,
  }),
  useSelectDataSourcesMutation: () => ({
    mutate: mockSelectDataSources,
  }),
}));

describe('AddDataModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  test('keeps local upload and catalog selection visible by default', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AddDataModal />);

    await user.click(screen.getByRole('button', { name: /add data/i }));

    expect(screen.getByText('Local files')).toBeInTheDocument();
    expect(
      screen.getByText('Select one or more CSV, XLSX, XLS files, up to 200MB.')
    ).toBeInTheDocument();
    expect(screen.getByText('Data Registry')).toBeInTheDocument();
    expect(screen.getByText('Select one or more catalog items')).toBeInTheDocument();
  });

  test('keeps database schema and table selection available', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AddDataModal />);

    await user.click(screen.getByRole('button', { name: /add data/i }));
    await user.click(screen.getByRole('radio', { name: 'Database' }));

    expect(screen.getByText('Database Schema')).toBeInTheDocument();
    expect(screen.getByLabelText('Schema')).toHaveValue('public');
    expect(screen.getByRole('option', { name: 'public - Public schema' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'finance - Finance schema' })).toBeInTheDocument();
    expect(screen.getByText('Database Tables')).toBeInTheDocument();
    expect(screen.getByTestId('database-table-select')).toHaveTextContent(
      'Select one or more tables.'
    );
  });

  test('keeps remote data connection selection available', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AddDataModal />);

    await user.click(screen.getByRole('button', { name: /add data/i }));
    await user.click(screen.getByRole('radio', { name: 'Remote Data Connections' }));

    expect(screen.getByText('Add External Data Source')).toBeInTheDocument();
    expect(screen.getByText('Select a data store')).toBeInTheDocument();
    expect(screen.getByText('Select one or more data sources')).toBeInTheDocument();
  });
});
