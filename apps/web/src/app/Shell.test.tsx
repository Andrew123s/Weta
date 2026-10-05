import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import axe from "axe-core";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { makeQueryClient, routes } from "./App";
import { NAV_ITEMS } from "./navigation";

const READY_NOT_CONFIGURED = {
  status: "not_configured",
  checks: [
    {
      name: "database",
      status: "not_configured",
      detail: "WETA_DATABASE_URL is not set",
      version: null,
    },
  ],
};
const VERSION = {
  application: "0.1.0",
  api_version: "v1",
  environment: "development",
  git_sha: null,
  python: "3.12.12",
  components: { "weta-core": "0.1.0", fastapi: "0.136.0" },
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

async function expectNoAxeViolations(container: HTMLElement) {
  // jsdom has no layout engine, so colour contrast is checked in the browser instead.
  const results = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
  expect(results.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
}

describe("application shell", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: Request) => {
        const url = new URL(input.url);
        if (url.pathname === "/api/v1/health/ready") {
          return Promise.resolve(json(READY_NOT_CONFIGURED, 503));
        }
        if (url.pathname === "/api/v1/version") return Promise.resolve(json(VERSION));
        return Promise.resolve(json({ title: "Not Found", status: 404 }, 404));
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists every main navigation area from docs/frontend.md", () => {
    renderAt("/");
    const nav = screen.getByRole("navigation", { name: "Main" });
    const labels = within(nav)
      .getAllByRole("link")
      .map((a) => a.textContent);
    expect(labels).toEqual([
      "Dashboard",
      "Projects",
      "Facilities",
      "Production",
      "Materials",
      "Waste",
      "GIS",
      "Scenarios",
      "LCA",
      "Risk",
      "ML",
      "Reports",
      "Data",
      "Administration",
    ]);
  });

  it("shows live dependency status from the API, treating 503 readiness as data", async () => {
    const { container } = renderAt("/");
    expect(await screen.findByText("Not configured")).toBeInTheDocument();
    expect(screen.getByText("WETA_DATABASE_URL is not set")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("API up · database not configured");
    expect(await screen.findByText("weta-core")).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("reports an unreachable API instead of showing stale or invented data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
    );
    renderAt("/");
    await waitFor(
      () => {
        expect(screen.getByRole("status")).toHaveTextContent("API unreachable");
      },
      { timeout: 4000 },
    );
  });

  it.each(NAV_ITEMS.filter((i) => i.path !== "/"))(
    "$label page states which phase delivers it",
    async (item) => {
      const { container } = renderAt(item.path);
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(item.label);
      expect(screen.getByRole("note")).toHaveTextContent(`Phase ${String(item.phase)}`);
      await expectNoAxeViolations(container);
    },
  );

  it("shows a not-found page for unknown routes", () => {
    renderAt("/no-such-page");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Not found");
  });
});
