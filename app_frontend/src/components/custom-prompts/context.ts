import { createContext } from 'react';

export interface CustomPromptStateContextType {
  isSaving: boolean;
  setSaving: (saving: boolean) => void;
  pendingUpdate: boolean;
  setPendingUpdate: (pending: boolean) => void;
}

export const CustomPromptStateContext = createContext<CustomPromptStateContextType | undefined>(
  undefined
);
