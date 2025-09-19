import { Sidebar } from '@/components/Sidebar';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { Outlet } from 'react-router-dom';

export const Layout = () => {
  return (
    <div className="h-screen">
      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel defaultSize={20} minSize={20} maxSize={30}>
          <Sidebar />
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={80}>
          <Outlet />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
};
