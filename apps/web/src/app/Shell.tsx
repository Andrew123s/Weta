import { NavLink, Outlet } from "react-router";

import { useReadiness } from "../api/system";
import { NAV_ITEMS } from "./navigation";

function ApiStatus() {
  const { data, isError, isPending } = useReadiness();
  let text = "Checking API…";
  let state = "pending";
  if (isError) {
    text = "API unreachable";
    state = "error";
  } else if (!isPending) {
    state = data.status;
    text =
      data.status === "ok"
        ? "API ready"
        : `API up · database ${(data.checks[0]?.status ?? "unknown").replace("_", " ")}`;
  }
  return (
    <span className="api-status" data-state={state} role="status">
      {text}
    </span>
  );
}

/** Layout: header, main navigation and the routed page. */
export function Shell() {
  return (
    <div className="shell">
      <header className="shell-header">
        <span className="brand">Weta</span>
        <span className="brand-sub">Predictive EIA · LCA · GIS · ML</span>
        <ApiStatus />
      </header>
      <nav className="shell-nav" aria-label="Main">
        <ul>
          {NAV_ITEMS.map((item) => (
            <li key={item.path}>
              <NavLink to={item.path} end={item.path === "/"}>
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <main className="shell-main" id="main">
        <Outlet />
      </main>
    </div>
  );
}
