import React from 'react';

interface MessageContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  testId?: string;
}

export const MessageContainer = React.memo(
  React.forwardRef<HTMLDivElement, MessageContainerProps>(({ children, testId, ...props }, ref) => {
    return (
      <div
<<<<<<< HEAD
        className="p-3 bg-card rounded flex-col justify-start items-start gap-3 flex mb-8 mr-2"
=======
        className="p-3 bg-card rounded flex-col justify-start items-start gap-3 flex mb-8 mr-2 min-w-0"
>>>>>>> upstream/main
        data-testid={testId}
        ref={ref}
        {...props}
      >
        {children}
      </div>
    );
  })
);
