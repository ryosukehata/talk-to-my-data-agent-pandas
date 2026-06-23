import { afterEach, describe, expect, test, vi } from "vitest";
import { getApiUrl, getBaseUrl } from "@/lib/utils";

const originalEnv = window.ENV;

afterEach(() => {
  window.ENV = originalEnv;
  vi.unstubAllEnvs();
});

describe("frontend URL helpers", () => {
  test("builds the default API URL from the current origin", () => {
    window.ENV = {};

    expect(getBaseUrl()).toBe(undefined);
    expect(getApiUrl()).toBe("http://localhost:3000/api");
  });

  test("preserves DataRobot app base paths from runtime env", () => {
    window.ENV = {
      APP_BASE_URL: "custom_applications/app-id",
    };

    expect(getBaseUrl()).toBe("custom_applications/app-id");
    expect(getApiUrl()).toBe(
      "http://localhost:3000/custom_applications/app-id/api",
    );
  });

  test("uses Vite notebook port during local notebook development", () => {
    vi.stubEnv("MODE", "development");
    window.ENV = {
      APP_BASE_URL: "notebook-sessions/notebook-id",
    };

    expect(getApiUrl()).toBe(
      "http://localhost:3000/notebook-sessions/notebook-id/ports/5173/api",
    );
  });

  test("uses backend API port when static frontend is served in notebooks", () => {
    window.ENV = {
      APP_BASE_URL: "notebook-sessions/notebook-id",
      API_PORT: "8080",
      IS_STATIC_FRONTEND: true,
    };

    expect(getBaseUrl()).toBe("notebook-sessions/notebook-id/ports/8080");
    expect(getApiUrl()).toBe(
      "http://localhost:3000/notebook-sessions/notebook-id/ports/8080/api",
    );
  });
});
