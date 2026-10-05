import type { NavItem } from "../../app/navigation";

/**
 * An area that is not built yet. It says so plainly and shows no sample numbers, so nothing
 * on screen can be mistaken for a result.
 */
export function PlaceholderPage({ item }: { item: NavItem }) {
  return (
    <section className="page" aria-labelledby="page-title">
      <h1 id="page-title">{item.label}</h1>
      <p className="placeholder-note" role="note">
        Not available yet. This area is delivered in Phase {item.phase} of the development plan.
      </p>
      <p className="muted">{item.summary}</p>
    </section>
  );
}
