/** Query hooks for the system endpoints: liveness, readiness and version. */
import { useQuery } from "@tanstack/react-query";

import { api, toApiError, type Schemas } from "./client";

export type Readiness = Schemas["ReadinessResponse"];
export type VersionInfo = Schemas["VersionResponse"];

const POLL_MS = 30_000;

export function useReadiness() {
  return useQuery({
    queryKey: ["system", "ready"],
    refetchInterval: POLL_MS,
    queryFn: async (): Promise<Readiness> => {
      const { data, error, response } = await api.GET("/api/v1/health/ready");
      if (data) return data;
      // 503 is a normal answer here: the body says which dependency is not ready.
      if (response.status === 503) return error;
      throw toApiError(response.status, error);
    },
  });
}

export function useVersion() {
  return useQuery({
    queryKey: ["system", "version"],
    queryFn: async (): Promise<VersionInfo> => {
      const { data, error, response } = await api.GET("/api/v1/version");
      if (data) return data;
      throw toApiError(response.status, error);
    },
  });
}
