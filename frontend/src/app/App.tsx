import { RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { Preloader } from "@/components/shared/Preloader";
import { router } from "@/app/router";

export default function App() {
  return (
    <AppProviders>
      <RouterProvider router={router} />
      <Preloader />
    </AppProviders>
  );
}
