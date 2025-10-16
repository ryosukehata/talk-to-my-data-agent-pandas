export interface SavePromptData {
  name: string;
  description?: string;
  prompt_text_template: string;
}

export interface SavePromptButtonProps {
  promptText: string;
  onSave?: (data: SavePromptData) => void;
  disabled?: boolean;
}

export interface SavePromptModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: SavePromptData) => void;
  initialPromptText: string;
}
