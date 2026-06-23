import { http, HttpResponse } from "msw";

export const appHandlers = [
  http.get("api/v1/welcome", () => {
    return HttpResponse.json({
      message: "Welcome Engineer!",
    });
  }),

  http.get("/api/v1/config/feature-flags", () => {
    return HttpResponse.json({
      refinerEnabled: false,
      refinerAutoSend: false,
      templateEditEnabled: false,
      customPromptsEnabled: false,
      reportBuilderEnabled: false,
    });
  }),

  http.get("/api/v1/templates", () => {
    return HttpResponse.json([]);
  }),

  http.get("/api/v1/templates/categories", () => {
    return HttpResponse.json([]);
  }),
];
