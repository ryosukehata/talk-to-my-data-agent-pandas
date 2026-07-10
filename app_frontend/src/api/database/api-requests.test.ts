import { describe, expect, it } from "vitest";

import { normalizeDatabaseTables } from "./api-requests";

describe("normalizeDatabaseTables", () => {
  it("maps legacy list responses by table name instead of array index", () => {
    expect(normalizeDatabaseTables(["ORDERS", "CUSTOMER"])).toEqual({
      ORDERS: "ORDERS",
      CUSTOMER: "CUSTOMER",
    });
  });

  it("preserves table descriptions from mapping responses", () => {
    expect(normalizeDatabaseTables({ ORDERS: "Order facts" })).toEqual({
      ORDERS: "Order facts",
    });
  });
});
