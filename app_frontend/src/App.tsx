import { useLayoutEffect, useState } from 'react';
import { Toaster } from '@/components/ui/sonner';
import './App.css';
import Pages from './pages';
import { useDataRobotInfo } from './api/user/hooks';
import i18n, { getSavedLanguage } from './i18n';
import { CustomPromptStateProvider } from '@/components/custom-prompts';
import { ThemeProvider } from './theme/theme-provider';

function App() {
  const { data: dataRobotInfo } = useDataRobotInfo();
  const [isReady, setIsReady] = useState(false);

  useLayoutEffect(() => {
    if (dataRobotInfo?.datarobot_account_info?.language && !getSavedLanguage()) {
      i18n.changeLanguage(dataRobotInfo.datarobot_account_info.language as string);
    }
    if (dataRobotInfo) {
      setIsReady(true);
    }
  }, [dataRobotInfo]);

  return (
    <ThemeProvider>
      <CustomPromptStateProvider>
        <div className="h-screen">
          {isReady && <Pages />}
          <Toaster />
        </div>
      </CustomPromptStateProvider>
    </ThemeProvider>
  );
}

export default App;
