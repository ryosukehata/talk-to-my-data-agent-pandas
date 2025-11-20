import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createCustomPrompt,
  getCustomPrompts,
  getCustomPromptByName,
  deleteCustomPrompt,
  getCustomPromptNames,
} from './api-requests';
import { customPromptsKeys } from './keys';
import { CustomPromptResponse } from './types';

// ローカルストレージにキャッシュするためのキー
const CUSTOM_PROMPTS_CACHE_KEY = 'custom_prompts_cache';

// キャッシュヘルパー関数
const saveToCache = (data: CustomPromptResponse[]) => {
  try {
    localStorage.setItem(
      CUSTOM_PROMPTS_CACHE_KEY,
      JSON.stringify({
        data,
        timestamp: Date.now(),
      })
    );
  } catch (error) {
    console.warn('Failed to save custom prompts to cache:', error);
  }
};

const getFromCache = (): CustomPromptResponse[] | null => {
  try {
    const cached = localStorage.getItem(CUSTOM_PROMPTS_CACHE_KEY);
    if (cached) {
      const { data } = JSON.parse(cached);
      return data;
    }
  } catch (error) {
    console.warn('Failed to load custom prompts from cache:', error);
  }
  return null;
};

export const useCreateCustomPrompt = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createCustomPrompt,
    onSuccess: () => {
      // キャッシュを無効化して最新データを取得
      queryClient.invalidateQueries({ queryKey: customPromptsKeys.all });
    },
  });
};

export const useFetchCustomPrompts = (options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: customPromptsKeys.lists(),
    queryFn: async () => {
      try {
        const result = await getCustomPrompts();
        // 成功時はキャッシュに保存
        saveToCache(result.custom_prompts);
        return result;
      } catch (error) {
        console.warn('Failed to fetch custom prompts, trying cache fallback:', error);
        // エラー時はキャッシュからフォールバック
        const cachedData = getFromCache();
        if (cachedData) {
          console.log('Using cached custom prompts data');
          return { custom_prompts: cachedData };
        }
        // キャッシュもない場合は空のリストを返す
        console.log('No cache available, returning empty list');
        return { custom_prompts: [] };
      }
    },
    retry: false, // エラー時の自動リトライを無効化してキャッシュフォールバックを優先
    staleTime: 30000, // 30秒間はデータを新鮮とみなす
    enabled: options?.enabled !== false, // デフォルトは有効、明示的にfalseの場合のみ無効
  });
};

export const useFetchCustomPromptByName = (name: string) => {
  return useQuery({
    queryKey: customPromptsKeys.detail(name),
    queryFn: () => getCustomPromptByName(name),
    enabled: !!name,
  });
};

export const useDeleteCustomPrompt = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteCustomPrompt,
    onSuccess: () => {
      // キャッシュを無効化して最新データを取得
      queryClient.invalidateQueries({ queryKey: customPromptsKeys.all });

      // ローカルストレージのキャッシュも更新
      const cached = getFromCache();
      if (cached) {
        // 削除されたアイテムを除いた新しいキャッシュを保存
        // 実際の削除されたアイテム名は onMutate で取得できますが、
        // ここでは簡単にキャッシュをクリアして次回フェッチ時に更新されるようにします
        localStorage.removeItem(CUSTOM_PROMPTS_CACHE_KEY);
      }
    },
  });
};

export const useFetchCustomPromptNames = () => {
  return useQuery({
    queryKey: customPromptsKeys.names(),
    queryFn: getCustomPromptNames,
  });
};
