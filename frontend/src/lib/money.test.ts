import { describe, expect, it } from "vitest";
import { formatMinor } from "./money";

describe("formatMinor", () => {
  it("formats integer minor units without float arithmetic", () => {
    expect(formatMinor(123456)).toBe("$1,234.56");
    expect(formatMinor(5)).toBe("$0.05");
    expect(formatMinor(0)).toBe("$0.00");
  });

  it("uses a true minus sign for outflows", () => {
    expect(formatMinor(-98701)).toBe("−$987.01");
  });

  it("adds an explicit plus only when asked", () => {
    expect(formatMinor(150000, { sign: true })).toBe("+$1,500.00");
    expect(formatMinor(150000)).toBe("$1,500.00");
  });

  it("survives the float-poison amounts", () => {
    expect(formatMinor(10 + 20)).toBe("$0.30"); // 0.1 + 0.2 as minor units
    expect(formatMinor(1999999999)).toBe("$19,999,999.99");
  });
});
