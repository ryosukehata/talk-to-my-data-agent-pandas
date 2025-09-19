import React from 'react';

export const ColorTest: React.FC = () => {
  return (
    <div className="p-4 space-y-4">
      <h3 className="text-lg font-semibold">Color Test</h3>
      
      {/* Suggested Prompt Background Test */}
      <div className="flex items-center gap-4">
        <div className="w-20 h-10 bg-suggested-prompt-bg border rounded"></div>
        <span>bg-suggested-prompt-bg</span>
      </div>
      
      {/* Original color for comparison */}
      <div className="flex items-center gap-4">
        <div className="w-20 h-10 bg-[#22272b] border rounded"></div>
        <span>Original #22272b</span>
      </div>
    </div>
  );
};