/**
 * Template reload hooks
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { reloadTemplates } from './reload';
import { templateQueryKeys } from './hooks';
import { customPromptsKeys } from '../custom-prompts/keys';

export const useReloadTemplates = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: reloadTemplates,
    onSuccess: data => {
      console.log('Templates reloaded successfully:', data);

      // すべてのテンプレート関連キャッシュを無効化
      queryClient.invalidateQueries({
        queryKey: templateQueryKeys.all,
      });

      // カスタムプロンプト関連のキャッシュも無効化
      queryClient.invalidateQueries({
        queryKey: customPromptsKeys.all,
      });

      console.log('Template and custom prompt caches invalidated');
    },
    onError: error => {
      console.error('Failed to reload templates:', error);
    },
  });
};
