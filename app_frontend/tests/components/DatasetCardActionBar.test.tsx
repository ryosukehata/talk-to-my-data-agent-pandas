import { render, screen } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';
import { DatasetCardActionBar } from '@/components/data/DatasetCardActionBar';
import { DATA_TABS } from '@/state/constants';

vi.mock('@fortawesome/react-fontawesome', () => ({
  FontAwesomeIcon: () => <span data-testid="font-awesome-icon" />,
}));

describe('DatasetCardActionBar', () => {
  test('shows dictionary download action on description tab', () => {
    render(<DatasetCardActionBar viewMode={DATA_TABS.DESCRIPTION} onDownload={vi.fn()} />);

    expect(screen.getByTitle('Download dictionary as CSV')).toBeInTheDocument();
  });

  test('hides dictionary download action on raw rows tab', () => {
    render(<DatasetCardActionBar viewMode={DATA_TABS.RAW} onDownload={vi.fn()} />);

    expect(screen.queryByTitle('Download dictionary as CSV')).not.toBeInTheDocument();
  });
});
