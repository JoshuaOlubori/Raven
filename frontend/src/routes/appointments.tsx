import { Link } from '@tanstack/react-router';
import {
  addDays,
  addWeeks,
  endOfWeek,
  format,
  isSameDay,
  parseISO,
  startOfWeek,
  subDays,
  subWeeks,
} from 'date-fns';
import { ChevronLeft, ChevronRight, Plus, Search } from 'lucide-react';
import { useState } from 'react';
import { useAppointments, useDentists } from '@/lib/hooks';
import { cn } from '@/lib/utils';

export function AppointmentsPage() {
  const [view, setView] = useState<'week' | 'day'>('week');
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dentistFilter, setDentistFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: dentists } = useDentists();

  // Get week boundaries
  const weekStart = startOfWeek(selectedDate, { weekStartsOn: 1 }); // Monday
  const weekEnd = endOfWeek(selectedDate, { weekStartsOn: 1 });

  const { data: appointments, isLoading } = useAppointments({
    dentistId: dentistFilter !== 'all' ? dentistFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    startDate: weekStart.toISOString(),
    endDate: weekEnd.toISOString(),
  });

  // Filter appointments
  const filteredAppointments =
    appointments?.filter(
      (apt) =>
        apt.patient.fullName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        apt.service.name.toLowerCase().includes(searchQuery.toLowerCase())
    ) || [];

  // Group by day and dentist
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const activeDentists = dentists || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-headline-lg text-text-primary">Appointments Calendar</h1>
          <p className="text-text-secondary text-body-md">
            {view === 'week'
              ? `${format(weekStart, 'MMM d')} - ${format(weekEnd, 'MMM d, yyyy')}`
              : format(selectedDate, 'EEEE, MMMM d, yyyy')}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() =>
              setSelectedDate(
                view === 'week' ? subWeeks(selectedDate, 1) : subDays(selectedDate, 1)
              )
            }
            className="p-2 rounded-lg border border-border-default hover:bg-bg-elevated transition-colors"
            aria-label={view === 'week' ? 'Previous week' : 'Previous day'}
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
            onClick={() =>
              setSelectedDate(
                view === 'week' ? addWeeks(selectedDate, 1) : addDays(selectedDate, 1)
              )
            }
            className="p-2 rounded-lg border border-border-default hover:bg-bg-elevated transition-colors"
            aria-label={view === 'week' ? 'Next week' : 'Next day'}
          >
            <ChevronRight className="w-5 h-5" />
          </button>

          <div className="hidden sm:flex items-center gap-2 border border-border-default rounded-lg overflow-hidden">
            <button
              onClick={() => setView('day')}
              className={cn(
                'px-3 py-2 text-sm font-medium transition-colors',
                view === 'day'
                  ? 'bg-brand-primary text-brand-on-primary'
                  : 'text-text-secondary hover:bg-bg-elevated'
              )}
            >
              Day
            </button>
            <button
              onClick={() => setView('week')}
              className={cn(
                'px-3 py-2 text-sm font-medium transition-colors',
                view === 'week'
                  ? 'bg-brand-primary text-brand-on-primary'
                  : 'text-text-secondary hover:bg-bg-elevated'
              )}
            >
              Week
            </button>
          </div>

          <Link
            to="/appointments/new"
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors hidden sm:flex"
          >
            <Plus className="w-4 h-4" />
            New Appointment
          </Link>
        </div>
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

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <label htmlFor="status-filter" className="text-label-sm text-text-muted">
                Status
              </label>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2.5 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
              >
                <option value="all">All</option>
                <option value="SCHEDULED">Scheduled</option>
                <option value="CONFIRMED">Confirmed</option>
                <option value="CHECKED_IN">Checked In</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="COMPLETED">Completed</option>
                <option value="CANCELLED">Cancelled</option>
                <option value="NO_SHOW">No Show</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
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

            <Link
              to="/appointments/new"
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors sm:hidden"
            >
              <Plus className="w-4 h-4" />
              New Appointment
            </Link>
          </div>
        </div>
      </div>

      {/* Calendar View */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-brand-primary border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-text-secondary">Loading appointments...</p>
          </div>
        ) : view === 'week' ? (
          <WeekView days={days} appointments={filteredAppointments} />
        ) : (
          <DayView
            date={selectedDate}
            appointments={filteredAppointments.filter((a) =>
              isSameDay(parseISO(a.startTime), selectedDate)
            )}
            dentists={activeDentists}
          />
        )}
      </div>
    </div>
  );
}

function WeekView({ days, appointments }: { days: Date[]; appointments: any[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[1000px]">
        <thead>
          <tr className="border-b border-border-subtle bg-bg-elevated/50">
            <th className="w-32 px-2 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
              Time
            </th>
            {days.map((day) => (
              <th key={day.toISOString()} className="px-2 py-3 text-center">
                <div
                  className={cn(
                    'rounded-lg px-2 py-2',
                    isSameDay(day, new Date()) && 'bg-brand-primary/10'
                  )}
                >
                  <p className="text-label-sm font-medium text-text-primary">
                    {format(day, 'EEE')}
                  </p>
                  <p
                    className={cn(
                      'text-body-md font-semibold',
                      isSameDay(day, new Date()) ? 'text-brand-primary' : 'text-text-primary'
                    )}
                  >
                    {format(day, 'd')}
                  </p>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {/* Time slots from 7am to 7pm */}
          {Array.from({ length: 12 }, (_, i) => i + 7).map((hour) => (
            <tr key={hour} className="border-b border-border-subtle/50">
              <td className="w-32 px-2 py-1 text-right text-label-sm text-text-muted pr-3">
                {format(new Date(2000, 0, 1, hour), 'h a')}
              </td>
              {days.map((day) => (
                <td key={day.toISOString()} className="px-1 py-1 relative min-h-[80px]">
                  {appointments
                    .filter((apt) => {
                      const aptDate = parseISO(apt.startTime);
                      const aptHour = aptDate.getHours();
                      return isSameDay(aptDate, day) && aptHour === hour;
                    })
                    .map((apt) => (
                      <Link
                        key={apt.id}
                        to={`/appointments/${apt.id}` as any}
                        className={cn(
                          'absolute left-1 right-1 mb-1 p-2 rounded-lg text-xs transition-colors',
                          'hover:shadow-elev-1 hover:z-10',
                          getStatusColor(apt.status)
                        )}
                        style={{ top: `${(parseISO(apt.startTime).getMinutes() / 60) * 100}%` }}
                      >
                        <p className="font-medium truncate">{apt.patient.fullName}</p>
                        <p className="text-xs opacity-80 truncate">{apt.service.name}</p>
                        <p className="text-xs opacity-70">Dr. {apt.dentist.fullName}</p>
                      </Link>
                    ))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DayView({
  date,
  appointments,
  dentists,
}: {
  date: Date;
  appointments: any[];
  dentists: any[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[800px]">
        <thead>
          <tr className="border-b border-border-subtle bg-bg-elevated/50">
            <th className="w-32 px-2 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
              Time
            </th>
            {dentists.map((dentist) => (
              <th key={dentist.id} className="px-2 py-3 text-center">
                <div className="rounded-lg px-2 py-2">
                  <p className="text-label-sm font-medium text-text-primary">
                    Dr. {dentist.fullName}
                  </p>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 12 }, (_, i) => i + 7).map((hour) => (
            <tr key={hour} className="border-b border-border-subtle/50">
              <td className="w-32 px-2 py-1 text-right text-label-sm text-text-muted pr-3">
                {format(new Date(2000, 0, 1, hour), 'h a')}
              </td>
              {dentists.map((dentist) => (
                <td key={dentist.id} className="px-1 py-1 relative min-h-[80px]">
                  {appointments
                    .filter((apt) => {
                      const aptDate = parseISO(apt.startTime);
                      const aptHour = aptDate.getHours();
                      return (
                        isSameDay(aptDate, date) && aptHour === hour && apt.dentistId === dentist.id
                      );
                    })
                    .map((apt) => (
                      <Link
                        key={apt.id}
                        to={`/appointments/${apt.id}` as any}
                        className={cn(
                          'absolute left-1 right-1 mb-1 p-2 rounded-lg text-xs transition-colors',
                          'hover:shadow-elev-1 hover:z-10',
                          getStatusColor(apt.status)
                        )}
                        style={{ top: `${(parseISO(apt.startTime).getMinutes() / 60) * 100}%` }}
                      >
                        <p className="font-medium truncate">{apt.patient.fullName}</p>
                        <p className="text-xs opacity-80 truncate">{apt.service.name}</p>
                      </Link>
                    ))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    SCHEDULED: 'bg-status-info-bg text-status-info border border-status-info/30',
    CONFIRMED: 'bg-brand-primary/10 text-brand-primary border border-brand-primary/30',
    CHECKED_IN: 'bg-status-warning-bg text-status-warning border border-status-warning/30',
    IN_PROGRESS: 'bg-brand-primary text-brand-on-primary',
    COMPLETED: 'bg-status-success-bg text-status-success border border-status-success/30',
    CANCELLED: 'bg-status-error-bg text-status-error border border-status-error/30',
    NO_SHOW: 'bg-status-error-bg text-status-error border border-status-error/30',
  };
  return colors[status] || 'bg-border-subtle text-text-secondary';
}
