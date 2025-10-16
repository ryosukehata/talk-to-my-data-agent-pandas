// Template Selection Button Component

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faWandMagicSparkles } from '@fortawesome/free-solid-svg-icons/faWandMagicSparkles';
import { useTranslation } from '@/i18n';
import { cn } from '@/lib/utils';
import type { PromptTemplate } from '@/api/templates/types';
import { TemplateSelector } from './TemplateSelector';

interface TemplateButtonProps {
  onSelectTemplate: (template: PromptTemplate) => void;
  onSendDirectly?: (message: string) => void;
  mode?: 'select' | 'send';
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
  disabled?: boolean;
  showIcon?: boolean;
  testId?: string;
}

export const TemplateButton = ({
  onSelectTemplate,
  onSendDirectly,
  mode = 'select',
  variant = 'outline',
  size = 'sm',
  className = '',
  disabled = false,
  showIcon = true,
  testId = 'template-button',
}: TemplateButtonProps) => {
  const { t } = useTranslation();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleSelectTemplate = (template: PromptTemplate) => {
    try {
      onSelectTemplate(template);
      setIsModalOpen(false);
    } catch (error) {
      console.error('Error selecting template:', error);
    }
  };

  const handleSendDirectly = (message: string) => {
    try {
      if (onSendDirectly) {
        onSendDirectly(message);
        setIsModalOpen(false);
      }
    } catch (error) {
      console.error('Error sending template directly:', error);
    }
  };

  const handleOpenModal = () => {
    try {
      setIsModalOpen(true);
    } catch (error) {
      console.error('Error opening template modal:', error);
    }
  };

  return (
    <>
      <Button
        variant={variant}
        size={size}
        className={cn('gap-2', className)}
        onClick={handleOpenModal}
        disabled={disabled}
        data-testid={testId}
      >
        {showIcon && <FontAwesomeIcon icon={faWandMagicSparkles} />}
        {mode === 'send' ? t('Quick Ask') : t('Select Template')}
      </Button>

      <TemplateSelector
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        onSelectTemplate={handleSelectTemplate}
        onSendDirectly={handleSendDirectly}
        mode={mode}
      />
    </>
  );
};
