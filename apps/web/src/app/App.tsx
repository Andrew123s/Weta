import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { createBrowserRouter, RouterProvider, type RouteObject } from "react-router";

import { DashboardPage } from "../features/dashboard/DashboardPage";
import { PlaceholderPage } from "../features/placeholder/PlaceholderPage";
import { NAV_ITEMS } from "./navigation";
import { RouteError } from "./RouteError";
import { Shell } from "./Shell";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Shell />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <DashboardPage /> },
      ...NAV_ITEMS.filter((item) => item.path !== "/").map((item) => ({
        path: item.path.slice(1),
        element: <PlaceholderPage item={item} />,
      })),
      { path: "*", element: <RouteError notFound /> },
    ],
  },
];

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
  });
}

export function App() {
  const [queryClient] = useState(makeQueryClient);
  const [router] = useState(() => createBrowserRouter(routes));
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
