import React from "react";

export const ColorTest: React.FC = () => {
  return (
    <div className="space-y-4 p-4">
      <h3 className="text-lg font-semibold">Color Test</h3>

      {/* Suggested Prompt Background Test */}
      <div className="flex items-center gap-4">
        <div className="h-10 w-20 rounded border bg-muted"></div>
        <span>bg-muted</span>
      </div>

      {/* Original color for comparison */}
      <div className="flex items-center gap-4">
        <div className="h-10 w-20 rounded border bg-[#22272b]"></div>
        <span>Original #22272b</span>
      </div>
    </div>
  );
};
