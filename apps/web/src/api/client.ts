/**
 * Thin typed API client. Types come from the generated `schema.d.ts`
 * (`pnpm --filter web gen:api`); nothing here is hand-written against the API.
 */
import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type Schemas = components["schemas"];
export type QuantityOut = Schemas["QuantityOut"];
export type ProvenanceClass = Schemas["ProvenanceClass"];
export type Taint = Schemas["Taint"];
export type Uncertainty = NonNullable<QuantityOut["uncertainty"]>;
export type ProblemDetail = Schemas["ProblemDetail"];

/**
 * Same-origin in every environment: Vite proxies /api in development, nginx in production.
 * `fetch` is looked up per request rather than captured once, so it can be replaced in tests.
 */
export const api = createClient<paths>({
  baseUrl: globalThis.location.origin,
  fetch: (request) => globalThis.fetch(request),
});

/** An API failure carrying the RFC 9457 problem details when the server sent them. */
export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetail | null;

  constructor(status: number, problem: ProblemDetail | null) {
    super(problem?.detail ?? problem?.title ?? `Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

function isProblem(body: unknown): body is ProblemDetail {
  return typeof body === "object" && body !== null && "title" in body && "status" in body;
}

/** Turn an openapi-fetch error body into an `ApiError`. */
export function toApiError(status: number, body: unknown): ApiError {
  return new ApiError(status, isProblem(body) ? body : null);
}
