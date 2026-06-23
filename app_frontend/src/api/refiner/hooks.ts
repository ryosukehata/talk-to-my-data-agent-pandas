/**
 * Question Refiner hooks using React Query
 */

import { useMutation, UseMutationOptions } from "@tanstack/react-query";
import { refineQuestions } from "./api";
import { RefineQuestionsRequest, RefineQuestionsResponse } from "./types";

export const REFINER_QUERY_KEY = ["refiner"];

/**
 * Hook to refine questions using the refiner API
 *
 * This is a mutation hook since refining questions is a POST operation
 * that may have side effects and shouldn't be cached like a query.
 *
 * @example
 * ```tsx
 * const { mutate: refine, isPending, data } = useRefineQuestions();
 *
 * const handleRefine = () => {
 *   refine({
 *     user_direction: "売上の傾向を分析したい",
 *     data_source: "file"
 *   });
 * };
 * ```
 */
export const useRefineQuestions = (
  options?: UseMutationOptions<
    RefineQuestionsResponse,
    Error,
    RefineQuestionsRequest
  >,
) => {
  return useMutation<RefineQuestionsResponse, Error, RefineQuestionsRequest>({
    mutationFn: refineQuestions,
    ...options,
  });
};
