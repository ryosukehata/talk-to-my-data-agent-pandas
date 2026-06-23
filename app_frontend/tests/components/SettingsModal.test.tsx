import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { SettingsModal } from "@/components/SettingsModal";
import { useDataRobotInfo, useUpdateApiToken } from "@/api/user/hooks";
import { renderWithProviders } from "../test-utils";

const reloadTemplatesMock = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
}));

vi.mock("@/api/user/hooks", () => ({
  useDataRobotInfo: vi.fn(),
  useUpdateApiToken: vi.fn(),
}));

vi.mock("@/api/templates/reloadHooks", () => ({
  useReloadTemplates: () => ({
    mutateAsync: reloadTemplatesMock.mutateAsync,
    isPending: false,
  }),
}));

let refetchDataRobotInfo: ReturnType<typeof vi.fn>;
let updateApiToken: ReturnType<typeof vi.fn>;

describe("SettingsModal", () => {
  beforeEach(() => {
    window.ENV = {};
    refetchDataRobotInfo = vi.fn().mockResolvedValue({});
    updateApiToken = vi.fn();
    reloadTemplatesMock.mutateAsync.mockReset();
    reloadTemplatesMock.mutateAsync.mockResolvedValue({
      total_templates: 2,
      categories: 1,
    });
    (useUpdateApiToken as Mock).mockReturnValue({
      mutate: updateApiToken,
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
      refetch: refetchDataRobotInfo,
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
    expect(screen.getByTestId("api-key-value")).toHaveTextContent("****1234");
    expect(screen.getByTestId("manage-api-keys-link")).toHaveAttribute(
      "href",
      "/account/developer-tools",
    );
  });

  test("hides connected-as row when no display name is available", () => {
    (useDataRobotInfo as Mock).mockReturnValue({
      data: {
        datarobot_account_info: {
          uid: "user-1",
          username: "fallback-user",
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

  test("keeps upstream refresh action wired to DataRobot info refetch", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SettingsModal isOpen={true} onOpenChange={vi.fn()} />);

    await user.click(screen.getByTestId("refresh-connection-button"));

    await waitFor(() => {
      expect(refetchDataRobotInfo).toHaveBeenCalledTimes(1);
    });
  });

  test("keeps upstream API token update action wired to mutation", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SettingsModal isOpen={true} onOpenChange={vi.fn()} />);

    await user.type(screen.getByPlaceholderText("Enter API key"), "new-token");
    await user.click(screen.getByTestId("update-api-key-button"));

    expect(updateApiToken).toHaveBeenCalledWith(
      "new-token",
      expect.objectContaining({
        onSuccess: expect.any(Function),
      }),
    );
  });

  test("keeps template reload action wired to added mutation", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SettingsModal isOpen={true} onOpenChange={vi.fn()} />);

    await user.click(screen.getByTestId("reload-templates-button"));

    await waitFor(() => {
      expect(reloadTemplatesMock.mutateAsync).toHaveBeenCalledTimes(1);
    });
  });
});
