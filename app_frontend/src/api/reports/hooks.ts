/**
 * Report Builder hooks using React Query
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from '@tanstack/react-query';
import {
  listReports,
  getReport,
  createReport,
  updateQuestion,
  updateQuestionStatus,
  executeQuestions,
  generateWord,
  deleteReport,
  downloadWord,
} from './api';
import {
  CreateReportRequest,
  CreateReportResponse,
  ListReportsResponse,
  ReportDetailResponse,
  ExecuteQuestionsResponse,
  GenerateWordResponse,
  ReportSummary,
  UpdateQuestionRequest,
  UpdateQuestionResponse,
  QuestionStatus,
} from './types';

export const REPORTS_QUERY_KEY = ['reports'];

/**
 * Hook to fetch all reports
 */
export const useReports = <T = ListReportsResponse>(
  options?: Omit<UseQueryOptions<ListReportsResponse, Error, T>, 'queryKey' | 'queryFn'>
) => {
  return useQuery<ListReportsResponse, Error, T>({
    queryKey: REPORTS_QUERY_KEY,
    queryFn: listReports,
    ...options,
  });
};

/**
 * Hook to fetch a single report by ID
 */
export const useReport = (
  reportId: string,
  options?: Omit<UseQueryOptions<ReportDetailResponse, Error>, 'queryKey' | 'queryFn'>
) => {
  return useQuery<ReportDetailResponse, Error>({
    queryKey: [...REPORTS_QUERY_KEY, reportId],
    queryFn: () => getReport(reportId),
    enabled: !!reportId,
    ...options,
  });
};

/**
 * Hook to create a new report
 */
export const useCreateReport = (
  options?: UseMutationOptions<CreateReportResponse, Error, CreateReportRequest>
) => {
  const queryClient = useQueryClient();

  return useMutation<CreateReportResponse, Error, CreateReportRequest>({
    mutationFn: createReport,
    onSuccess: () => {
      // Invalidate reports list to refetch
      queryClient.invalidateQueries({ queryKey: REPORTS_QUERY_KEY });
    },
    ...options,
  });
};

/**
 * Hook to update a question's refined_question
 */
export const useUpdateQuestion = (
  options?: UseMutationOptions<
    UpdateQuestionResponse,
    Error,
    { reportId: string; questionId: string; request: UpdateQuestionRequest }
  >
) => {
  const queryClient = useQueryClient();

  return useMutation<
    UpdateQuestionResponse,
    Error,
    { reportId: string; questionId: string; request: UpdateQuestionRequest }
  >({
    mutationFn: ({ reportId, questionId, request }) =>
      updateQuestion(reportId, questionId, request),
    onSuccess: (_, variables) => {
      // Invalidate specific report to refetch
      queryClient.invalidateQueries({ queryKey: [...REPORTS_QUERY_KEY, variables.reportId] });
    },
    ...options,
  });
};

/**
 * Hook to execute questions in a report
 */
export const useExecuteQuestions = (
  options?: UseMutationOptions<ExecuteQuestionsResponse, Error, string>
) => {
  const queryClient = useQueryClient();

  return useMutation<ExecuteQuestionsResponse, Error, string>({
    mutationFn: executeQuestions,
    onSuccess: (_, reportId) => {
      // Invalidate specific report to refetch
      queryClient.invalidateQueries({ queryKey: [...REPORTS_QUERY_KEY, reportId] });
      queryClient.invalidateQueries({ queryKey: REPORTS_QUERY_KEY });
    },
    ...options,
  });
};

/**
 * Hook to generate Word document
 */
export const useGenerateWord = (
  options?: UseMutationOptions<GenerateWordResponse, Error, string>
) => {
  const queryClient = useQueryClient();

  return useMutation<GenerateWordResponse, Error, string>({
    mutationFn: generateWord,
    onSuccess: (_, reportId) => {
      queryClient.invalidateQueries({ queryKey: [...REPORTS_QUERY_KEY, reportId] });
      queryClient.invalidateQueries({ queryKey: REPORTS_QUERY_KEY });
    },
    ...options,
  });
};

export const useDownloadWord = (options?: UseMutationOptions<void, Error, string>) => {
  return useMutation<void, Error, string>({
    mutationFn: downloadWord,
    ...options,
  });
};

/**
 * Hook to delete a report
 */
export const useDeleteReport = (options?: UseMutationOptions<void, Error, string>) => {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: deleteReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REPORTS_QUERY_KEY });
    },
    ...options,
  });
};

/**
 * Transform reports response to sidebar menu format
 */
export const getReportsMenu = (data: ListReportsResponse): ReportSummary[] => {
  return data.reports;
};

export const useUpdateQuestionStatus = (
  options?: UseMutationOptions<
    UpdateQuestionResponse,
    Error,
    { reportId: string; questionId: string; status: QuestionStatus }
  >
) => {
  const queryClient = useQueryClient();

  return useMutation<
    UpdateQuestionResponse,
    Error,
    { reportId: string; questionId: string; status: QuestionStatus }
  >({
    mutationFn: ({ reportId, questionId, status }) =>
      updateQuestionStatus(reportId, questionId, status),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [...REPORTS_QUERY_KEY, variables.reportId] });
    },
    ...options,
  });
};
