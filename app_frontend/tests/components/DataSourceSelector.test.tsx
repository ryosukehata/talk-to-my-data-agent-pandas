import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';
import { DataSourceSelector } from '@/components/DataSourceSelector';

vi.mock('@/api/datasets/hooks', () => ({
  useGetSupportedDataSourceTypes: () => ({ isLoading: false }),
}));

vi.mock('@/api/datasources/hooks', () => ({
  useListAvailableDataStores: () => ({ isLoading: false }),
}));

describe('DataSourceSelector', () => {
  test('shows upstream v0.5.0 data source descriptions', () => {
    render(<DataSourceSelector value="file" onChange={() => {}} />);

    expect(
      screen.getByText(
        'Select to upload a local file or your DataRobot Data Registry file up to 200 MB.'
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'Connect and add data from your remote data registry for files greater than 200 MB, up to a maximum of 10 GB. Processing large files may involve lengthy runtimes and increased costs.'
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'Select tables from the application-configured database. This option supports Snowflake, SAP DataSphere, and BigQuery.'
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'Select tables from DataRobot supported data store connections, such as Redshift or PostgreSQL.'
      )
    ).toBeInTheDocument();
  });
});
