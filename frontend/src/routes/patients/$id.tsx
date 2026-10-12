import { Link, useParams } from '@tanstack/react-router';
import { format, parseISO } from 'date-fns';
import {
  AlertTriangle,
  ArrowLeft,
  Calendar,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Edit,
  Mail,
  MapPin,
  Phone,
  Stethoscope,
  User,
  XCircle,
} from 'lucide-react';
import { useState } from 'react';
import { useAppointments, usePatient } from '@/lib/hooks';
import { cn } from '@/lib/utils';
import type { AppointmentStatus } from '@/types/api';

export function PatientProfilePage() {
  const { id } = useParams({ from: '/patients/$id' });
  const { data: patient, isLoading } = usePatient(id);
  const { data: appointments } = useAppointments({ patientId: id });
  const [showMedicalAlerts, setShowMedicalAlerts] = useState(false);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-border-subtle rounded w-1/4" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-64 bg-border-subtle rounded-xl" />
          <div className="h-64 bg-border-subtle rounded-xl" />
        </div>
        <div className="h-96 bg-border-subtle rounded-xl" />
      </div>
    );
  }

  if (!patient) {
    return (
      <div className="text-center py-12">
        <User className="w-12 h-12 text-text-muted mx-auto mb-4" />
        <h2 className="text-headline-md text-text-primary mb-2">Patient not found</h2>
        <Link to="/patients" className="text-brand-primary hover:underline">
          Back to patients
        </Link>
      </div>
    );
  }

  const upcomingAppointments =
    appointments?.filter(
      (a) =>
        new Date(a.startTime) >= new Date() &&
        !['CANCELLED', 'NO_SHOW', 'COMPLETED'].includes(a.status)
    ) || [];

  const pastAppointments =
    appointments?.filter(
      (a) =>
        new Date(a.startTime) < new Date() ||
        ['CANCELLED', 'NO_SHOW', 'COMPLETED'].includes(a.status)
    ) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link
            to="/patients"
            className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-text-primary"
            aria-label="Back to patients"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-headline-lg text-text-primary">{patient.fullName}</h1>
              {!patient.isActive && (
                <span className="px-2.5 py-1 rounded-full text-label-xs font-medium bg-status-error-bg text-status-error">
                  Inactive
                </span>
              )}
            </div>
            <p className="text-text-secondary text-body-md">
              {patient.email || 'No email'} • {patient.phone}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to={`/patients/${id}/edit` as any}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors"
          >
            <Edit className="w-4 h-4" />
            Edit
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Patient Info Card */}
        <div className="lg:col-span-2 space-y-6">
          {/* Demographics */}
          <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-6">
            <h2 className="text-title-sm text-text-primary mb-5 flex items-center gap-2">
              <User className="w-5 h-5 text-brand-primary" />
              Demographics
            </h2>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-label-xs text-text-muted uppercase tracking-wider">
                  Full Name
                </dt>
                <dd className="text-body-md text-text-primary font-medium">{patient.fullName}</dd>
              </div>
              <div>
                <dt className="text-label-xs text-text-muted uppercase tracking-wider">
                  Date of Birth
                </dt>
                <dd className="text-body-md text-text-primary">
                  {format(parseISO(patient.dateOfBirth), 'MMMM d, yyyy')}
                  <span className="text-text-muted ml-2">
                    ({calculateAge(patient.dateOfBirth)} years)
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-label-xs text-text-muted uppercase tracking-wider">Phone</dt>
                <dd className="text-body-md text-text-primary flex items-center gap-2">
                  <Phone className="w-4 h-4 text-text-muted" />
                  {patient.phone}
                </dd>
              </div>
              <div>
                <dt className="text-label-xs text-text-muted uppercase tracking-wider">Email</dt>
                <dd className="text-body-md text-text-primary flex items-center gap-2">
                  <Mail className="w-4 h-4 text-text-muted" />
                  {patient.email || <span className="text-text-muted">Not provided</span>}
                </dd>
              </div>
            </dl>
          </div>

          {/* Emergency Contact */}
          {patient.emergencyContactName || patient.emergencyContactPhone ? (
            <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-6">
              <h2 className="text-title-sm text-text-primary mb-5 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-brand-primary" />
                Emergency Contact
              </h2>
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {patient.emergencyContactName && (
                  <>
                    <dt className="text-label-xs text-text-muted uppercase tracking-wider">Name</dt>
                    <dd className="text-body-md text-text-primary">
                      {patient.emergencyContactName}
                    </dd>
                  </>
                )}
                {patient.emergencyContactPhone && (
                  <>
                    <dt className="text-label-xs text-text-muted uppercase tracking-wider">
                      Phone
                    </dt>
                    <dd className="text-body-md text-text-primary flex items-center gap-2">
                      <Phone className="w-4 h-4 text-text-muted" />
                      {patient.emergencyContactPhone}
                    </dd>
                  </>
                )}
              </dl>
            </div>
          ) : null}

          {/* Medical Alerts */}
          {patient.medicalAlerts ? (
            <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-title-sm text-text-primary flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-status-warning" />
                  Medical Alerts
                </h2>
                <button
                  onClick={() => setShowMedicalAlerts(!showMedicalAlerts)}
                  className="text-sm text-brand-primary hover:underline flex items-center gap-1"
                >
                  {showMedicalAlerts ? (
                    <>
                      <ChevronUp className="w-4 h-4" />
                      Show Less
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-4 h-4" />
                      Show More
                    </>
                  )}
                </button>
              </div>
              <div
                className={cn('prose prose-sm max-w-none', !showMedicalAlerts && 'line-clamp-3')}
              >
                <p className="text-body-md text-text-primary whitespace-pre-wrap">
                  {patient.medicalAlerts}
                </p>
              </div>
            </div>
          ) : null}
        </div>

        {/* Sidebar - Quick Actions & Upcoming */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-6">
            <h2 className="text-title-sm text-text-primary mb-5">Quick Stats</h2>
            <div className="space-y-4">
              <StatItem label="Total Visits" value={appointments?.length || 0} icon={Stethoscope} />
              <StatItem
                label="Upcoming"
                value={upcomingAppointments.length}
                icon={Calendar}
                color="text-brand-primary"
              />
              <StatItem
                label="Completed"
                value={pastAppointments.filter((a) => a.status === 'COMPLETED').length}
                icon={CheckCircle}
                color="text-status-success"
              />
              <StatItem
                label="Cancelled"
                value={pastAppointments.filter((a) => a.status === 'CANCELLED').length}
                icon={XCircle}
                color="text-status-error"
              />
            </div>
          </div>

          {/* Upcoming Appointments */}
          <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-title-sm text-text-primary flex items-center gap-2">
                <Calendar className="w-5 h-5 text-brand-primary" />
                Upcoming Appointments
              </h2>
              <Link
                to={`/appointments?patientId=${id}` as any}
                className="text-sm text-brand-primary hover:underline"
              >
                View All
              </Link>
            </div>
            {upcomingAppointments.length === 0 ? (
              <p className="text-text-secondary text-center py-4">No upcoming appointments</p>
            ) : (
              <ul className="space-y-3">
                {upcomingAppointments.slice(0, 5).map((apt) => (
                  <li
                    key={apt.id}
                    className="p-3 rounded-lg border border-border-subtle hover:bg-bg-elevated transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-brand-primary/10 flex items-center justify-center">
                          <Stethoscope className="w-5 h-5 text-brand-primary" />
                        </div>
                        <div>
                          <p className="font-medium text-text-primary">{apt.service.name}</p>
                          <p className="text-body-xs text-text-muted">Dr. {apt.dentist.fullName}</p>
                        </div>
                      </div>
                      <StatusBadge status={apt.status} />
                    </div>
                    <div className="mt-2 flex items-center gap-4 text-body-xs text-text-muted">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {format(parseISO(apt.startTime), 'MMM d, h:mm a')}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Visit History */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle overflow-hidden">
        <div className="p-6 border-b border-border-subtle">
          <h2 className="text-title-sm text-text-primary flex items-center gap-2">
            <Clock className="w-5 h-5 text-brand-primary" />
            Visit History
          </h2>
        </div>
        {pastAppointments.length === 0 ? (
          <div className="p-12 text-center text-text-secondary">No past visits</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-bg-elevated/50 border-b border-border-subtle">
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Service
                  </th>
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Provider
                  </th>
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Duration
                  </th>
                </tr>
              </thead>
              <tbody>
                {pastAppointments.slice(0, 20).map((apt) => (
                  <tr
                    key={apt.id}
                    className="border-b border-border-subtle/50 hover:bg-bg-elevated/50"
                  >
                    <td className="px-4 py-4 text-body-md text-text-primary">
                      {format(parseISO(apt.startTime), 'MMM d, yyyy h:mm a')}
                    </td>
                    <td className="px-4 py-4 text-body-md text-text-primary">{apt.service.name}</td>
                    <td className="px-4 py-4 text-body-md text-text-secondary">
                      Dr. {apt.dentist.fullName}
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge status={apt.status} />
                    </td>
                    <td className="px-4 py-4 text-body-md text-text-secondary tabular-nums">
                      {calculateDuration(apt.startTime, apt.endTime)} min
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function StatItem({
  label,
  value,
  icon: Icon,
  color = 'text-text-primary',
}: {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color?: string;
}) {
  return (
    <div className="flex items-center gap-4">
      <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', `${color}/10`)}>
        <Icon className={cn('w-5 h-5', color)} />
      </div>
      <div>
        <p className="text-stat-metric text-text-primary">{value}</p>
        <p className="text-label-sm text-text-muted">{label}</p>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: AppointmentStatus }) {
  const config: Record<AppointmentStatus, { label: string; className: string }> = {
    SCHEDULED: { label: 'Scheduled', className: 'bg-status-info-bg text-status-info' },
    CONFIRMED: { label: 'Confirmed', className: 'bg-brand-primary/10 text-brand-primary' },
    CHECKED_IN: { label: 'Checked In', className: 'bg-status-warning-bg text-status-warning' },
    IN_PROGRESS: { label: 'In Progress', className: 'bg-brand-primary text-brand-on-primary' },
    COMPLETED: { label: 'Completed', className: 'bg-status-success-bg text-status-success' },
    CANCELLED: { label: 'Cancelled', className: 'bg-status-error-bg text-status-error' },
    NO_SHOW: { label: 'No Show', className: 'bg-status-error-bg text-status-error' },
  };

  const { label, className } = config[status] || {
    label: status,
    className: 'bg-border-subtle text-text-secondary',
  };

  return (
    <span className={cn('px-2.5 py-1 rounded-full text-label-xs font-medium', className)}>
      {label}
    </span>
  );
}

function calculateAge(dateOfBirth: string): number {
  const today = new Date();
  const birth = new Date(dateOfBirth);
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
}

function calculateDuration(start: string, end: string): number {
  const startTime = new Date(start).getTime();
  const endTime = new Date(end).getTime();
  return Math.round((endTime - startTime) / 60000);
}
