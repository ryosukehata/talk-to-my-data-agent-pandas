/**
 * Reports Page - Report Builder
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { isAxiosError } from "axios";
import { useTranslation } from "@/i18n";
import {
  useReports,
  useReport,
  useCreateReport,
  useExecuteQuestions,
  useDeleteReport,
  useUpdateQuestion,
  useUpdateQuestionStatus,
  useGenerateWord,
  useDownloadWord,
} from "@/api/reports";
import { ReportStatus, QuestionStatus, Report } from "@/api/reports/types";
import { refineQuestions } from "@/api/refiner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft,
  Check,
  CircleCheck,
  Clock,
  Download,
  Loader2,
  Play,
  Plus,
  Trash2,
  TriangleAlert,
  WandSparkles,
  type LucideIcon,
} from "lucide-react";
import loader from "@/assets/loader.svg";
import { useAppState } from "@/state/hooks";

type ApiErrorResponse = {
  detail?: unknown;
};

const getReportErrorMessage = (error: unknown, fallback: string): string => {
  if (isAxiosError<ApiErrorResponse>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (detail && typeof detail === "object" && "message" in detail) {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string" && message.trim()) {
        return message;
      }
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
};

// Status badge component
const StatusBadge = ({ status }: { status: ReportStatus | QuestionStatus }) => {
  const { t } = useTranslation();

  const getStatusConfig = (): {
    type?: "default" | "outline";
    variant: "default" | "destructive" | "info" | "warning" | "success";
    icon: LucideIcon;
    label: string;
  } => {
    switch (status) {
      case "completed":
      case "done":
        return { variant: "success", icon: Check, label: t("Completed") };
      case "generating_word":
        return {
          variant: "info",
          icon: Loader2,
          label: t("Generating Word"),
        };
      case "refining":
        return { variant: "info", icon: Loader2, label: t("Refining") };
      case "chat_processing":
      case "running":
        return { variant: "info", icon: Loader2, label: t("Processing") };
      case "error":
        return {
          variant: "destructive",
          icon: TriangleAlert,
          label: t("Error"),
        };
      case "ready":
        return { variant: "success", icon: CircleCheck, label: t("Ready") };
      case "pending":
      default:
        return {
          type: "outline",
          variant: "default",
          icon: Clock,
          label: t("Pending"),
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <Badge type={config.type} variant={config.variant} className="gap-1">
      <Icon
        className={[
          "size-4",
          [
            "refining",
            "chat_processing",
            "running",
            "generating_word",
          ].includes(status as string)
            ? "animate-spin"
            : "",
        ]
          .filter(Boolean)
          .join(" ")}
      />
      {config.label}
    </Badge>
  );
};

// Create Report Form
const CreateReportForm = ({
  onSuccess,
}: {
  onSuccess: (reportId: string) => void;
}) => {
  const { t } = useTranslation();
  const { dataSource } = useAppState();
  const [theme, setTheme] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { mutate: createReport } = useCreateReport({
    onSuccess: (data) => {
      setTheme("");
      setIsCreating(false);
      setErrorMessage(null);
      onSuccess(data.report_id);
    },
    onError: (error) => {
      setIsCreating(false);
      setErrorMessage(
        getReportErrorMessage(error, t("Failed to create report")),
      );
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (theme.trim()) {
      setIsCreating(true);
      setErrorMessage(null);
      createReport({
        theme: theme.trim(),
        data_source: dataSource,
        num_questions: 3 /** 後で直す */,
      });
    }
  };

  // Show full-screen loading when creating
  if (isCreating) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center space-y-4 py-12">
            <Loader2 className="size-8 animate-spin text-primary" />
            <div className="text-center">
              <p className="text-lg font-medium">
                {t("Generating questions...")}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {t(
                  "AI is analyzing your data and creating analysis questions.",
                )}
              </p>
              <p className="text-sm text-muted-foreground">
                {t("This may take a few seconds.")}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("Create New Report")}</CardTitle>
        <CardDescription>
          {t(
            "Enter a theme and we will generate analysis questions automatically",
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="theme">{t("Report Theme")}</Label>
            <Input
              id="theme"
              placeholder={t(
                "e.g., Analyze sales trends and predict next month",
              )}
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              disabled={isCreating}
            />
          </div>
          <Button type="submit" disabled={isCreating || !theme.trim()}>
            <Plus className="mr-2 size-4" />
            {t("Create Report")}
          </Button>
          {errorMessage && (
            <p className="text-sm text-destructive">{errorMessage}</p>
          )}
        </form>
      </CardContent>
    </Card>
  );
};

// Report Detail View
const ReportDetail = ({ reportId }: { reportId: string }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { dataSource } = useAppState();
  const [refiningQuestionIds, setRefiningQuestionIds] = useState<Set<string>>(
    new Set(),
  );
  const { data, isLoading, refetch } = useReport(reportId, {
    refetchInterval: (query) => {
      // Auto-refetch while processing
      const report = query.state.data?.report;
      if (!report) return false;

      // Check if processing
      if (["chat_processing", "generating_word"].includes(report.status))
        return 3000;

      return false;
    },
  });
  const { mutate: executeQuestions, isPending: isExecuting } =
    useExecuteQuestions({
      onSuccess: () => {
        refetch();
      },
    });
  const { mutate: deleteReport, isPending: isDeleting } = useDeleteReport({
    onSuccess: () => {
      navigate("/reports");
    },
  });
  const { mutateAsync: updateQuestion } = useUpdateQuestion();
  const { mutateAsync: updateQuestionStatus } = useUpdateQuestionStatus();
  const { mutate: generateWord, isPending: isGeneratingWord } = useGenerateWord(
    {
      onSuccess: () => {
        refetch();
      },
    },
  );
  const { mutate: downloadWord, isPending: isDownloadingWord } =
    useDownloadWord();

  // Refine a single question
  const refineQuestion = useCallback(
    async (questionId: string, direction: string): Promise<boolean> => {
      setRefiningQuestionIds((prev) => new Set(prev).add(questionId));
      await updateQuestionStatus({ reportId, questionId, status: "refining" });
      try {
        const result = await refineQuestions({
          user_direction: direction,
          data_source: dataSource,
        });

        if (result.success && result.refined_questions.length > 0) {
          await updateQuestion({
            reportId,
            questionId,
            request: {
              refined_question: result.refined_questions[0].refined_question,
              error_message: null,
            },
          });
          await updateQuestionStatus({ reportId, questionId, status: "ready" });
          refetch();
          return true;
        }

        throw new Error(result.error || t("Failed to refine question"));
      } catch (error) {
        console.error("Failed to refine question:", error);
        const message = getReportErrorMessage(
          error,
          t("Failed to refine question"),
        );
        await updateQuestion({
          reportId,
          questionId,
          request: { status: "error", error_message: message },
        });
        refetch();
        return false;
      } finally {
        setRefiningQuestionIds((prev) => {
          const next = new Set(prev);
          next.delete(questionId);
          return next;
        });
      }
    },
    [dataSource, reportId, t, updateQuestion, updateQuestionStatus, refetch],
  );

  // Refine all unrefined questions sequentially to avoid rate limiting, then auto-execute
  const refineAllQuestions = useCallback(
    async (report: Report, autoExecuteAfter: boolean = false) => {
      const unrefinedQuestions = report.questions.filter(
        (q) =>
          !q.refined_question || q.refined_question === q.original_direction,
      );

      console.log(
        `🔄 Starting refine for ${unrefinedQuestions.length} questions, autoExecuteAfter=${autoExecuteAfter}`,
      );

      // Run refinements sequentially to avoid overwhelming the LLM API
      // (Parallel requests can cause rate limiting or timeout issues)
      let allRefinementsSucceeded = true;
      for (const question of unrefinedQuestions) {
        try {
          console.log(`🔄 Refining question ${question.question_id}...`);
          const success = await refineQuestion(
            question.question_id,
            question.original_direction,
          );
          if (success) {
            console.log(`✅ Refined question ${question.question_id}`);
          } else {
            allRefinementsSucceeded = false;
            console.error(
              `❌ Failed to refine question ${question.question_id}`,
            );
          }
        } catch (error) {
          allRefinementsSucceeded = false;
          console.error(
            `❌ Failed to refine question ${question.question_id}:`,
            error,
          );
          // Continue with next question even if one fails
        }
      }

      console.log(`🏁 All refinements complete`);

      // After all refinements complete, auto-execute if requested
      if (autoExecuteAfter && allRefinementsSucceeded) {
        console.log(`🚀 Auto-executing questions for report ${reportId}`);
        // Small delay to ensure state is updated
        setTimeout(() => {
          console.log(`🚀 Calling executeQuestions(${reportId})`);
          executeQuestions(reportId);
        }, 1000);
      }
    },
    [refineQuestion, executeQuestions, reportId],
  );

  // Auto-refine: automatically start refining when there are unrefined questions
  const autoRefineStarted = useRef<string | null>(null);
  useEffect(() => {
    if (!data?.report) return;
    if (autoRefineStarted.current === reportId) return;
    if (refiningQuestionIds.size > 0) return; // Already refining

    const report = data.report;
    const unrefinedQuestions = report.questions.filter(
      (q) => !q.refined_question || q.refined_question === q.original_direction,
    );

    if (
      unrefinedQuestions.length > 0 &&
      (["pending", "refining"].includes(report.status) ||
        report.status === "refining")
    ) {
      autoRefineStarted.current = reportId;
      // Auto-execute after refinement completes
      refineAllQuestions(report, true);
    }
  }, [data?.report, refiningQuestionIds.size, refineAllQuestions, reportId]);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <img src={loader} alt={t("Loading")} className="size-8 animate-spin" />
      </div>
    );
  }

  if (!data?.report) {
    return (
      <div className="text-center text-muted-foreground">
        {t("Report not found")}
      </div>
    );
  }

  const report = data.report;
  const hasUnrefinedQuestions = report.questions.some(
    (q) => !q.refined_question || q.refined_question === q.original_direction,
  );
  const canExecute =
    (["pending", "refining"].includes(report.status) ||
      report.status === "refining") &&
    report.questions.length > 0 &&
    !hasUnrefinedQuestions;
  const canGenerateWord =
    report.status === "completed" && !report.word_file_path;
  const isWordBeingGenerated =
    report.status === "generating_word" || isGeneratingWord;
  const progress =
    report.questions.length > 0
      ? (report.questions.filter((q) => q.status === "completed").length /
          report.questions.length) *
        100
      : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate("/reports")}
          >
            <ArrowLeft className="mr-2 size-4" />
            {t("Back")}
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{report.title}</h1>
            <p className="text-muted-foreground">{report.theme}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={report.status} />
          {hasUnrefinedQuestions &&
            (["pending", "refining"].includes(report.status) ||
              report.status === "refining") && (
              <Button
                variant="secondary"
                onClick={() => refineAllQuestions(report, true)}
                disabled={refiningQuestionIds.size > 0}
              >
                {refiningQuestionIds.size > 0 ? (
                  <Loader2 className="mr-2 size-4 animate-spin" />
                ) : (
                  <WandSparkles className="mr-2 size-4" />
                )}
                {t("Refine All")}
              </Button>
            )}
          {canExecute && (
            <Button
              onClick={() => executeQuestions(reportId)}
              disabled={isExecuting}
            >
              {isExecuting ? (
                <Loader2 className="mr-2 size-4 animate-spin" />
              ) : (
                <Play className="mr-2 size-4" />
              )}
              {t("Execute Questions")}
            </Button>
          )}
          {(canGenerateWord || report.status === "generating_word") &&
            !report.word_file_path && (
              <Button
                variant="secondary"
                onClick={() => generateWord(reportId)}
                disabled={isWordBeingGenerated}
              >
                {isWordBeingGenerated ? (
                  <Loader2 className="mr-2 size-4 animate-spin" />
                ) : (
                  <WandSparkles className="mr-2 size-4" />
                )}
                {isWordBeingGenerated
                  ? t("Generating Word")
                  : t("Generate Word")}
              </Button>
            )}
          {report.status === "done" && report.word_file_path && (
            <Button
              variant="secondary"
              onClick={() => downloadWord(reportId)}
              disabled={isDownloadingWord}
            >
              {isDownloadingWord ? (
                <Loader2 className="mr-2 size-4 animate-spin" />
              ) : (
                <Download className="mr-2 size-4" />
              )}
              {t("Download Word")}
            </Button>
          )}
          <Button
            variant="destructive"
            size="icon"
            onClick={() => {
              if (
                window.confirm(
                  t("Are you sure you want to delete this report?"),
                )
              ) {
                deleteReport(reportId);
              }
            }}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Trash2 />
            )}
          </Button>
        </div>
      </div>

      {/* Progress */}
      {report.status === "chat_processing" && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>{t("Executing questions...")}</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} />
            </div>
          </CardContent>
        </Card>
      )}

      {report.status === "generating_word" && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              <span>{t("Generating Word")}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Questions */}
      <Card className="flex max-h-[60vh] flex-col">
        <CardHeader className="flex-shrink-0">
          <CardTitle>
            {t("Questions")} ({report.questions.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-y-auto">
          <div className="space-y-4">
            {report.questions.map((question, index) => {
              const isRefiningThis = refiningQuestionIds.has(
                question.question_id,
              );
              const needsRefinement =
                !question.refined_question ||
                question.refined_question === question.original_direction;

              return (
                <div
                  key={question.question_id}
                  className="rounded-lg border p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="mb-2 flex items-center gap-2">
                        <span className="font-medium text-muted-foreground">
                          #{index + 1}
                        </span>
                        <StatusBadge status={question.status} />
                        {isRefiningThis && (
                          <Badge
                            type="outline"
                            variant="info"
                            className="gap-1"
                          >
                            <Loader2 className="size-4 animate-spin" />
                            {t("Refining...")}
                          </Badge>
                        )}
                        {!isRefiningThis && needsRefinement && (
                          <Badge variant="warning" className="gap-1">
                            {t("Not refined")}
                          </Badge>
                        )}
                        {!isRefiningThis &&
                          !needsRefinement &&
                          question.status === "pending" && (
                            <Badge variant="success" className="gap-1">
                              <CircleCheck className="size-4" />
                              {t("Refined")}
                            </Badge>
                          )}
                      </div>
                      <p className="mb-1 text-sm text-muted-foreground">
                        {t("Direction")}: {question.original_direction}
                      </p>
                      {!needsRefinement && (
                        <p className="font-medium">
                          {question.refined_question}
                        </p>
                      )}
                      {question.error_message && (
                        <p className="mt-2 text-sm text-destructive">
                          {t("Error")}: {question.error_message}
                        </p>
                      )}
                      {question.chat_id && (
                        <Button
                          variant="link"
                          className="mt-2 h-auto p-0"
                          onClick={() => navigate(`/chats/${question.chat_id}`)}
                        >
                          {t("View Chat Result")} →
                        </Button>
                      )}
                    </div>
                    {/* Refine button for individual question */}
                    {needsRefinement &&
                      (["pending", "refining"].includes(report.status) ||
                        report.status === "refining") && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            refineQuestion(
                              question.question_id,
                              question.original_direction,
                            )
                          }
                          disabled={isRefiningThis}
                        >
                          {isRefiningThis ? (
                            <Loader2 className="size-4 animate-spin" />
                          ) : (
                            <WandSparkles className="size-4" />
                          )}
                        </Button>
                      )}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {report.error_message && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">{report.error_message}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

// Report List View
const ReportList = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, isLoading } = useReports();
  const { mutate: generateWord, isPending: isGeneratingWord } =
    useGenerateWord();
  const { mutate: downloadWord, isPending: isDownloadingWord } =
    useDownloadWord();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <img src={loader} alt={t("Loading")} className="size-8 animate-spin" />
      </div>
    );
  }

  if (!data?.reports?.length) {
    return (
      <div className="py-8 text-center text-muted-foreground">
        {t("No reports yet. Create your first report above.")}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t("Your Reports")}</h2>
      <div className="grid gap-4">
        {data.reports.map((report) => (
          <Card key={report.report_id} className="transition-colors">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between gap-4">
                <button
                  type="button"
                  className="flex-1 text-left"
                  onClick={() => navigate(`/reports/${report.report_id}`)}
                >
                  <h3 className="font-medium">{report.title}</h3>
                  <p className="text-sm text-muted-foreground">
                    {new Date(report.created_at).toLocaleDateString()}
                  </p>
                </button>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">
                      {t("Progress")}
                    </p>
                    <p className="font-medium">
                      {Math.round(report.progress * 100)}%
                    </p>
                  </div>
                  <StatusBadge status={report.status} />
                  {(report.status === "completed" ||
                    report.status === "generating_word") &&
                    !report.word_file_path && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => generateWord(report.report_id)}
                        disabled={
                          isGeneratingWord ||
                          report.status === "generating_word"
                        }
                      >
                        {isGeneratingWord ||
                        report.status === "generating_word" ? (
                          <Loader2 className="mr-2 size-4 animate-spin" />
                        ) : (
                          <WandSparkles className="mr-2 size-4" />
                        )}
                        {isGeneratingWord || report.status === "generating_word"
                          ? t("Generating Word")
                          : t("Generate Word")}
                      </Button>
                    )}
                  {report.status === "done" && report.word_file_path && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => downloadWord(report.report_id)}
                      disabled={isDownloadingWord}
                    >
                      {isDownloadingWord ? (
                        <Loader2 className="mr-2 size-4 animate-spin" />
                      ) : (
                        <Download className="mr-2 size-4" />
                      )}
                      {t("Download Word")}
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

// Main Reports Page
export const Reports = () => {
  const { reportId } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [showCreateForm, setShowCreateForm] = useState(false);

  const handleReportCreated = (newReportId: string) => {
    setShowCreateForm(false);
    // Navigate to the new report to allow user to refine questions
    navigate(`/reports/${newReportId}`);
  };

  // If we have a reportId, show detail view
  if (reportId) {
    return (
      <div className="container mx-auto max-w-4xl px-4 py-6">
        <ReportDetail reportId={reportId} />
      </div>
    );
  }

  // Otherwise show list view
  return (
    <div className="container mx-auto max-w-4xl px-4 py-6">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">{t("Report Builder")}</h1>
          {!showCreateForm && (
            <Button onClick={() => setShowCreateForm(true)}>
              <Plus className="mr-2 size-4" />
              {t("New Report")}
            </Button>
          )}
        </div>

        {showCreateForm && (
          <>
            <CreateReportForm onSuccess={handleReportCreated} />
            <Button variant="ghost" onClick={() => setShowCreateForm(false)}>
              {t("Cancel")}
            </Button>
            <Separator />
          </>
        )}

        <ReportList />
      </div>
    </div>
  );
};
