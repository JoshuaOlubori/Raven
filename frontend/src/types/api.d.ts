// Placeholder API types - replace by running `npm run generate:api` when backend is available
// This file provides minimal types for development until OpenAPI types are generated

export type StaffRole = 'ADMIN' | 'RECEPTIONIST' | 'DENTIST';

export interface TokenRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  role: StaffRole;
}

export interface StaffRead {
  id: string;
  email: string;
  fullName: string;
  role: StaffRole;
  isActive: boolean;
  createdAt: string;
}

export interface StaffCreate {
  email: string;
  password: string;
  fullName: string;
  role: StaffRole;
}

export interface StaffUpdate {
  fullName?: string;
  role?: StaffRole;
  isActive?: boolean;
}

export interface ServiceRead {
  id: string;
  name: string;
  description: string | null;
  durationMinutes: number;
  isActive: boolean;
  createdAt: string;
}

export interface ServiceCreate {
  name: string;
  description?: string;
  durationMinutes: number;
  isActive?: boolean;
}

export interface ServiceUpdate {
  name?: string;
  description?: string;
  durationMinutes?: number;
  isActive?: boolean;
}

export interface PatientRead {
  id: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  phone: string;
  email: string | null;
  emergencyContactName: string | null;
  emergencyContactPhone: string | null;
  medicalAlerts: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  fullName: string;
}

export interface PatientCreate {
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  phone: string;
  email?: string;
  emergencyContactName?: string;
  emergencyContactPhone?: string;
  medicalAlerts?: string;
}

export interface PatientUpdate {
  firstName?: string;
  lastName?: string;
  dateOfBirth?: string;
  phone?: string;
  email?: string;
  emergencyContactName?: string;
  emergencyContactPhone?: string;
  medicalAlerts?: string;
}

export interface PatientPage {
  items: PatientRead[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export type AppointmentStatus =
  | 'SCHEDULED'
  | 'CONFIRMED'
  | 'CHECKED_IN'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'NO_SHOW';

export interface AppointmentRead {
  id: string;
  patientId: string;
  dentistId: string;
  serviceId: string;
  startTime: string;
  endTime: string;
  status: AppointmentStatus;
  cancellationReason: string | null;
  reminderSentAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AppointmentDetailRead extends AppointmentRead {
  patient: PatientRead;
  dentist: StaffRead;
  service: ServiceRead;
}

export interface AppointmentCreate {
  patientId: string;
  dentistId: string;
  serviceId: string;
  startTime: string;
}

export interface AppointmentReschedule {
  startTime: string;
  dentistId?: string;
}

export interface AppointmentCancel {
  cancellationReason: string;
}

export interface AppointmentStatusUpdate {
  toStatus: AppointmentStatus;
  note?: string;
}

export interface AuditLogRead {
  id: string;
  appointmentId: string;
  actorId: string;
  fromStatus: string | null;
  toStatus: string | null;
  oldStartTime: string | null;
  newStartTime: string | null;
  note: string | null;
  createdAt: string;
  actor: StaffRead;
  actorName: string;
}

export interface WorkingShiftRead {
  id: string;
  dentistId: string;
  dayOfWeek: number;
  startTime: string;
  endTime: string;
}

export interface WorkingShiftCreate {
  dentistId: string;
  dayOfWeek: number;
  startTime: string;
  endTime: string;
}

export interface TimeOffBlockRead {
  id: string;
  dentistId: string;
  startTime: string;
  endTime: string;
  reason: string | null;
  createdAt: string;
}

export interface TimeOffBlockCreate {
  dentistId: string;
  startTime: string;
  endTime: string;
  reason?: string;
}

export interface TimeSlot {
  startTime: string;
  endTime: string;
  dentistId: string;
  dentistName: string;
}

export interface AvailabilityResponse {
  date: string;
  serviceId: string;
  durationMinutes: number;
  slots: TimeSlot[];
}

export interface ReminderDispatchResult {
  dispatchedCount: number;
  checkedWindowStart: string;
  checkedWindowEnd: string;
}

export interface AppointmentLiveEvent {
  eventType: string;
  appointmentId: string;
  dentistId: string;
  patientName: string;
  status: string;
  startTime: string;
  timestamp: string;
}

export type EventType =
  | 'appointment.booked'
  | 'appointment.rescheduled'
  | 'appointment.cancelled'
  | 'appointment.confirmed'
  | 'appointment.checked_in'
  | 'appointment.started'
  | 'appointment.completed'
  | 'appointment.no_show';
