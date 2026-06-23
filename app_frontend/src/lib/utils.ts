import { VITE_DEFAULT_PORT } from "@/constants/dev";
import { useRef, useEffect, useCallback } from "react";
import { clsx, type ClassValue } from "clsx";

import { twMerge } from "tailwind-merge";

const trimSlashes = (value: string) => value.replace(/^\/+|\/+$/g, "");

const joinUrlPath = (origin: string, path?: string) => {
  if (!path) {
    return origin;
  }
  return `${origin}/${trimSlashes(path)}`;
};

export function getBaseUrl() {
  const runtimeBaseUrl = window.ENV?.APP_BASE_URL ?? window.ENV?.BASE_PATH;

  if (
    runtimeBaseUrl?.includes("notebook-sessions") &&
    window.ENV?.API_PORT &&
    isServedStatic()
  ) {
    return `${trimSlashes(runtimeBaseUrl)}/ports/${window.ENV.API_PORT}`;
  }

  return runtimeBaseUrl;
}

export function getApiUrl() {
  let apiBaseURL = joinUrlPath(window.location.origin, getBaseUrl());

  if (
    getBaseUrl()?.includes("notebook-sessions") &&
    isDev() &&
    !isServedStatic()
  ) {
    apiBaseURL += `/ports/${VITE_DEFAULT_PORT}`;
  }

  return `${apiBaseURL}/api`;
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function isDev() {
  return import.meta.env.MODE === "development";
}

export function isServedStatic() {
  return window.ENV?.IS_STATIC_FRONTEND;
}

export function useDebounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  delay: number,
) {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const debouncedFunc = useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        func(...args);
      }, delay);
    },
    [func, delay],
  );

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return debouncedFunc;
}
