/**
 * Feature flags types
 */

export interface FeatureFlags {
  templateEditEnabled: boolean;
  customPromptsEnabled: boolean;
  refinerEnabled: boolean;
  refinerAutoSend: boolean;
  // Add more feature flags here as needed
}

export interface FeatureFlagsResponse {
  templateEditEnabled: boolean;
  customPromptsEnabled: boolean;
  refinerEnabled: boolean;
  refinerAutoSend: boolean;
}
