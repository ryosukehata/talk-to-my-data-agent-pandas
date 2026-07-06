/**
 * Feature flags API functions
 */

import apiClient from "@/api/apiClient";
import { FeatureFlagsResponse } from "./types";

/**
 * Fetch feature flags from the backend
 */
export const fetchFeatureFlags = async (): Promise<FeatureFlagsResponse> => {
  const response = await apiClient.get("/v1/config/feature-flags");
  return response.data;
};
