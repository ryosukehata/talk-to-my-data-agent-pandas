/**
 * Question Refiner API types
 */

/**
 * A refined question with reasoning and relevant columns
 */
export interface RefinedQuestion {
  original_direction: string;
  refined_question: string;
  reasoning: string;
  relevant_columns: string[];
}

/**
 * Request payload for refining questions
 */
export interface RefineQuestionsRequest {
  user_direction: string;
  data_source?: string;
}

/**
 * Response from the refine questions API
 */
export interface RefineQuestionsResponse {
  success: boolean;
  refined_questions: RefinedQuestion[];
  error: string | null;
}
