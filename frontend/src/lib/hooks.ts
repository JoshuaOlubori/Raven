import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  appointmentApi,
  authApi,
  patientApi,
  scheduleApi,
  serviceApi,
  staffApi,
} from './api-client';

/** Query keys factory */
export const queryKeys = {
  auth: {
    me: ['auth', 'me'] as const,
  },
  patients: {
    all: ['patients'] as const,
    list: (params?: { search?: string; page?: number; size?: number }) =>
      ['patients', 'list', params] as const,
    detail: (id: string) => ['patients', 'detail', id] as const,
  },
  staff: {
    all: ['staff'] as const,
    list: (role?: string) => ['staff', 'list', role] as const,
    detail: (id: string) => ['staff', 'detail', id] as const,
    dentists: () => ['staff', 'dentists'] as const,
  },
  services: {
    all: ['services'] as const,
    list: (activeOnly?: boolean) => ['services', 'list', activeOnly] as const,
    detail: (id: string) => ['services', 'detail', id] as const,
  },
  schedules: {
    shifts: {
      all: ['schedules', 'shifts'] as const,
      list: (dentistId?: string) => ['schedules', 'shifts', 'list', dentistId] as const,
    },
    timeOff: {
      all: ['schedules', 'timeOff'] as const,
      list: (dentistId: string, startDate: string, endDate: string) =>
        ['schedules', 'timeOff', 'list', dentistId, startDate, endDate] as const,
    },
    availability: (params: { serviceId: string; date: string; dentistId?: string }) =>
      ['schedules', 'availability', params] as const,
  },
  appointments: {
    all: ['appointments'] as const,
    list: (params?: {
      dentistId?: string;
      patientId?: string;
      status?: string;
      startDate?: string;
      endDate?: string;
    }) => ['appointments', 'list', params] as const,
    detail: (id: string) => ['appointments', 'detail', id] as const,
    auditLogs: (id: string) => ['appointments', 'auditLogs', id] as const,
  },
} as const;

/** Auth hooks */
export function useMe() {
  return useQuery({
    queryKey: queryKeys.auth.me,
    queryFn: () => authApi.me(),
    staleTime: 5 * 60_000, // 5 minutes
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (data) => {
      // Import dynamically to avoid circular dependency
      import('./api-client').then(({ setAuth }) => {
        setAuth(data.accessToken, {
          id: '', // Will be populated by me query
          email: '',
          fullName: '',
          role: data.role,
          isActive: true,
          createdAt: new Date().toISOString(),
        });
      });
      // Invalidate and refetch user
      queryClient.invalidateQueries({ queryKey: queryKeys.auth.me });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      // No backend logout endpoint, just clear local storage
      import('./api-client').then(({ clearAuth }) => clearAuth());
    },
    onSuccess: () => {
      queryClient.clear();
    },
  });
}

/** Patient hooks */
export function usePatients(params?: { search?: string; page?: number; size?: number }) {
  return useQuery({
    queryKey: queryKeys.patients.list(params),
    queryFn: () => patientApi.list(params),
  });
}

export function usePatient(id: string) {
  return useQuery({
    queryKey: queryKeys.patients.detail(id),
    queryFn: () => patientApi.get(id),
    enabled: !!id,
  });
}

export function useCreatePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof patientApi.create>[0]) => patientApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.patients.all });
    },
  });
}

export function useUpdatePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof patientApi.update>[1] }) =>
      patientApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.patients.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.patients.all });
    },
  });
}

export function useDeletePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => patientApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.patients.all });
    },
  });
}

/** Staff hooks */
export function useStaff(role?: string) {
  return useQuery({
    queryKey: queryKeys.staff.list(role),
    queryFn: () => staffApi.list(role),
  });
}

export function useDentists() {
  return useQuery({
    queryKey: queryKeys.staff.dentists(),
    queryFn: () => staffApi.list('DENTIST'),
  });
}

export function useStaffMember(id: string) {
  return useQuery({
    queryKey: queryKeys.staff.detail(id),
    queryFn: () => staffApi.get(id),
    enabled: !!id,
  });
}

export function useCreateStaff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof staffApi.create>[0]) => staffApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.staff.all });
    },
  });
}

export function useUpdateStaff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof staffApi.update>[1] }) =>
      staffApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.staff.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.staff.all });
    },
  });
}

/** Service hooks */
export function useServices(activeOnly = true) {
  return useQuery({
    queryKey: queryKeys.services.list(activeOnly),
    queryFn: () => serviceApi.list(activeOnly),
  });
}

export function useService(id: string) {
  return useQuery({
    queryKey: queryKeys.services.detail(id),
    queryFn: () => serviceApi.get(id),
    enabled: !!id,
  });
}

export function useCreateService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof serviceApi.create>[0]) => serviceApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.services.all });
    },
  });
}

export function useUpdateService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof serviceApi.update>[1] }) =>
      serviceApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.services.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.services.all });
    },
  });
}

/** Schedule hooks */
export function useShifts(dentistId?: string) {
  return useQuery({
    queryKey: queryKeys.schedules.shifts.list(dentistId),
    queryFn: () => scheduleApi.shifts.list(dentistId),
  });
}

export function useCreateShift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof scheduleApi.shifts.create>[0]) =>
      scheduleApi.shifts.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.schedules.shifts.all });
    },
  });
}

export function useDeleteShift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => scheduleApi.shifts.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.schedules.shifts.all });
    },
  });
}

export function useTimeOff(dentistId: string, startDate: string, endDate: string) {
  return useQuery({
    queryKey: queryKeys.schedules.timeOff.list(dentistId, startDate, endDate),
    queryFn: () => scheduleApi.timeOff.list(dentistId, startDate, endDate),
    enabled: !!dentistId && !!startDate && !!endDate,
  });
}

export function useCreateTimeOff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof scheduleApi.timeOff.create>[0]) =>
      scheduleApi.timeOff.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.schedules.timeOff.all });
    },
  });
}

export function useDeleteTimeOff() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => scheduleApi.timeOff.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.schedules.timeOff.all });
    },
  });
}

export function useAvailability(
  params: { serviceId: string; date: string; dentistId?: string },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: queryKeys.schedules.availability(params),
    queryFn: () => scheduleApi.availability(params),
    enabled: !!params.serviceId && !!params.date && (options?.enabled ?? true),
  });
}

/** Appointment hooks */
export function useAppointments(params?: {
  dentistId?: string;
  patientId?: string;
  status?: string;
  startDate?: string;
  endDate?: string;
}) {
  return useQuery({
    queryKey: queryKeys.appointments.list(params),
    queryFn: () => appointmentApi.list(params),
  });
}

export function useAppointment(id: string) {
  return useQuery({
    queryKey: queryKeys.appointments.detail(id),
    queryFn: () => appointmentApi.get(id),
    enabled: !!id,
  });
}

export function useCreateAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof appointmentApi.create>[0]) => appointmentApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.appointments.all });
    },
  });
}

export function useRescheduleAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Parameters<typeof appointmentApi.reschedule>[1];
    }) => appointmentApi.reschedule(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.appointments.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.appointments.all });
    },
  });
}

export function useCancelAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof appointmentApi.cancel>[1] }) =>
      appointmentApi.cancel(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.appointments.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.appointments.all });
    },
  });
}

export function useUpdateAppointmentStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Parameters<typeof appointmentApi.updateStatus>[1];
    }) => appointmentApi.updateStatus(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.appointments.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.appointments.all });
    },
  });
}

export function useAuditLogs(id: string) {
  return useQuery({
    queryKey: queryKeys.appointments.auditLogs(id),
    queryFn: () => appointmentApi.auditLogs(id),
    enabled: !!id,
  });
}

export function useDispatchReminders() {
  return useMutation({
    mutationFn: () => appointmentApi.reminders.dispatch(),
  });
}
