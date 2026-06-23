import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { SettingsModal } from "@/components/SettingsModal";
import { useDataRobotInfo, useUpdateApiToken } from "@/api/user/hooks";
import { renderWithProviders } from "../test-utils";

vi.mock("@/api/user/hooks", () => ({
  useDataRobotInfo: vi.fn(),
  useUpdateApiToken: vi.fn(),
}));

vi.mock("@/api/templates/reloadHooks", () => ({
  useReloadTemplates: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

describe("SettingsModal", () => {
  beforeEach(() => {
    window.ENV = {};
    (useUpdateApiToken as Mock).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      reset: vi.fn(),
    });
    (useDataRobotInfo as Mock).mockReturnValue({
      data: {
        datarobot_account_info: {
          uid: "user-1",
          username: "",
          firstName: "Anton",
          lastName: "Berezhinsky",
          email: "anton@example.com",
          language: "en",
        },
        datarobot_api_token: "****1234",
        datarobot_api_scoped_token: null,
      },
      isLoading: false,
      refetch: vi.fn(),
    });
  });

  test("shows connected user name from first and last name", () => {
    renderWithProviders(<SettingsModal isOpen={true} onOpenChange={vi.fn()} />);

    expect(screen.getByTestId("connected-as-value")).toHaveTextContent(
      "Anton Berezhinsky",
    );
    expect(screen.getByTestId("email-value")).toHaveTextContent(
      "anton@example.com",
    );
  });

  test("hides connected-as row when no display name is available", () => {
    (useDataRobotInfo as Mock).mockReturnValue({
      data: {
        datarobot_account_info: {
          uid: "user-1",
          username: "",
          firstName: "",
          lastName: "",
          email: "anon@example.com",
          language: "en",
        },
        datarobot_api_token: "****1234",
        datarobot_api_scoped_token: null,
      },
      isLoading: false,
      refetch: vi.fn(),
    });

    renderWithProviders(<SettingsModal isOpen={true} onOpenChange={vi.fn()} />);

    expect(screen.queryByTestId("connected-as-value")).not.toBeInTheDocument();
    expect(screen.getByTestId("email-value")).toHaveTextContent(
      "anon@example.com",
    );
  });

  test("shows app version when runtime env provides APP_VERSION", () => {
    window.ENV = { APP_VERSION: "v11.5.3-1-gabcdef0" };

    renderWithProviders(<SettingsModal isOpen={true} onOpenChange={vi.fn()} />);

    expect(
      screen.getByText(/Version: v11\.5\.3-1-gabcdef0/),
    ).toBeInTheDocument();
  });
});
