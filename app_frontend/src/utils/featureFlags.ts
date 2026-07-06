/**
 * Environment variables utility functions
 *
 * Note: This file is now deprecated. Use the API-based feature flags instead:
 * import { useFetchFeatureFlags } from '@/api/feature-flag';
 */

/**
 * Check if template edit feature is enabled via environment variable
 * @returns true if template edit is enabled, false otherwise
 * @deprecated Use useFetchFeatureFlags hook instead
 */
export const isTemplateEditEnabled = (): boolean => {
  const envValue = import.meta.env.VITE_ENABLE_TEMPLATE_EDIT;

  // Default to true if not set (backwards compatibility)
  if (envValue === undefined || envValue === "") {
    return true;
  }

  // Convert string to boolean
  return envValue.toLowerCase() === "true" || envValue === "1";
};

/**
 * Get all feature flags from environment variables
 * @deprecated Use useFetchFeatureFlags hook instead
 */
export const getFeatureFlags = () => ({
  templateEditEnabled: isTemplateEditEnabled(),
});
