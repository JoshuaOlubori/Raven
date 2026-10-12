import { Link, useParams } from '@tanstack/react-router';
import { format, parseISO } from 'date-fns';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Calendar,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  Package,
  Plus,
  Stethoscope,
  User,
  X,
} from 'lucide-react';
import { useState } from 'react';
import {
  useAppointment,
  useAuditLogs,
  useCancelAppointment,
  useRescheduleAppointment,
  useUpdateAppointmentStatus,
} from '@/lib/hooks';
import { cn } from '@/lib/utils';
import type { AppointmentStatus } from '@/types/api';

export function AppointmentDetailPage() {
  const { id } = useParams({ from: '/appointments/$id' });
  const { data: appointment, isLoading } = useAppointment(id);
  const { data: auditLogs } = useAuditLogs(id);
  const updateStatusMutation = useUpdateAppointmentStatus();
  const rescheduleMutation = useRescheduleAppointment();
  const cancelMutation = useCancelAppointment();
  const [showAuditLogs, setShowAuditLogs] = useState(true);
  const [showReschedule, setShowReschedule] = useState(false);
  const [showCancel, setShowCancel] = useState(false);
  const [rescheduleData, setRescheduleData] = useState({ startTime: '', dentistId: '' });
  const [cancelReason, setCancelReason] = useState('');

  const handleStatusChange = async (newStatus: AppointmentStatus) => {
    try {
      await updateStatusMutation.mutateAsync({ id, data: { toStatus: newStatus } });
    } catch (error) {
      console.error('Failed to update status:', error);
      alert('Failed to update status');
    }
  };

  const handleReschedule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await rescheduleMutation.mutateAsync({
        id,
        data: {
          startTime: new Date(rescheduleData.startTime).toISOString(),
          dentistId: rescheduleData.dentistId || undefined,
        },
      });
      setShowReschedule(false);
    } catch (error) {
      console.error('Failed to reschedule:', error);
      alert('Failed to reschedule appointment');
    }
  };

  const handleCancel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cancelReason.trim()) {
      alert('Cancellation reason is required');
      return;
    }
    try {
      await cancelMutation.mutateAsync({ id, data: { cancellationReason: cancelReason } });
      setShowCancel(false);
      setCancelReason('');
    } catch (error) {
      console.error('Failed to cancel:', error);
      alert('Failed to cancel appointment');
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-border-subtle rounded w-1/4" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-64 bg-border-subtle rounded-xl" />
          <div className="h-64 bg-border-subtle rounded-xl" />
        </div>
      </div>
    );
  }

  if (!appointment) {
    return (
      <div className="text-center py-12">
        <Calendar className="w-12 h-12 text-text-muted mx-auto mb-4" />
        <h2 className="text-headline-md text-text-primary mb-2">Appointment not found</h2>
        <Link to="/appointments" className="text-brand-primary hover:underline">
          Back to appointments
        </Link>
      </div>
    );
  }

  const nextActions = getNextStatusActions(appointment.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link
            to="/appointments"
            className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-text-primary"
            aria-label="Back to appointments"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-headline-lg text-text-primary">
              {appointment.patient.fullName} - {appointment.service.name}
            </h1>
            <p className="text-text-secondary text-body-md">
              Dr. {appointment.dentist.fullName} •{' '}
              {format(parseISO(appointment.startTime), 'EEEE, MMMM d, yyyy')}
            </p>
          </div>
        </div>
        <StatusBadge status={appointment.status} large />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Appointment Info */}
          <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-6">
            <h2 className="text-title-sm text-text-primary mb-5 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-brand-primary" />
              Appointment Details
            </h2>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-label-xs text-text-muted uppercase tracking-wider">
                  Date & Time
                </dt>
                <dd className="text-body-md text-text-primary flex items-center gap-2">
                  <Clock className="w-4 h-4 text-text-muted" />
                  {format(parseISO(appointment.startTime), "EEEE, MMMM d, yyyy 'at' h:mm a")} -
                  {format(parseISO(appointment.endTime), 'h:mm a')}
                </dd>
              </div>
              <div>
                <dt className="text-label-xs text-text-muted uppercase tracking-wider">Duration</dt>
                <dd className="text-body-md text-text-primary tabular-nums">
                  {calculateDuration(appointment.startTime, appointment.endTime)} minutes
                </dd>
              </div>
              <div>
                <dt className="text-label-xs text-text-muted uppercase tracking-wider">Patient</dt>
                <dd className="text-body-md text-text-primary flex items-center gap-2">
                  <User className="w-4 h-4 text-text-muted" />
                  <Link
                    to={`/patients/${appointment.patient.id}` as any}
                    className="hover:underline"
                  >
                    {appointment.patient.fullName}
                  </Link>
                </dd>
              </div>
              <div>
                <dt className="text-label-xs text-text-muted uppercase tracking-wider">Provider</dt>
                <dd className="text-body-md text-text-primary flex items-center gap-2">
                  <Stethoscope className="w-4 h-4 text-text-muted" />
                  Dr. {appointment.dentist.fullName}
                </dd>
              </div>
              <div>
                <dt className="text-label-xs text-text-muted uppercase tracking-wider">Service</dt>
                <dd className="text-body-md text-text-primary flex items-center gap-2">
                  <Package className="w-4 h-4 text-text-muted" />
                  {appointment.service.name}
                  {appointment.service.description && (
                    <span className="text-text-muted"> - {appointment.service.description}</span>
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-label-xs text-text-muted uppercase tracking-wider">Status</dt>
                <dd className="text-body-md text-text-primary">
                  <StatusBadge status={appointment.status} />
                </dd>
              </div>
              {appointment.cancellationReason && (
                <div className="md:col-span-2">
                  <dt className="text-label-xs text-text-muted uppercase tracking-wider">
                    Cancellation Reason
                  </dt>
                  <dd className="text-body-md text-status-error">
                    {appointment.cancellationReason}
                  </dd>
                </div>
              )}
            </dl>
          </div>

          {/* Actions */}
          {nextActions.length > 0 && (
            <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-6">
              <h2 className="text-title-sm text-text-primary mb-5">Actions</h2>
              <div className="flex flex-wrap gap-3">
                {nextActions.map((action) => (
                  <button
                    key={action}
                    onClick={() => handleStatusChange(action as AppointmentStatus)}
                    className={cn(
                      'px-4 py-2 rounded-lg font-medium transition-colors',
                      action === 'CANCELLED'
                        ? 'bg-status-error/10 text-status-error hover:bg-status-error/20'
                        : action === 'COMPLETED'
                          ? 'bg-brand-primary text-brand-on-primary hover:bg-brand-primary-hover'
                          : 'bg-bg-elevated border border-border-default text-text-primary hover:bg-border-subtle'
                    )}
                  >
                    {action.replace('_', ' ')}
                  </button>
                ))}
                {appointment.status !== 'CANCELLED' &&
                  appointment.status !== 'NO_SHOW' &&
                  appointment.status !== 'COMPLETED' && (
                    <>
                      <button
                        onClick={() => setShowReschedule(true)}
                        className="px-4 py-2 rounded-lg border border-border-default text-text-secondary hover:bg-bg-elevated font-medium transition-colors"
                      >
                        Reschedule
                      </button>
                      <button
                        onClick={() => setShowCancel(true)}
                        className="px-4 py-2 rounded-lg bg-status-error/10 text-status-error hover:bg-status-error/20 font-medium transition-colors"
                      >
                        Cancel
                      </button>
                    </>
                  )}
              </div>
            </div>
          )}

          {/* Audit Logs */}
          <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle">
            <div className="p-6 border-b border-border-subtle flex items-center justify-between">
              <h2 className="text-title-sm text-text-primary flex items-center gap-2">
                <FileText className="w-5 h-5 text-brand-primary" />
                Audit History
              </h2>
              <button
                onClick={() => setShowAuditLogs(!showAuditLogs)}
                className="text-sm text-brand-primary hover:underline flex items-center gap-1"
              >
                {showAuditLogs ? (
                  <>
                    <ChevronUp className="w-4 h-4" />
                    Collapse
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    Expand
                  </>
                )}
              </button>
            </div>
            {showAuditLogs && (
              <div className="p-6">
                {auditLogs && auditLogs.length > 0 ? (
                  <div className="space-y-4">
                    {auditLogs.map((log) => (
                      <AuditLogEntry key={log.id} log={log} />
                    ))}
                  </div>
                ) : (
                  <p className="text-text-secondary text-center py-4">No audit history available</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Quick Info */}
        <div className="space-y-6">
          {/* Patient Quick Info */}
          <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-6">
            <h2 className="text-title-sm text-text-primary mb-5">Patient</h2>
            <Link
              to={`/patients/${appointment.patient.id}` as any}
              className="flex items-center gap-3"
            >
              <div className="w-12 h-12 rounded-full bg-brand-primary/10 flex items-center justify-center">
                <User className="w-6 h-6 text-brand-primary" />
              </div>
              <div>
                <p className="font-medium text-text-primary">{appointment.patient.fullName}</p>
                <p className="text-body-sm text-text-muted">{appointment.patient.phone}</p>
                {appointment.patient.email && (
                  <p className="text-body-xs text-text-muted">{appointment.patient.email}</p>
                )}
              </div>
            </Link>
            {appointment.patient.medicalAlerts && (
              <div className="mt-4 p-3 rounded-lg bg-status-warning-bg border border-status-warning/30">
                <p className="text-label-xs text-status-warning font-medium flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Medical Alert
                </p>
                <p className="text-body-sm text-status-warning mt-1">
                  {appointment.patient.medicalAlerts}
                </p>
              </div>
            )}
          </div>

          {/* Service Info */}
          <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-6">
            <h2 className="text-title-sm text-text-primary mb-5">Service</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Package className="w-5 h-5 text-brand-primary" />
                <div>
                  <p className="font-medium text-text-primary">{appointment.service.name}</p>
                  <p className="text-body-sm text-text-muted">
                    {appointment.service.durationMinutes} minutes
                  </p>
                </div>
              </div>
              {appointment.service.description && (
                <p className="text-body-sm text-text-secondary pl-8">
                  {appointment.service.description}
                </p>
              )}
            </div>
          </div>

          {/* Provider Info */}
          <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-6">
            <h2 className="text-title-sm text-text-primary mb-5">Provider</h2>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-brand-primary/10 flex items-center justify-center">
                <Stethoscope className="w-6 h-6 text-brand-primary" />
              </div>
              <div>
                <p className="font-medium text-text-primary">Dr. {appointment.dentist.fullName}</p>
                <p className="text-body-sm text-text-muted">{appointment.dentist.role}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Reschedule Modal */}
      {showReschedule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-bg-card rounded-2xl shadow-elev-2 w-full max-w-md p-6">
            <h2 className="text-headline-md text-text-primary mb-6">Reschedule Appointment</h2>
            <form onSubmit={handleReschedule} className="space-y-4">
              <div>
                <label
                  htmlFor="rescheduleTime"
                  className="block text-label-md text-text-primary mb-1.5"
                >
                  New Date & Time *
                </label>
                <input
                  type="datetime-local"
                  id="rescheduleTime"
                  value={rescheduleData.startTime}
                  onChange={(e) =>
                    setRescheduleData({ ...rescheduleData, startTime: e.target.value })
                  }
                  required
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                />
              </div>
              <div>
                <label
                  htmlFor="rescheduleDentist"
                  className="block text-label-md text-text-primary mb-1.5"
                >
                  Provider (optional)
                </label>
                <select
                  id="rescheduleDentist"
                  value={rescheduleData.dentistId}
                  onChange={(e) =>
                    setRescheduleData({ ...rescheduleData, dentistId: e.target.value })
                  }
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                >
                  <option value="">Keep current provider</option>
                  {/* Would need dentists list here */}
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowReschedule(false)}
                  className="px-4 py-2.5 rounded-lg border border-border-default text-text-secondary hover:bg-bg-elevated font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors"
                >
                  Reschedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cancel Modal */}
      {showCancel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-bg-card rounded-2xl shadow-elev-2 w-full max-w-md p-6">
            <h2 className="text-headline-md text-text-primary mb-6">Cancel Appointment</h2>
            <form onSubmit={handleCancel} className="space-y-4">
              <div>
                <label
                  htmlFor="cancelReason"
                  className="block text-label-md text-text-primary mb-1.5"
                >
                  Reason for Cancellation *
                </label>
                <textarea
                  id="cancelReason"
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  rows={4}
                  required
                  placeholder="Please provide a reason for cancellation..."
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors resize-y"
                />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCancel(false)}
                  className="px-4 py-2.5 rounded-lg border border-border-default text-text-secondary hover:bg-bg-elevated font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2.5 rounded-lg bg-status-error text-status-on-error font-medium hover:bg-status-error/90 transition-colors"
                >
                  Confirm Cancellation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function AuditLogEntry({ log }: { log: any }) {
  const getActionIcon = (fromStatus: string | null, toStatus: string | null) => {
    if (!fromStatus && toStatus) return <Plus className="w-4 h-4 text-status-success" />;
    if (fromStatus && !toStatus) return <X className="w-4 h-4 text-status-error" />;
    return <ArrowRight className="w-4 h-4 text-brand-primary" />;
  };

  return (
    <div className="flex gap-4 pb-4 border-b border-border-subtle/50 last:border-0 last:pb-0">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-bg-elevated flex items-center justify-center">
        {getActionIcon(log.fromStatus, log.toStatus)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium text-text-primary">{log.actorName}</p>
          <p className="text-body-xs text-text-muted">
            {format(parseISO(log.createdAt), 'MMM d, yyyy h:mm a')}
          </p>
        </div>
        <p className="text-body-sm text-text-secondary">
          {log.fromStatus && log.toStatus && (
            <>
              <span
                className={cn(
                  'px-1.5 py-0.5 rounded text-label-xs font-medium',
                  getStatusColor(log.fromStatus)
                )}
              >
                {log.fromStatus}
              </span>
              <ArrowRight className="w-3 h-3 mx-1 text-text-muted" />
              <span
                className={cn(
                  'px-1.5 py-0.5 rounded text-label-xs font-medium',
                  getStatusColor(log.toStatus)
                )}
              >
                {log.toStatus}
              </span>
            </>
          )}
          {log.note && <span className="text-text-muted"> - {log.note}</span>}
          {log.oldStartTime && log.newStartTime && (
            <>
              <span className="text-text-muted"> Rescheduled from </span>
              <span className="font-medium">
                {format(parseISO(log.oldStartTime), 'MMM d, h:mm a')}
              </span>
              <span className="text-text-muted"> to </span>
              <span className="font-medium">
                {format(parseISO(log.newStartTime), 'MMM d, h:mm a')}
              </span>
            </>
          )}
        </p>
      </div>
    </div>
  );
}

function StatusBadge({ status, large = false }: { status: AppointmentStatus; large?: boolean }) {
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
    <span
      className={cn(
        'px-3 py-1 rounded-full font-medium',
        large ? 'text-sm' : 'text-label-xs',
        className
      )}
    >
      {label}
    </span>
  );
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    SCHEDULED: 'bg-status-info-bg text-status-info',
    CONFIRMED: 'bg-brand-primary/10 text-brand-primary',
    CHECKED_IN: 'bg-status-warning-bg text-status-warning',
    IN_PROGRESS: 'bg-brand-primary text-brand-on-primary',
    COMPLETED: 'bg-status-success-bg text-status-success',
    CANCELLED: 'bg-status-error-bg text-status-error',
    NO_SHOW: 'bg-status-error-bg text-status-error',
  };
  return colors[status] || 'bg-border-subtle text-text-secondary';
}

function getNextStatusActions(currentStatus: AppointmentStatus): AppointmentStatus[] {
  const transitions: Record<AppointmentStatus, AppointmentStatus[]> = {
    SCHEDULED: ['CONFIRMED', 'CANCELLED'],
    CONFIRMED: ['CHECKED_IN', 'CANCELLED'],
    CHECKED_IN: ['IN_PROGRESS', 'CANCELLED'],
    IN_PROGRESS: ['COMPLETED', 'CANCELLED'],
    COMPLETED: [],
    CANCELLED: [],
    NO_SHOW: [],
  };
  return transitions[currentStatus] || [];
}

function calculateDuration(start: string, end: string): number {
  const startTime = new Date(start).getTime();
  const endTime = new Date(end).getTime();
  return Math.round((endTime - startTime) / 60000);
}
