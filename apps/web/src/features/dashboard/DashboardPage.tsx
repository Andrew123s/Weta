import { ApiError } from "../../api/client";
import { useReadiness, useVersion } from "../../api/system";

const CHECK_LABELS: Record<string, string> = {
  ok: "OK",
  not_configured: "Not configured",
  unavailable: "Unavailable",
  degraded: "Degraded",
};

function errorText(error: Error): string {
  return error instanceof ApiError ? `${error.message} (HTTP ${error.status})` : error.message;
}

function SystemStatus() {
  const readiness = useReadiness();
  if (readiness.isPending) return <p>Checking dependencies…</p>;
  if (readiness.isError) {
    return (
      <p className="error" role="alert">
        The API could not be reached: {errorText(readiness.error)}
      </p>
    );
  }
  return (
    <table className="data-table">
      <caption>Dependencies</caption>
      <thead>
        <tr>
          <th scope="col">Component</th>
          <th scope="col">Status</th>
          <th scope="col">Version</th>
          <th scope="col">Detail</th>
        </tr>
      </thead>
      <tbody>
        {readiness.data.checks.map((check) => (
          <tr key={check.name}>
            <td>{check.name}</td>
            <td>
              <span className="status-pill" data-state={check.status}>
                {CHECK_LABELS[check.status] ?? check.status}
              </span>
            </td>
            <td>{check.version ?? "—"}</td>
            <td>{check.detail ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Versions() {
  const version = useVersion();
  if (version.isPending) return null;
  if (version.isError) {
    return (
      <p className="error" role="alert">
        Version information unavailable: {errorText(version.error)}
      </p>
    );
  }
  const { application, api_version, environment, git_sha, python, components } = version.data;
  return (
    <dl className="kv">
      <dt>Application</dt>
      <dd>
        {application} (API {api_version}, {environment})
      </dd>
      <dt>Build</dt>
      <dd>{git_sha ?? "not recorded"}</dd>
      <dt>Python</dt>
      <dd>{python}</dd>
      {Object.entries(components).map(([name, v]) => (
        <div key={name} className="kv-row">
          <dt>{name}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * Phase 1 dashboard: live system status from the API. Project status, data completeness and
 * data gaps are added once projects exist (Phase 2 onward).
 */
export function DashboardPage() {
  return (
    <section className="page" aria-labelledby="page-title">
      <h1 id="page-title">Dashboard</h1>
      <p className="muted">
        No projects exist yet. Project status, data completeness and data gaps appear here from
        Phase 2.
      </p>
      <h2>System status</h2>
      <SystemStatus />
      <h2>Versions</h2>
      <Versions />
    </section>
  );
}
