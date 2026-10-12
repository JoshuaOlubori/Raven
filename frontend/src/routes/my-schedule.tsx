import { useQueryClient } from '@tanstack/react-query';
import { endOfDay, format, parseISO, startOfDay } from 'date-fns';
import {
  AlertTriangle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Clock,
  Plus,
  Stethoscope,
  Sun,
  Trash2,
} from 'lucide-react';
import { useState } from 'react';
import { appointmentApi } from '@/lib/api-client';
import { useAuthStore } from '@/lib/auth-store';
import { useAppointments, useCreateTimeOff, useDeleteTimeOff, useTimeOff } from '@/lib/hooks';
import { cn } from '@/lib/utils';

export function MySchedulePage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [showTimeOffModal, setShowTimeOffModal] = useState(false);
  const [timeOffForm, setTimeOffForm] = useState({
    startTime: '',
    endTime: '',
    reason: '',
  });

  const dentistId = user?.id || '';
  const dayStart = format(startOfDay(selectedDate), 'yyyy-MM-dd');
  const dayEnd = format(endOfDay(selectedDate), 'yyyy-MM-dd');
  const { data: appointments, isLoading: apptsLoading } = useAppointments({
    dentistId,
    startDate: dayStart,
    endDate: dayEnd,
  });
  const { data: timeOff } = useTimeOff(dentistId, dayStart, dayEnd);

  const createTimeOffMutation = useCreateTimeOff();
  const deleteTimeOffMutation = useDeleteTimeOff();

  const handleStatusChange = async (appointmentId: string, newStatus: string) => {
    try {
      await appointmentApi.updateStatus(appointmentId, { toStatus: newStatus as any });
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  };

  const handleCreateTimeOff = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createTimeOffMutation.mutateAsync({
        dentistId,
        startTime: new Date(timeOffForm.startTime).toISOString(),
        endTime: new Date(timeOffForm.endTime).toISOString(),
        reason: timeOffForm.reason,
      });
      setShowTimeOffModal(false);
      setTimeOffForm({ startTime: '', endTime: '', reason: '' });
      queryClient.invalidateQueries({ queryKey: ['schedules', 'timeOff'] });
    } catch (error) {
      console.error('Failed to create time off:', error);
      alert('Failed to create time off block');
    }
  };

  const handleDeleteTimeOff = async (id: string) => {
    if (confirm('Delete this time off block?')) {
      try {
        await deleteTimeOffMutation.mutateAsync(id);
        queryClient.invalidateQueries({ queryKey: ['schedules', 'timeOff'] });
      } catch (error) {
        console.error('Failed to delete time off:', error);
        alert('Failed to delete time off block');
      }
    }
  };

  const formatTime = (dateString: string) => format(parseISO(dateString), 'h:mm a');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-headline-lg text-text-primary">My Schedule</h1>
          <p className="text-text-secondary text-body-md">
            {format(selectedDate, 'EEEE, MMMM d, yyyy')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSelectedDate((d) => new Date(d.getTime() - 86400000))}
            className="p-2 rounded-lg border border-border-default hover:bg-bg-elevated transition-colors"
            aria-label="Previous day"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={() => setSelectedDate(new Date())}
            className="px-4 py-2 rounded-lg border border-border-default hover:bg-bg-elevated transition-colors text-sm font-medium"
          >
            Today
          </button>
          <button
            onClick={() => setSelectedDate((d) => new Date(d.getTime() + 86400000))}
            className="p-2 rounded-lg border border-border-default hover:bg-bg-elevated transition-colors"
            aria-label="Next day"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
          <button
            onClick={() => setShowTimeOffModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Time Off
          </button>
        </div>
      </div>

      {/* Time Off Blocks */}
      {timeOff && timeOff.length > 0 && (
        <div className="bg-status-warning-bg border border-status-warning/30 rounded-xl p-4">
          <h3 className="text-title-sm text-status-warning flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5" />
            Time Off Blocks
          </h3>
          <div className="space-y-2">
            {timeOff.map((block) => (
              <div
                key={block.id}
                className="flex items-center justify-between p-3 bg-white rounded-lg border border-border-subtle"
              >
                <div className="flex items-center gap-3">
                  <Sun className="w-5 h-5 text-status-warning" />
                  <div>
                    <p className="font-medium text-text-primary">{block.reason || 'Time Off'}</p>
                    <p className="text-body-sm text-text-muted">
                      {format(parseISO(block.startTime), 'h:mm a')} -{' '}
                      {format(parseISO(block.endTime), 'h:mm a')}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteTimeOff(block.id)}
                  className="p-2 rounded-lg hover:bg-status-error/10 text-text-muted hover:text-status-error transition-colors"
                  aria-label="Delete time off"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Appointments */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle overflow-hidden">
        {apptsLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-brand-primary border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-text-secondary">Loading schedule...</p>
          </div>
        ) : appointments && appointments.length === 0 ? (
          <div className="p-12 text-center">
            <Calendar className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-headline-md text-text-primary mb-2">No appointments</h3>
            <p className="text-text-secondary">No appointments scheduled for this day.</p>
          </div>
        ) : (
          <div className="divide-y divide-border-subtle/50">
            {appointments?.map((apt) => (
              <div key={apt.id} className="p-4 hover:bg-bg-elevated/50 transition-colors">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div
                      className={cn(
                        'w-16 h-16 rounded-xl flex items-center justify-center flex-shrink-0',
                        apt.status === 'COMPLETED' && 'bg-status-success-bg',
                        apt.status === 'IN_PROGRESS' && 'bg-brand-primary/10',
                        apt.status === 'CHECKED_IN' && 'bg-status-warning-bg',
                        apt.status === 'CONFIRMED' && 'bg-brand-primary/10',
                        apt.status === 'SCHEDULED' && 'bg-status-info-bg',
                        apt.status === 'CANCELLED' && 'bg-status-error-bg',
                        apt.status === 'NO_SHOW' && 'bg-status-error-bg'
                      )}
                    >
                      <Stethoscope
                        className={cn(
                          'w-7 h-7',
                          apt.status === 'COMPLETED' && 'text-status-success',
                          apt.status === 'IN_PROGRESS' && 'text-brand-primary',
                          apt.status === 'CHECKED_IN' && 'text-status-warning',
                          apt.status === 'CONFIRMED' && 'text-brand-primary',
                          apt.status === 'SCHEDULED' && 'text-status-info',
                          apt.status === 'CANCELLED' && 'text-status-error',
                          apt.status === 'NO_SHOW' && 'text-status-error'
                        )}
                      />
                    </div>
                    <div>
                      <p className="font-medium text-text-primary text-lg">
                        {apt.patient.fullName}
                      </p>
                      <p className="text-text-secondary">{apt.service.name}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-body-md text-text-secondary">
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-4 h-4" />
                      {formatTime(apt.startTime)} - {formatTime(apt.endTime)}
                    </span>
                    <StatusBadge status={apt.status} />
                  </div>

                  <div className="flex items-center gap-2">
                    {getNextStatusActions(apt.status).map((action) => (
                      <button
                        key={action}
                        onClick={() => handleStatusChange(apt.id, action)}
                        className="px-3 py-1.5 text-xs font-medium rounded-full border transition-colors hover:bg-bg-elevated"
                      >
                        {action.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Time Off Modal */}
      {showTimeOffModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-bg-card rounded-2xl shadow-elev-2 w-full max-w-md p-6">
            <h2 className="text-headline-md text-text-primary mb-6">Add Time Off</h2>
            <form onSubmit={handleCreateTimeOff} className="space-y-4">
              <div>
                <label htmlFor="startTime" className="block text-label-md text-text-primary mb-1.5">
                  Start Time *
                </label>
                <input
                  type="datetime-local"
                  id="startTime"
                  value={timeOffForm.startTime}
                  onChange={(e) => setTimeOffForm({ ...timeOffForm, startTime: e.target.value })}
                  required
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                />
              </div>
              <div>
                <label htmlFor="endTime" className="block text-label-md text-text-primary mb-1.5">
                  End Time *
                </label>
                <input
                  type="datetime-local"
                  id="endTime"
                  value={timeOffForm.endTime}
                  onChange={(e) => setTimeOffForm({ ...timeOffForm, endTime: e.target.value })}
                  required
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                />
              </div>
              <div>
                <label htmlFor="reason" className="block text-label-md text-text-primary mb-1.5">
                  Reason (optional)
                </label>
                <input
                  type="text"
                  id="reason"
                  value={timeOffForm.reason}
                  onChange={(e) => setTimeOffForm({ ...timeOffForm, reason: e.target.value })}
                  placeholder="Vacation, Conference, Personal, etc."
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                />
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowTimeOffModal(false)}
                  className="px-4 py-2.5 rounded-lg border border-border-default text-text-secondary hover:bg-bg-elevated font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors"
                >
                  Add Time Off
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
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

function getNextStatusActions(currentStatus: string): string[] {
  const transitions: Record<string, string[]> = {
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
