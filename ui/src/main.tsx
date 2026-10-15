import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter } from "react-router";
import { RouterProvider } from "react-router/dom";
import { LiveProvider } from "./api/LiveProvider";
import { createQueryClient } from "./api/queryClient";
import "./i18n";
import { routes } from "./routes";
import "./styles/fonts.css";
import "./styles/tokens.css";
import "./styles/base.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("index.html has no #root element");
}

const router = createBrowserRouter(routes);
const queryClient = createQueryClient();

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <LiveProvider>
        <RouterProvider router={router} />
      </LiveProvider>
    </QueryClientProvider>
  </StrictMode>,
);
