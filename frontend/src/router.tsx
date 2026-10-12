import { createRootRoute, createRoute, createRouter, Outlet } from '@tanstack/react-router';
import { useAuthStore } from '@/lib/auth-store';
import { Providers } from './app/providers';
import { ErrorPage } from './routes/__error';
import { NotFoundPage } from './routes/__not-found';
import { RootLayout } from './routes/__root';
import { AppointmentsPage } from './routes/appointments';
import { AppointmentDetailPage } from './routes/appointments/$id';
import { MySchedulePage } from './routes/my-schedule';
import { PatientsPage } from './routes/patients';
import { PatientProfilePage } from './routes/patients/$id';
import { PatientEditPage } from './routes/patients/$id.edit';
import { PatientNewPage } from './routes/patients/$new';
import { ProviderSchedulesPage } from './routes/provider-schedules';
import { ServicesPage } from './routes/services';
import { SignInPage } from './routes/sign-in';
import { StaffPage } from './routes/staff';
import { TodayPage } from './routes/today';

// Placeholder components for routes not yet implemented
function AppointmentsNewPage() {
  return (
    <div className="p-6 text-center">
      <h2 className="text-headline-md text-text-primary mb-4">New Appointment</h2>
      <p className="text-text-secondary">Appointment creation form coming soon.</p>
    </div>
  );
}

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

// Root route
const rootRoute = createRootRoute({
  component: () => (
    <Providers>
      <RootLayout />
    </Providers>
  ),
});

// Public routes
const signInRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/sign-in',
  component: SignInPage,
});

// Protected route wrapper
const protectedRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => {
    const { user, isInitialized } = useAuthStore();
    if (!isInitialized) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-4 border-brand-primary border-t-transparent rounded-full" />
        </div>
      );
    }
    if (!user) return null;
    return <Outlet />;
  },
});

// Protected routes
const todayRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: 'today',
  component: TodayPage,
});

const patientsRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: 'patients',
  component: PatientsPage,
});

const patientNewRoute = createRoute({
  getParentRoute: () => patientsRoute,
  path: 'new',
  component: PatientNewPage,
});

const appointmentsNewRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: 'appointments/new',
  component: AppointmentsNewPage,
});

const patientEditRoute = createRoute({
  getParentRoute: () => patientsRoute,
  path: '$id/edit',
  component: PatientEditPage,
});

const patientProfileRoute = createRoute({
  getParentRoute: () => patientsRoute,
  path: '$id',
  component: PatientProfilePage,
});

const myScheduleRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: 'my-schedule',
  component: MySchedulePage,
});

const appointmentsRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: 'appointments',
  component: AppointmentsPage,
});

const appointmentDetailRoute = createRoute({
  getParentRoute: () => appointmentsRoute,
  path: '$id',
  component: AppointmentDetailPage,
});

const servicesRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: 'services',
  component: ServicesPage,
});

const providerSchedulesRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: 'provider-schedules',
  component: ProviderSchedulesPage,
});

const staffRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: 'staff',
  component: StaffPage,
});

const notFoundRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/*',
  component: NotFoundPage,
});

const errorRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/__error',
  component: ErrorPage,
});

const routeTree = rootRoute.addChildren([
  signInRoute,
  protectedRoute.addChildren([
    todayRoute,
    patientsRoute.addChildren([patientNewRoute, patientEditRoute, patientProfileRoute]),
    myScheduleRoute,
    appointmentsRoute.addChildren([appointmentDetailRoute, appointmentsNewRoute]),
    servicesRoute,
    providerSchedulesRoute,
    staffRoute,
  ]),
  notFoundRoute,
  errorRoute,
]);

export const router = createRouter({ routeTree });
