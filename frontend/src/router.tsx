import { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";

import { setDataProvider } from "./lib/api/data-provider";
import { fastAPIProvider } from "./lib/api/fastapi-provider";

// Register the production provider once
setDataProvider(fastAPIProvider);

export const getRouter = () => {
  const queryClient = new QueryClient();

  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
  });

  return router;
};
