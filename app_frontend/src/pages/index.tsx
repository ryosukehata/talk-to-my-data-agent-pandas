import { Route, Routes, Navigate } from "react-router-dom";
import { ROUTES } from "./routes";
import { Suspense, lazy } from "react";
import { useTranslation } from "@/i18n";
import { Layout } from "./Layout";
import { useFetchFeatureFlags } from "@/api/feature-flag";

const Data = lazy(() =>
  import("./Data").then((module) => ({ default: module.Data })),
);
const Chats = lazy(() =>
  import("./Chats").then((module) => ({ default: module.Chats })),
);
const Reports = lazy(() =>
  import("./Reports").then((module) => ({ default: module.Reports })),
);

const Loading = () => {
  const { t } = useTranslation();
  return (
    <div className="flex h-full items-center justify-center">
      {t("Loading...")}
    </div>
  );
};

const FeatureFlaggedReports = () => {
  const { data: featureFlags, isLoading } = useFetchFeatureFlags();

  if (isLoading) {
    return <Loading />;
  }

  if (featureFlags?.reportBuilderEnabled !== true) {
    return <Navigate to={ROUTES.DATA} replace />;
  }

  return <Reports />;
};

const Pages = () => {
  return (
    <div className="size-full overflow-y-auto">
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to={ROUTES.DATA} replace />} />
            <Route path={ROUTES.DATA} element={<Data />} />
            <Route path={ROUTES.CHATS} element={<Chats />} />
            <Route path={ROUTES.CHAT_WITH_ID} element={<Chats />} />
            <Route path={ROUTES.DATA_WITH_ID} element={<Data />} />
            <Route path={ROUTES.REPORTS} element={<FeatureFlaggedReports />} />
            <Route
              path={ROUTES.REPORT_WITH_ID}
              element={<FeatureFlaggedReports />}
            />
            <Route path="*" element={<Navigate to={ROUTES.DATA} replace />} />
          </Route>
        </Routes>
      </Suspense>
    </div>
  );
};

export default Pages;
