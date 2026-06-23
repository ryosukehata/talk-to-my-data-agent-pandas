// global.d.ts

export {};

declare global {
  interface Window {
    ENV: {
      APP_BASE_URL?: string;
      BASE_PATH?: string;
      API_PORT?: string;
      APP_VERSION?: string;
      DATAROBOT_ENDPOINT?: string;
      IS_STATIC_FRONTEND?: boolean;
    };
  }
}
