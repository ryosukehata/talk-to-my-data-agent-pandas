/**
 * Report Builder API functions
 */

import apiClient from '@/api/apiClient';
import {
  CreateReportRequest,
  CreateReportResponse,
  ListReportsResponse,
  ReportDetailResponse,
  ExecuteQuestionsResponse,
  GenerateWordResponse,
  UpdateQuestionRequest,
  UpdateQuestionResponse,
  QuestionStatus,
} from './types';

/**
 * List all reports for the current user
 */
export const listReports = async (): Promise<ListReportsResponse> => {
  const response = await apiClient.get('/v1/reports');
  return response.data;
};

/**
 * Get a specific report by ID
 */
export const getReport = async (reportId: string): Promise<ReportDetailResponse> => {
  const response = await apiClient.get(`/v1/reports/${reportId}`);
  return response.data;
};

/**
 * Create a new report with auto-generated questions
 */
export const createReport = async (
  request: CreateReportRequest
): Promise<CreateReportResponse> => {
  const response = await apiClient.post('/v1/reports', request);
  return response.data;
};

/**
 * Update a question's refined_question field
 */
export const updateQuestion = async (
  reportId: string,
  questionId: string,
  request: UpdateQuestionRequest
): Promise<UpdateQuestionResponse> => {
  const response = await apiClient.patch(
    `/v1/reports/${reportId}/questions/${questionId}`,
    request
  );
  return response.data;
};

export const updateQuestionStatus = async (
  reportId: string,
  questionId: string,
  status: QuestionStatus
): Promise<UpdateQuestionResponse> => {
  const response = await apiClient.patch(
    `/v1/reports/${reportId}/questions/${questionId}`,
    { status }
  );
  return response.data;
};

/**
 * Execute all questions in a report (start chat generation)
 */
export const executeQuestions = async (
  reportId: string
): Promise<ExecuteQuestionsResponse> => {
  const response = await apiClient.post(`/v1/reports/${reportId}/execute`);
  return response.data;
};

/**
 * Generate Word document for a completed report
 */
export const generateWord = async (
  reportId: string
): Promise<GenerateWordResponse> => {
  const response = await apiClient.post(`/v1/reports/${reportId}/generate-word`);
  return response.data;
};

export const getReportSummary = async (
  reportId: string
): Promise<ReportDetailResponse> => {
  const response = await apiClient.get(`/v1/reports/${reportId}`);
  return response.data;
};

export const downloadWord = async (reportId: string): Promise<void> => {
  const response = await apiClient.get(`/v1/reports/${reportId}/download`, {
    responseType: 'blob',
  });

  if (response.status !== 200) {
    throw new Error('Failed to download Word document');
  }

  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `report_${reportId}.docx`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

/**
 * Delete a report
 */
export const deleteReport = async (reportId: string): Promise<void> => {
  await apiClient.delete(`/v1/reports/${reportId}`);
};
