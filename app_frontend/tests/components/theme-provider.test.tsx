import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test } from 'vitest';
import { ThemeProvider, useTheme } from '@/theme/theme-provider';

const ThemeProbe = () => {
  const { theme, setTheme } = useTheme();

  return (
    <button type="button" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
      {theme}
    </button>
  );
};

describe('ThemeProvider', () => {
  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  test('defaults to upstream dark theme and persists it', () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>
    );

    expect(screen.getByRole('button', { name: 'dark' })).toBeInTheDocument();
    expect(document.documentElement).toHaveClass('dark');
    expect(localStorage.getItem('app-theme')).toBe('dark');
  });

  test('uses saved upstream app-theme value and updates document class', async () => {
    const user = userEvent.setup();
    localStorage.setItem('app-theme', 'light');

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>
    );

    expect(screen.getByRole('button', { name: 'light' })).toBeInTheDocument();
    expect(document.documentElement).not.toHaveClass('dark');

    await user.click(screen.getByRole('button', { name: 'light' }));

    expect(screen.getByRole('button', { name: 'dark' })).toBeInTheDocument();
    expect(document.documentElement).toHaveClass('dark');
    expect(localStorage.getItem('app-theme')).toBe('dark');
  });
});
