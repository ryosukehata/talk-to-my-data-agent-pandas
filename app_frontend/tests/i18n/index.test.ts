import { afterAll, beforeEach, describe, expect, test } from "vitest";
import i18n from "@/i18n";

describe("i18n <html lang> sync", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  afterAll(async () => {
    await i18n.changeLanguage("en");
  });

  test("initializes document.documentElement.lang from i18n", () => {
    expect(document.documentElement.lang).toBe("en");
  });

  test("updates document.documentElement.lang on language change and normalizes underscores", async () => {
    await i18n.changeLanguage("pt_BR");
    expect(document.documentElement.lang).toBe("pt-BR");

    await i18n.changeLanguage("fr");
    expect(document.documentElement.lang).toBe("fr");
  });
});
