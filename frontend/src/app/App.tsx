import { Navigate, Route, Routes } from "react-router-dom";

import { GlobalErrorBoundary } from "@/components/GlobalErrorBoundary";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { AuthLayout } from "@/layouts/AuthLayout";
import { DashboardLayout } from "@/layouts/DashboardLayout";
import { ApiKeysPage } from "@/pages/ApiKeysPage";
import { DeadLetterPage } from "@/pages/DeadLetterPage";
import { DeliveriesPage } from "@/pages/DeliveriesPage";
import { DeliveryDetailPage } from "@/pages/DeliveryDetailPage";
import { EndpointDetailPage } from "@/pages/EndpointDetailPage";
import { EndpointsPage } from "@/pages/EndpointsPage";
import { EventTypesPage } from "@/pages/EventTypesPage";
import { EventsPage } from "@/pages/EventsPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { OverviewPage } from "@/pages/OverviewPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SubscriptionsPage } from "@/pages/SubscriptionsPage";

export function App() {
  return (
    <GlobalErrorBoundary>
      <Routes>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        <Route element={<RequireAuth />}>
          <Route element={<DashboardLayout />}>
            <Route index element={<OverviewPage />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/deliveries" element={<DeliveriesPage />} />
            <Route path="/deliveries/:deliveryId" element={<DeliveryDetailPage />} />
            <Route path="/endpoints" element={<EndpointsPage />} />
            <Route path="/endpoints/:endpointId" element={<EndpointDetailPage />} />
            <Route path="/event-types" element={<EventTypesPage />} />
            <Route path="/subscriptions" element={<SubscriptionsPage />} />
            <Route path="/api-keys" element={<ApiKeysPage />} />
            <Route path="/dead-letter" element={<DeadLetterPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/status" element={<Navigate to="/settings" replace />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </GlobalErrorBoundary>
  );
}
