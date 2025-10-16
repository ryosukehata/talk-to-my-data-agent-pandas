import { useLayoutEffect, useState } from 'react';
import { Toaster } from '@/components/ui/sonner';
import './App.css';
import Pages from './pages';
import { useDataRobotInfo } from './api/user/hooks';
import { useAppState } from '@/state/hooks';
import i18n, { getSavedLanguage } from './i18n';
import { CustomPromptStateProvider } from '@/components/custom-prompts';

function App() {
  const { data: dataRobotInfo } = useDataRobotInfo();
  const { theme } = useAppState();
  const [isReady, setIsReady] = useState(false);

  useLayoutEffect(() => {
    if (dataRobotInfo?.datarobot_account_info?.language && !getSavedLanguage()) {
      i18n.changeLanguage(dataRobotInfo.datarobot_account_info.language as string);
    }
    if (dataRobotInfo) {
      setIsReady(true);
    }
  }, [dataRobotInfo]);

  // Apply theme class to document element
  useLayoutEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  return (
    <CustomPromptStateProvider>
      {isReady && <Pages />}
      <Toaster />
    </CustomPromptStateProvider>
  );
}

export default App;
