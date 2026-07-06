import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ThemeProvider, useTheme } from "@/theme/theme-provider";

const mockPrefersDark = (matches: boolean) => {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
};

const ThemeProbe = () => {
  const { theme, setTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme}
    </button>
  );
};

describe("ThemeProvider", () => {
  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
    mockPrefersDark(false);
  });

  test("uses upstream system light preference and persists it", () => {
    mockPrefersDark(false);

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByRole("button", { name: "light" })).toBeInTheDocument();
    expect(document.documentElement).not.toHaveClass("dark");
    expect(localStorage.getItem("app-theme")).toBe("light");
  });

  test("uses upstream system dark preference and persists it", () => {
    mockPrefersDark(true);

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByRole("button", { name: "dark" })).toBeInTheDocument();
    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem("app-theme")).toBe("dark");
  });

  test("uses saved upstream app-theme value and updates document class", async () => {
    const user = userEvent.setup();
    mockPrefersDark(true);
    localStorage.setItem("app-theme", "light");

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByRole("button", { name: "light" })).toBeInTheDocument();
    expect(document.documentElement).not.toHaveClass("dark");

    await user.click(screen.getByRole("button", { name: "light" }));

    expect(screen.getByRole("button", { name: "dark" })).toBeInTheDocument();
    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem("app-theme")).toBe("dark");
  });
});
