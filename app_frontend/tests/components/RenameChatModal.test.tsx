import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi, type Mock } from 'vitest';
import { RenameChatModal } from '@/components/RenameChatModal';
import { useRenameChat } from '@/api/chat-messages/hooks';

vi.mock('@/api/chat-messages/hooks', () => ({
  useRenameChat: vi.fn(),
}));

vi.mock('@fortawesome/react-fontawesome', () => ({
  FontAwesomeIcon: () => <div data-testid="mock-icon" />,
}));

describe('RenameChatModal Component', () => {
  beforeEach(() => {
    (useRenameChat as Mock).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
  });

  test('enforces max length on chat name input', () => {
    render(<RenameChatModal chatId="123" currentName="Test Chat" />);

    fireEvent.click(screen.getByRole('button'));

    expect(screen.getByRole('textbox')).toHaveAttribute('maxLength', '200');
  });

  test('shows warning when chat name reaches max length', () => {
    render(<RenameChatModal chatId="123" currentName="Test Chat" />);

    fireEvent.click(screen.getByRole('button'));
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'a'.repeat(200) },
    });

    expect(screen.getByText(/has reached maximum of 200 characters/i)).toBeInTheDocument();
  });
});
