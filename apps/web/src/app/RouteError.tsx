import { isRouteErrorResponse, Link, useRouteError } from "react-router";

/** Error and not-found view. Shows what failed; never a blank page. */
export function RouteError({ notFound = false }: { notFound?: boolean }) {
  const error = useRouteError();
  let message = "This page does not exist.";
  if (!notFound) {
    if (isRouteErrorResponse(error)) message = `${String(error.status)} ${error.statusText}`;
    else if (error instanceof Error) message = error.message;
    else message = "An unexpected error occurred.";
  }
  return (
    <section className="page" aria-labelledby="page-title">
      <h1 id="page-title">{notFound ? "Not found" : "Something went wrong"}</h1>
      <p role="alert">{message}</p>
      <Link to="/">Back to the dashboard</Link>
    </section>
  );
}
