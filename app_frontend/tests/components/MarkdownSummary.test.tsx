import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { MarkdownContent } from "@/components/chat/MarkdownContent";
import { SummaryTabContent } from "@/components/chat/SummaryTabContent";

vi.mock("@/components/chat/PlotPanel", () => ({
  PlotPanel: ({
    plotData,
  }: {
    plotData: { layout?: { title?: { text?: string } } };
  }) => <div data-testid="plot-panel">{plotData.layout?.title?.text}</div>,
}));

describe("MarkdownContent and summary rendering", () => {
  test("renders strong markdown as semantic bold text", () => {
    render(<MarkdownContent content="Revenue is **up** this quarter." />);

    const strong = screen.getByText("up");
    expect(strong.tagName).toBe("STRONG");
  });

  test("renders bottom line markdown in the summary tab", () => {
    render(
      <SummaryTabContent bottomLine="**Revenue** increased." fig1="" fig2="" />,
    );

    expect(screen.getByText("Bottom line")).toBeInTheDocument();
    expect(screen.getByText("Revenue").tagName).toBe("STRONG");
  });

  test("continues rendering summary plots when figure JSON is present", () => {
    render(
      <SummaryTabContent
        bottomLine="Result"
        fig1='{"data":[],"layout":{"title":{"text":"First plot"}}}'
        fig2='{"data":[],"layout":{"title":{"text":"Second plot"}}}'
      />,
    );

    expect(screen.getByText("First plot")).toBeInTheDocument();
    expect(screen.getByText("Second plot")).toBeInTheDocument();
  });
});
