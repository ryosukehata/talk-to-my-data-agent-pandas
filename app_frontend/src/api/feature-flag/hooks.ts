/**
 * Feature flags hooks using React Query
 */

import { useQuery } from '@tanstack/react-query';
import { fetchFeatureFlags } from './api';
import { FeatureFlagsResponse } from './types';

export const FEATURE_FLAGS_QUERY_KEY = ['feature-flags'];

/**
 * Hook to fetch feature flags
 */
export const useFetchFeatureFlags = () => {
  return useQuery<FeatureFlagsResponse, Error>({
    queryKey: FEATURE_FLAGS_QUERY_KEY,
    queryFn: fetchFeatureFlags,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
    retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
};
