import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const IPHONE_SAFARI =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1";
const IPHONE_IN_APP =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148";
const DESKTOP_FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0";
const ANDROID_CHROME =
  "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36";

// install.ts y platform.ts leen window y navigator al importarse, así que cada test
// prepara un "navegador" falso y vuelve a importar los módulos desde cero.
async function load(options: { userAgent: string; standalone?: boolean }) {
  const win = new EventTarget();
  vi.stubGlobal("window", Object.assign(win, { matchMedia: () => ({ matches: !!options.standalone }) }));
  vi.stubGlobal("navigator", { userAgent: options.userAgent });
  vi.resetModules();
  const install = await import("./install");
  const platform = await import("./platform");
  return { win, install, platform };
}

/** Un `beforeinstallprompt` falso, con el `prompt()` y el `userChoice` del navegador. */
function fakeInstallEvent(outcome: "accepted" | "dismissed" = "accepted") {
  const event = new Event("beforeinstallprompt", { cancelable: true });
  const prompt = vi.fn().mockResolvedValue(undefined);
  Object.assign(event, { prompt, userChoice: Promise.resolve({ outcome }) });
  return { event, prompt };
}

function fakeStorage(initial: Record<string, string>) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
    removeItem: (key: string) => void data.delete(key),
  };
}

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("getInstallMode", () => {
  it("no ofrece nada en un navegador de escritorio que no avisa de que se pueda instalar", async () => {
    const { install } = await load({ userAgent: DESKTOP_FIREFOX });
    expect(install.getInstallMode()).toBe("unavailable");
  });

  it("en Android sin evento (lo descartaste antes) explica cómo hacerlo desde el menú", async () => {
    const { install } = await load({ userAgent: ANDROID_CHROME });
    expect(install.getInstallMode()).toBe("manual");
  });

  it("ofrece el botón cuando Chrome lanza beforeinstallprompt", async () => {
    const { win, install } = await load({ userAgent: ANDROID_CHROME });
    const { event } = fakeInstallEvent();

    win.dispatchEvent(event);

    expect(install.getInstallMode()).toBe("prompt");
    // Se cancela el comportamiento por defecto para pintar nuestro propio botón.
    expect(event.defaultPrevented).toBe(true);
  });

  it("pasa a done cuando se instala, para decir que la abras desde la pantalla de inicio", async () => {
    const { win, install } = await load({ userAgent: ANDROID_CHROME });
    win.dispatchEvent(fakeInstallEvent().event);

    win.dispatchEvent(new Event("appinstalled"));

    expect(install.getInstallMode()).toBe("done");
  });

  it("recuerda que ya se instaló y no la vuelve a ofrecer en otra visita", async () => {
    vi.stubGlobal("localStorage", fakeStorage({ "psst-installed": "1" }));
    const { install } = await load({ userAgent: ANDROID_CHROME });
    expect(install.getInstallMode()).toBe("installed");
  });

  it("si Chrome vuelve a ofrecer instalarla, es que se desinstaló", async () => {
    const storage = fakeStorage({ "psst-installed": "1" });
    vi.stubGlobal("localStorage", storage);
    const { win, install } = await load({ userAgent: ANDROID_CHROME });

    win.dispatchEvent(fakeInstallEvent().event);

    expect(install.getInstallMode()).toBe("prompt");
    expect(storage.getItem("psst-installed")).toBeNull();
  });

  it("está installed si la web ya se abrió desde la pantalla de inicio", async () => {
    const { install } = await load({ userAgent: ANDROID_CHROME, standalone: true });
    expect(install.getInstallMode()).toBe("installed");
  });

  it("en iPhone explica los pasos a mano, porque no existe el evento", async () => {
    const { install } = await load({ userAgent: IPHONE_SAFARI });
    expect(install.getInstallMode()).toBe("ios");
  });

  it("en iPhone ya instalada no ofrece nada", async () => {
    const { install } = await load({ userAgent: IPHONE_SAFARI, standalone: true });
    expect(install.getInstallMode()).toBe("installed");
  });
});

describe("promptInstall", () => {
  it("abre el diálogo del navegador y gasta el evento, que solo sirve una vez", async () => {
    const { win, install } = await load({ userAgent: ANDROID_CHROME });
    const { event, prompt } = fakeInstallEvent();
    win.dispatchEvent(event);

    await install.promptInstall();

    expect(prompt).toHaveBeenCalledOnce();
    // Aceptado: sigue "instalando" hasta que el navegador lance appinstalled.
    expect(install.getInstallMode()).toBe("installing");
  });

  it("si se cancela el diálogo, vuelve a explicar cómo instalarla desde el menú", async () => {
    const { win, install } = await load({ userAgent: ANDROID_CHROME });
    win.dispatchEvent(fakeInstallEvent("dismissed").event);

    await install.promptInstall();

    expect(install.getInstallMode()).toBe("manual");
  });

  it("no hace nada si el navegador no ha avisado todavía", async () => {
    const { install } = await load({ userAgent: ANDROID_CHROME });
    await expect(install.promptInstall()).resolves.toBeUndefined();
  });
});

describe("isInAppBrowser", () => {
  it("reconoce el navegador interno de otra app en iPhone (sin «Safari» en el user agent)", async () => {
    const { platform } = await load({ userAgent: IPHONE_IN_APP });
    expect(platform.isInAppBrowser).toBe(true);
  });

  it("no confunde Safari con un navegador interno", async () => {
    const { platform } = await load({ userAgent: IPHONE_SAFARI });
    expect(platform.isInAppBrowser).toBe(false);
  });
});
