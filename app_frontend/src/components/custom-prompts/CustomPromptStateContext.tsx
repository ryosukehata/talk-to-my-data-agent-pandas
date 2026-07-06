import React, { useState, ReactNode } from "react";
import { CustomPromptStateContext } from "./context";

interface CustomPromptStateProviderProps {
  children: ReactNode;
}

export const CustomPromptStateProvider: React.FC<
  CustomPromptStateProviderProps
> = ({ children }) => {
  const [isSaving, setIsSaving] = useState(false);
  const [pendingUpdate, setPendingUpdate] = useState(false);

  const setSaving = (saving: boolean) => {
    setIsSaving(saving);
    if (saving) {
      setPendingUpdate(true);
    }
  };

  return (
    <CustomPromptStateContext.Provider
      value={{
        isSaving,
        setSaving,
        pendingUpdate,
        setPendingUpdate,
      }}
    >
      {children}
    </CustomPromptStateContext.Provider>
  );
};
