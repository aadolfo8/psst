import { describe, expect, it } from "vitest";

import { slugFromInput } from "./groupSlug";

describe("slugFromInput", () => {
  it("acepta el enlace completo del grupo", () => {
    expect(slugFromInput("https://psst.hidan.es/g/abcdefghjk")).toBe("abcdefghjk");
  });

  it("acepta un enlace de otra pantalla del grupo, o con texto alrededor", () => {
    expect(slugFromInput("https://psst.hidan.es/g/abcdefghjk/chat")).toBe("abcdefghjk");
    expect(slugFromInput("  Mira: https://psst.hidan.es/g/abcdefghjk  ")).toBe("abcdefghjk");
  });

  it("acepta solo el código, sin importar mayúsculas ni espacios", () => {
    expect(slugFromInput(" ABCDEFGHJK ")).toBe("abcdefghjk");
  });

  it("rechaza lo que no se parece a un código", () => {
    expect(slugFromInput("")).toBeNull();
    expect(slugFromInput("hola")).toBeNull();
    expect(slugFromInput("https://psst.hidan.es/")).toBeNull();
    expect(slugFromInput("https://psst.hidan.es/g/corto")).toBeNull();
  });
});
