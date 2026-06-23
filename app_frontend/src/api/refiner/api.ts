/**
 * Question Refiner API functions
 */

import apiClient from "@/api/apiClient";
import { RefineQuestionsRequest, RefineQuestionsResponse } from "./types";

/**
 * Refine user questions based on dataset context
 *
 * @param request - The refine questions request
 * @returns Promise with refined questions response
 */
export const refineQuestions = async (
  request: RefineQuestionsRequest,
): Promise<RefineQuestionsResponse> => {
  const response = await apiClient.post("/v1/refiner", request);
  return response.data;
};
