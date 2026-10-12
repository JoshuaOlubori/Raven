import { useQueryClient } from '@tanstack/react-query';
import { endOfDay, format, parseISO, startOfDay } from 'date-fns';
import {
  Calendar,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Search,
  Stethoscope,
  User,
} from 'lucide-react';
import { useState } from 'react';
import { appointmentApi } from '@/lib/api-client';
import { useAppointments, useDentists } from '@/lib/hooks';
import { cn } from '@/lib/utils';

export function TodayPage() {
  const queryClient = useQueryClient();
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dentistFilter, setDentistFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: dentists } = useDentists();

  const {
    data: appointments,
    isLoading,
    refetch,
  } = useAppointments({
    startDate: format(startOfDay(selectedDate), 'yyyy-MM-dd'),
    endDate: format(endOfDay(selectedDate), 'yyyy-MM-dd'),
    dentistId: dentistFilter !== 'all' ? dentistFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
  });

  // Filter appointments by search query
  const filteredAppointments =
    appointments?.filter(
      (apt) =>
        apt.patient.fullName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        apt.service.name.toLowerCase().includes(searchQuery.toLowerCase())
    ) || [];

  // Stats
  const stats = {
    total: filteredAppointments.length,
    scheduled: filteredAppointments.filter((a) => a.status === 'SCHEDULED').length,
    confirmed: filteredAppointments.filter((a) => a.status === 'CONFIRMED').length,
    checkedIn: filteredAppointments.filter((a) => a.status === 'CHECKED_IN').length,
    inProgress: filteredAppointments.filter((a) => a.status === 'IN_PROGRESS').length,
    completed: filteredAppointments.filter((a) => a.status === 'COMPLETED').length,
    cancelled: filteredAppointments.filter((a) => a.status === 'CANCELLED').length,
    noShow: filteredAppointments.filter((a) => a.status === 'NO_SHOW').length,
  };

  const handleStatusChange = async (appointmentId: string, newStatus: string) => {
    try {
      await appointmentApi.updateStatus(appointmentId, { toStatus: newStatus as any });
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  };

  const formatTime = (dateString: string) => {
    return format(parseISO(dateString), 'h:mm a');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-headline-lg text-text-primary">Today's Operations</h1>
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
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total" value={stats.total} icon={Calendar} color="text-text-primary" />
        <StatCard
          label="Scheduled"
          value={stats.scheduled}
          icon={Clock}
          color="text-status-info"
          bgColor="bg-status-info-bg"
        />
        <StatCard
          label="In Progress"
          value={stats.inProgress + stats.checkedIn}
          icon={Stethoscope}
          color="text-brand-primary"
          bgColor="bg-brand-primary/10"
        />
        <StatCard
          label="Completed"
          value={stats.completed}
          icon={CheckCircle}
          color="text-status-success"
          bgColor="bg-status-success-bg"
        />
      </div>

      {/* Filters */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
            <input
              type="text"
              placeholder="Search patients, services..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border-default bg-bg-card text-text-primary placeholder-text-muted focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
            />
          </div>

          <div className="flex items-center gap-3">
            <label htmlFor="status-filter" className="text-label-sm text-text-muted">
              Status
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2.5 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
            >
              <option value="all">All Statuses</option>
              <option value="SCHEDULED">Scheduled</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="CHECKED_IN">Checked In</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
              <option value="NO_SHOW">No Show</option>
            </select>
          </div>

          <div className="flex items-center gap-3">
            <label htmlFor="dentist-filter" className="text-label-sm text-text-muted">
              Provider
            </label>
            <select
              id="dentist-filter"
              value={dentistFilter}
              onChange={(e) => setDentistFilter(e.target.value)}
              className="px-3 py-2.5 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
            >
              <option value="all">All Providers</option>
              {dentists?.map((d) => (
                <option key={d.id} value={d.id}>
                  Dr. {d.fullName}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => refetch()}
            className="px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium text-sm hover:bg-brand-primary-hover transition-colors flex items-center gap-2"
          >
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M23 4v6h-6" />
              <path d="M1 20v-6h6" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Appointments List */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-brand-primary border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-text-secondary">Loading appointments...</p>
          </div>
        ) : filteredAppointments.length === 0 ? (
          <div className="p-12 text-center">
            <Calendar className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-headline-md text-text-primary mb-2">No appointments</h3>
            <p className="text-text-secondary">No appointments found for the selected filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border-subtle bg-bg-elevated/50">
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Patient
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
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredAppointments.map((apt) => (
                  <tr
                    key={apt.id}
                    className="border-b border-border-subtle/50 hover:bg-bg-elevated/50 transition-colors"
                  >
                    <td className="px-4 py-4 text-body-md text-text-primary tabular-nums">
                      {formatTime(apt.startTime)} - {formatTime(apt.endTime)}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-brand-primary/10 flex items-center justify-center">
                          <User className="w-4 h-4 text-brand-primary" />
                        </div>
                        <div>
                          <p className="font-medium text-text-primary">{apt.patient.fullName}</p>
                          <p className="text-body-xs text-text-muted">{apt.patient.phone}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-body-md text-text-primary">{apt.service.name}</td>
                    <td className="px-4 py-4 text-body-md text-text-secondary">
                      Dr. {apt.dentist.fullName}
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge status={apt.status} />
                    </td>
                    <td className="px-4 py-4">
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

function StatCard({
  label,
  value,
  icon: Icon,
  color,
  bgColor = 'bg-bg-elevated',
}: {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor?: string;
}) {
  return (
    <div className={cn('rounded-xl p-5 border border-border-subtle', bgColor)}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-label-sm text-text-muted">{label}</p>
          <p className="text-stat-metric text-text-primary">{value}</p>
        </div>
        <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', color)}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
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
