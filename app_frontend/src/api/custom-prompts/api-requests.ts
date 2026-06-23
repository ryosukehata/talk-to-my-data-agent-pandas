import apiClient from "@/api/apiClient";
import {
  CustomPromptCreate,
  CustomPromptResponse,
  CustomPromptDelete,
} from "./types";

export const createCustomPrompt = async (
  promptData: CustomPromptCreate,
): Promise<{ message: string }> => {
  const response = await apiClient.post("/v1/custom-prompts", promptData);
  return response.data;
};

export const getCustomPrompts = async (): Promise<{
  custom_prompts: CustomPromptResponse[];
}> => {
  try {
    console.log("Fetching custom prompts from:", "/v1/custom-prompts");
    const response = await apiClient.get("/v1/custom-prompts");
    console.log("Custom prompts response:", response.data);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch custom prompts:", error);
    if (error && typeof error === "object" && "response" in error) {
      const axiosError = error as {
        response?: { status?: number; data?: unknown };
      };
      console.error("Response status:", axiosError.response?.status);
      console.error("Response data:", axiosError.response?.data);
    }
    throw error;
  }
};

export const getCustomPromptByName = async (
  name: string,
): Promise<CustomPromptResponse> => {
  const response = await apiClient.get(
    `/v1/custom-prompts/${encodeURIComponent(name)}`,
  );
  return response.data;
};

export const deleteCustomPrompt = async (
  promptData: CustomPromptDelete,
): Promise<{ message: string }> => {
  const response = await apiClient.delete("/v1/custom-prompts", {
    data: promptData,
  });
  return response.data;
};

export const getCustomPromptNames = async (): Promise<{
  prompt_names: string[];
}> => {
  const response = await apiClient.get("/v1/custom-prompts-names");
  return response.data;
};
