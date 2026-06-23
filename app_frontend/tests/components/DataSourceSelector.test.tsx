import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { DataSourceSelector } from "@/components/DataSourceSelector";

vi.mock("@/api/datasets/hooks", () => ({
  useGetSupportedDataSourceTypes: () => ({ isLoading: false }),
}));

vi.mock("@/api/datasources/hooks", () => ({
  useListAvailableDataStores: () => ({ isLoading: false }),
}));

describe("DataSourceSelector", () => {
  test("shows upstream v0.5.2 data source descriptions in tooltips", async () => {
    const user = userEvent.setup();
    const descriptions = [
      [
        "Show Local file or Data Registry description",
        "Select to upload a local file or your DataRobot Data Registry file up to 200 MB.",
      ],
      [
        "Show Remote Data Registry description",
        "Connect and add data from your remote data registry for files greater than 200 MB, up to a maximum of 10 GB. Processing large files may involve lengthy runtimes and increased costs.",
      ],
      [
        "Show Database description",
        "Select tables from the application-configured database. This option supports Snowflake, SAP DataSphere, and BigQuery.",
      ],
      [
        "Show Remote Data Connections description",
        "Select tables from DataRobot supported data store connections, such as Redshift or PostgreSQL.",
      ],
    ] as const;

    for (const [buttonName, description] of descriptions) {
      const { unmount } = render(
        <DataSourceSelector value="file" onChange={() => {}} />,
      );

      expect(screen.queryByText(description)).not.toBeInTheDocument();

      await user.hover(screen.getByRole("button", { name: buttonName }));
      expect(await screen.findAllByText(description)).not.toHaveLength(0);
      unmount();
    }
  });
});
