import { useContext } from "react";
import { CustomPromptStateContext } from "./context";

export const useCustomPromptState = () => {
  const context = useContext(CustomPromptStateContext);
  if (context === undefined) {
    throw new Error(
      "useCustomPromptState must be used within a CustomPromptStateProvider",
    );
  }
  return context;
};
