import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import {
  addDays,
  addWeeks,
  endOfDay,
  format,
  isSameDay,
  parseISO,
  startOfDay,
  startOfWeek,
  subWeeks,
} from 'date-fns';
import {
  AlertTriangle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Clock,
  Grid,
  List,
  Plus,
  Sun,
  Trash2,
} from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import {
  useAvailability,
  useCreateTimeOff,
  useDeleteTimeOff,
  useDentists,
  useServices,
  useShifts,
  useTimeOff,
} from '@/lib/hooks';
import { cn } from '@/lib/utils';

const timeOffSchema = z.object({
  dentistId: z.string().uuid('Please select a provider'),
  startTime: z.string().min(1, 'Start time is required'),
  endTime: z.string().min(1, 'End time is required'),
  reason: z.string().optional(),
});

type TimeOffForm = z.infer<typeof timeOffSchema>;

export function ProviderSchedulesPage() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<'week' | 'availability'>('week');
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [selectedDentist, setSelectedDentist] = useState<string>('all');
  const [selectedService, setSelectedService] = useState<string>('');
  const [showTimeOffModal, setShowTimeOffModal] = useState(false);

  const { data: dentists } = useDentists();
  const { data: services } = useServices();
  const { data: shifts } = useShifts();
  const { data: timeOff } = useTimeOff(
    selectedDentist !== 'all' ? selectedDentist : '',
    format(startOfDay(selectedDate), 'yyyy-MM-dd'),
    format(endOfDay(selectedDate), 'yyyy-MM-dd')
  );

  const { data: availability } = useAvailability(
    {
      serviceId: selectedService,
      date: format(selectedDate, 'yyyy-MM-dd'),
      dentistId: selectedDentist !== 'all' ? selectedDentist : undefined,
    },
    {
      enabled: !!selectedService && view === 'availability' && !!selectedService,
    }
  );

  const createTimeOffMutation = useCreateTimeOff();
  const deleteTimeOffMutation = useDeleteTimeOff();

  const timeOffForm = useForm<TimeOffForm>({
    resolver: zodResolver(timeOffSchema),
    defaultValues: { dentistId: '', startTime: '', endTime: '', reason: '' },
  });

  const weekStart = startOfWeek(selectedDate, { weekStartsOn: 1 });
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const handleCreateTimeOff = async (data: TimeOffForm) => {
    try {
      await createTimeOffMutation.mutateAsync({
        dentistId: data.dentistId,
        startTime: new Date(data.startTime).toISOString(),
        endTime: new Date(data.endTime).toISOString(),
        reason: data.reason,
      });
      setShowTimeOffModal(false);
      timeOffForm.reset();
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

  // Filter shifts by selected dentist
  const filteredShifts =
    shifts?.filter((s) => selectedDentist === 'all' || s.dentistId === selectedDentist) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-headline-lg text-text-primary">Provider Schedules</h1>
          <p className="text-text-secondary text-body-md">
            View and manage provider shifts, time off, and availability
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSelectedDate(subWeeks(selectedDate, 1))}
            className="p-2 rounded-lg border border-border-default hover:bg-bg-elevated transition-colors"
            aria-label="Previous week"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={() => setSelectedDate(new Date())}
            className="px-4 py-2 rounded-lg border border-border-default hover:bg-bg-elevated transition-colors text-sm font-medium"
          >
            This Week
          </button>
          <button
            onClick={() => setSelectedDate(addWeeks(selectedDate, 1))}
            className="p-2 rounded-lg border border-border-default hover:bg-bg-elevated transition-colors"
            aria-label="Next week"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex items-center gap-3">
            <label htmlFor="provider-filter" className="text-label-sm text-text-muted">
              Provider
            </label>
            <select
              id="provider-filter"
              value={selectedDentist}
              onChange={(e) => setSelectedDentist(e.target.value)}
              className="px-3 py-2.5 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors w-48"
            >
              <option value="all">All Providers</option>
              {dentists?.map((d) => (
                <option key={d.id} value={d.id}>
                  Dr. {d.fullName}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3">
            <label htmlFor="service-filter" className="text-label-sm text-text-muted">
              Service (Availability)
            </label>
            <select
              id="service-filter"
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              className="px-3 py-2.5 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors w-56"
            >
              <option value="">Select a service</option>
              {services?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.durationMinutes}min)
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 border border-border-default rounded-lg overflow-hidden">
            <button
              onClick={() => setView('week')}
              className={cn(
                'px-3 py-2 text-sm font-medium transition-colors',
                view === 'week'
                  ? 'bg-brand-primary text-brand-on-primary'
                  : 'text-text-secondary hover:bg-bg-elevated'
              )}
            >
              <Grid className="w-4 h-4" />
              <span className="hidden sm:inline">Week View</span>
            </button>
            <button
              onClick={() => setView('availability')}
              className={cn(
                'px-3 py-2 text-sm font-medium transition-colors',
                view === 'availability'
                  ? 'bg-brand-primary text-brand-on-primary'
                  : 'text-text-secondary hover:bg-bg-elevated'
              )}
            >
              <List className="w-4 h-4" />
              <span className="hidden sm:inline">Availability</span>
            </button>
          </div>

          <button
            onClick={() => setShowTimeOffModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors ml-auto"
          >
            <Plus className="w-4 h-4" />
            Add Time Off
          </button>
        </div>
      </div>

      {/* Time Off Alerts */}
      {timeOff && timeOff.length > 0 && (
        <div className="bg-status-warning-bg border border-status-warning/30 rounded-xl p-4">
          <h3 className="text-title-sm text-status-warning flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5" />
            Time Off This Week
          </h3>
          <div className="flex flex-wrap gap-2">
            {timeOff.map((block) => (
              <div
                key={block.id}
                className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-border-subtle"
              >
                <Sun className="w-4 h-4 text-status-warning" />
                <span className="text-sm font-medium text-text-primary">
                  {block.reason || 'Time Off'}
                </span>
                <span className="text-body-xs text-text-muted">
                  {format(parseISO(block.startTime), 'EEE h:mm a')} -{' '}
                  {format(parseISO(block.endTime), 'h:mm a')}
                </span>
                <button
                  onClick={() => handleDeleteTimeOff(block.id)}
                  className="p-1 rounded hover:bg-status-error/10 text-text-muted hover:text-status-error"
                  aria-label="Delete time off"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* View Content */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle overflow-hidden">
        {view === 'week' ? (
          <WeekScheduleView
            days={days}
            shifts={filteredShifts}
            dentists={dentists || []}
            timeOff={timeOff || []}
            selectedDentist={selectedDentist}
          />
        ) : (
          <AvailabilityView
            date={selectedDate}
            availability={availability}
            selectedService={selectedService}
            services={services || []}
          />
        )}
      </div>

      {/* Time Off Modal */}
      {showTimeOffModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-bg-card rounded-2xl shadow-elev-2 w-full max-w-md p-6">
            <h2 className="text-headline-md text-text-primary mb-6">Add Time Off Block</h2>
            <form onSubmit={timeOffForm.handleSubmit(handleCreateTimeOff)} className="space-y-4">
              <div>
                <label
                  htmlFor="to-dentistId"
                  className="block text-label-md text-text-primary mb-1.5"
                >
                  Provider *
                </label>
                <select
                  {...timeOffForm.register('dentistId')}
                  id="to-dentistId"
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                >
                  <option value="">Select a provider</option>
                  {dentists?.map((d) => (
                    <option key={d.id} value={d.id}>
                      Dr. {d.fullName}
                    </option>
                  ))}
                </select>
                {timeOffForm.formState.errors.dentistId && (
                  <p className="mt-1.5 text-sm text-status-error">
                    {timeOffForm.formState.errors.dentistId.message}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="to-startTime"
                    className="block text-label-md text-text-primary mb-1.5"
                  >
                    Start *
                  </label>
                  <input
                    {...timeOffForm.register('startTime')}
                    type="datetime-local"
                    id="to-startTime"
                    className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                  />
                  {timeOffForm.formState.errors.startTime && (
                    <p className="mt-1.5 text-sm text-status-error">
                      {timeOffForm.formState.errors.startTime.message}
                    </p>
                  )}
                </div>
                <div>
                  <label
                    htmlFor="to-endTime"
                    className="block text-label-md text-text-primary mb-1.5"
                  >
                    End *
                  </label>
                  <input
                    {...timeOffForm.register('endTime')}
                    type="datetime-local"
                    id="to-endTime"
                    className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                  />
                  {timeOffForm.formState.errors.endTime && (
                    <p className="mt-1.5 text-sm text-status-error">
                      {timeOffForm.formState.errors.endTime.message}
                    </p>
                  )}
                </div>
              </div>
              <div>
                <label htmlFor="to-reason" className="block text-label-md text-text-primary mb-1.5">
                  Reason (optional)
                </label>
                <input
                  {...timeOffForm.register('reason')}
                  type="text"
                  id="to-reason"
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

function WeekScheduleView({
  days,
  shifts,
  dentists,
  timeOff,
  selectedDentist,
}: {
  days: Date[];
  shifts: any[];
  dentists: any[];
  timeOff: any[];
  selectedDentist: string;
}) {
  const activeDentists =
    selectedDentist === 'all' ? dentists : dentists.filter((d) => d.id === selectedDentist);

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
          {Array.from({ length: 14 }, (_, i) => i + 7).map((hour) => (
            <tr key={hour} className="border-b border-border-subtle/50">
              <td className="w-32 px-2 py-1 text-right text-label-sm text-text-muted pr-3">
                {format(new Date(2000, 0, 1, hour), 'h a')}
              </td>
              {days.map((day) => (
                <td key={day.toISOString()} className="px-1 py-1 relative min-h-[60px]">
                  {/* Shifts */}
                  {activeDentists.map((dentist) => {
                    const dayShifts = shifts.filter(
                      (s) => s.dentistId === dentist.id && s.dayOfWeek === day.getDay()
                    );
                    return dayShifts.map((shift) => {
                      const shiftStart = parseInt(shift.startTime.split(':')[0], 10);
                      const shiftEnd = parseInt(shift.endTime.split(':')[0], 10);
                      if (hour < shiftStart || hour >= shiftEnd) return null;
                      return (
                        <div
                          key={shift.id}
                          className="absolute left-1 right-1 mb-1 h-6 bg-brand-primary/10 border-l-3 border-brand-primary rounded-r px-1.5 flex items-center"
                          style={{
                            top: `${((hour - shiftStart) / (shiftEnd - shiftStart)) * 100}%`,
                            height: `${(1 / (shiftEnd - shiftStart)) * 100}%`,
                          }}
                        >
                          <span className="text-xs font-medium text-brand-primary truncate">
                            Dr. {dentist.fullName}
                          </span>
                        </div>
                      );
                    });
                  })}
                  {/* Time Off */}
                  {timeOff
                    .filter((t) => isSameDay(parseISO(t.startTime), day))
                    .filter((t) => {
                      const tHour = parseISO(t.startTime).getHours();
                      return tHour === hour;
                    })
                    .map((block) => (
                      <div
                        key={block.id}
                        className="absolute left-1 right-1 mb-1 h-6 bg-status-warning-bg border-l-3 border-status-warning rounded-r px-1.5 flex items-center"
                      >
                        <span className="text-xs font-medium text-status-warning truncate">
                          {block.reason || 'Time Off'}
                        </span>
                      </div>
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

function AvailabilityView({
  date,
  availability,
  selectedService,
  services,
}: {
  date: Date;
  availability: any;
  selectedService: string;
  services: any[];
}) {
  if (!selectedService) {
    return (
      <div className="p-12 text-center">
        <Calendar className="w-12 h-12 text-text-muted mx-auto mb-4" />
        <h3 className="text-headline-md text-text-primary mb-2">Select a Service</h3>
        <p className="text-text-secondary">
          Choose a service from the filter above to view available slots.
        </p>
      </div>
    );
  }

  const service = services.find((s) => s.id === selectedService);
  const slots = availability?.slots || [];

  return (
    <div className="p-6">
      <div className="mb-6 p-4 bg-bg-elevated rounded-lg">
        <h3 className="text-title-sm text-text-primary mb-2">Availability for {service?.name}</h3>
        <p className="text-text-secondary">
          {format(date, 'EEEE, MMMM d, yyyy')} • {service?.durationMinutes} minutes
        </p>
      </div>

      {slots.length === 0 ? (
        <div className="text-center py-12">
          <Clock className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-headline-md text-text-primary mb-2">No available slots</h3>
          <p className="text-text-secondary">
            No available time slots for the selected service and date.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {slots.map((slot: any) => (
            <div
              key={slot.startTime}
              className="p-4 rounded-lg border border-border-subtle hover:bg-bg-elevated transition-colors flex items-center justify-between"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-brand-primary/10 flex items-center justify-center">
                  <Clock className="w-6 h-6 text-brand-primary" />
                </div>
                <div>
                  <p className="font-medium text-text-primary">
                    {format(parseISO(slot.startTime), 'h:mm a')} -{' '}
                    {format(parseISO(slot.endTime), 'h:mm a')}
                  </p>
                  <p className="text-body-sm text-text-muted">Dr. {slot.dentistName}</p>
                </div>
              </div>
              <span className="px-3 py-1.5 rounded-full text-label-sm font-medium bg-status-success-bg text-status-success">
                Available
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
