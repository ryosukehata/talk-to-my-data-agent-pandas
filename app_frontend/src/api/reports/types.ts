/**
 * Report Builder API types
 */

/**
 * Report status enum
 */
export type ReportStatus =
  | 'pending'
  | 'refining'
  | 'chat_processing'
  | 'completed'
  | 'generating_word'
  | 'done'
  | 'error';

/**
 * Question status enum
 */
export type QuestionStatus = 'pending' | 'refining' | 'ready' | 'running' | 'completed' | 'error';

/**
 * A question in a report
 */
export interface ReportQuestion {
  question_id: string;
  original_direction: string;
  refined_question: string;
  refine_status?: QuestionStatus;
  status: QuestionStatus;
  chat_id?: string | null;
  message_id?: string | null;
  executed_at?: string | null;
  error_message?: string | null;
}

/**
 * Report summary for list view
 */
export interface ReportSummary {
  report_id: string;
  title: string;
  status: ReportStatus;
  progress: number;
  created_at: string;
  updated_at: string;
  word_file_path?: string | null;
}

/**
 * Full report detail
 */
export interface Report {
  report_id: string;
  user_id: string;
  title: string;
  theme: string;
  data_source: string;
  status: ReportStatus;
  questions: ReportQuestion[];
  created_at: string;
  updated_at: string;
  error_message?: string | null;
  word_file_path?: string | null;
}

/**
 * Request to create a new report
 */
export interface CreateReportRequest {
  theme: string;
  data_source: string;
  num_questions?: number;
}

/**
 * Response from creating a report
 */
export interface CreateReportResponse {
  report_id: string;
  message: string;
}

/**
 * Response from listing reports
 */
export interface ListReportsResponse {
  reports: ReportSummary[];
  total: number;
}

/**
 * Response from getting report detail
 */
export interface ReportDetailResponse {
  report: Report;
}

/**
 * Request to update a question
 */
export interface UpdateQuestionRequest {
  refined_question?: string;
  status?: QuestionStatus;
  refine_status?: QuestionStatus;
}

/**
 * Response from updating a question
 */
export interface UpdateQuestionResponse {
  success: boolean;
  question_id: string;
  message: string;
}

/**
 * Response from executing questions
 */
export interface ExecuteQuestionsResponse {
  report_id: string;
  status: ReportStatus;
  message: string;
}

/**
 * Response from generating Word document
 */
export interface GenerateWordResponse {
  report_id: string;
  status: ReportStatus;
  message: string;
}
