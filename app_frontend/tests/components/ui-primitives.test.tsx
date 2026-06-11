import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

describe('UI primitives', () => {
  test('renders clickable badges as buttons and passive badges as divs', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    const { rerender } = render(<Badge onClick={onClick}>Clickable</Badge>);

    await user.click(screen.getByRole('button', { name: /clickable/i }));
    expect(onClick).toHaveBeenCalledTimes(1);

    rerender(<Badge>Passive</Badge>);
    expect(screen.queryByRole('button', { name: /passive/i })).not.toBeInTheDocument();
    expect(screen.getByText('Passive')).toHaveAttribute('data-slot', 'badge');
  });

  test('renders checkbox checked and indeterminate states', () => {
    const { rerender } = render(<Checkbox checked aria-label="checked option" />);

    expect(screen.getByRole('checkbox', { name: /checked option/i })).toHaveAttribute(
      'data-state',
      'checked'
    );

    rerender(<Checkbox checked="indeterminate" aria-label="mixed option" />);
    expect(screen.getByRole('checkbox', { name: /mixed option/i })).toHaveAttribute(
      'data-state',
      'indeterminate'
    );
  });

  test('renders tooltip content on hover', async () => {
    const user = userEvent.setup();

    render(
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger>Details</TooltipTrigger>
          <TooltipContent>Helpful content</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );

    await user.hover(screen.getByText('Details'));

    expect(await screen.findAllByText('Helpful content')).not.toHaveLength(0);
  });

  test('renders skeleton with pulse styling', () => {
    render(<Skeleton data-testid="loading-skeleton" />);

    expect(screen.getByTestId('loading-skeleton')).toHaveClass('animate-pulse');
  });
});
