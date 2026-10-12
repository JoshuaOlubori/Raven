import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate, useParams } from '@tanstack/react-router';
import { ArrowLeft, Save, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { usePatient, useUpdatePatient } from '@/lib/hooks';
import { cn } from '@/lib/utils';

const patientSchema = z.object({
  firstName: z.string().min(1, 'First name is required'),
  lastName: z.string().min(1, 'Last name is required'),
  dateOfBirth: z.string().min(1, 'Date of birth is required'),
  phone: z.string().min(7, 'Phone number is required'),
  email: z.string().email('Invalid email address').optional().or(z.literal('')),
  emergencyContactName: z.string().optional(),
  emergencyContactPhone: z.string().optional(),
  medicalAlerts: z.string().optional(),
});

type PatientForm = z.infer<typeof patientSchema>;

export function PatientEditPage() {
  const navigate = useNavigate();
  const { id } = useParams({ from: '/patients/$id/edit' });
  const { data: patient, isLoading } = usePatient(id);
  const updateMutation = useUpdatePatient();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<PatientForm>({
    resolver: zodResolver(patientSchema),
    defaultValues: {
      firstName: '',
      lastName: '',
      dateOfBirth: '',
      phone: '',
      email: '',
      emergencyContactName: '',
      emergencyContactPhone: '',
      medicalAlerts: '',
    },
  });

  // Populate form when patient data loads
  useEffect(() => {
    if (patient) {
      reset({
        firstName: patient.firstName,
        lastName: patient.lastName,
        dateOfBirth: patient.dateOfBirth.split('T')[0],
        phone: patient.phone,
        email: patient.email || '',
        emergencyContactName: patient.emergencyContactName || '',
        emergencyContactPhone: patient.emergencyContactPhone || '',
        medicalAlerts: patient.medicalAlerts || '',
      });
    }
  }, [patient, reset]);

  const onSubmit = async (data: PatientForm) => {
    setSubmitError(null);
    try {
      await updateMutation.mutateAsync({
        id,
        data: {
          firstName: data.firstName,
          lastName: data.lastName,
          dateOfBirth: data.dateOfBirth,
          phone: data.phone,
          email: data.email || undefined,
          emergencyContactName: data.emergencyContactName || undefined,
          emergencyContactPhone: data.emergencyContactPhone || undefined,
          medicalAlerts: data.medicalAlerts || undefined,
        },
      });
      navigate({ to: `/patients/${id}` as any });
    } catch (error) {
      if (error instanceof Error) {
        setSubmitError(error.message);
      } else {
        setSubmitError('Failed to update patient');
      }
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Link to="/patients" className="p-2 rounded-lg hover:bg-bg-elevated transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </div>
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-border-subtle rounded w-1/4" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-12 bg-border-subtle rounded" />
            <div className="h-12 bg-border-subtle rounded" />
          </div>
          <div className="h-12 bg-border-subtle rounded" />
          <div className="h-12 bg-border-subtle rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to={`/patients/${id}` as any}
          className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-text-primary"
          aria-label="Back to patient"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-headline-lg text-text-primary">Edit Patient</h1>
          <p className="text-text-secondary text-body-md">{patient?.fullName}</p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {submitError && (
          <div className="p-4 rounded-lg bg-status-error-bg text-status-error border border-status-error/20 flex items-center gap-3">
            <X className="w-5 h-5 flex-shrink-0" />
            <p>{submitError}</p>
          </div>
        )}

        {/* Name Section */}
        <fieldset className="space-y-4">
          <legend className="text-title-sm text-text-primary mb-4">Personal Information</legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="firstName" className="block text-label-md text-text-primary mb-1.5">
                First Name <span className="text-status-error">*</span>
              </label>
              <input
                {...register('firstName')}
                type="text"
                id="firstName"
                autoComplete="given-name"
                className={cn(
                  'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary placeholder-text-muted transition-colors',
                  errors.firstName
                    ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                    : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                )}
                aria-invalid={errors.firstName ? 'true' : 'false'}
              />
              {errors.firstName && (
                <p className="mt-1.5 text-sm text-status-error">{errors.firstName.message}</p>
              )}
            </div>
            <div>
              <label htmlFor="lastName" className="block text-label-md text-text-primary mb-1.5">
                Last Name <span className="text-status-error">*</span>
              </label>
              <input
                {...register('lastName')}
                type="text"
                id="lastName"
                autoComplete="family-name"
                className={cn(
                  'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary placeholder-text-muted transition-colors',
                  errors.lastName
                    ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                    : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                )}
                aria-invalid={errors.lastName ? 'true' : 'false'}
              />
              {errors.lastName && (
                <p className="mt-1.5 text-sm text-status-error">{errors.lastName.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="dateOfBirth" className="block text-label-md text-text-primary mb-1.5">
                Date of Birth <span className="text-status-error">*</span>
              </label>
              <input
                {...register('dateOfBirth')}
                type="date"
                id="dateOfBirth"
                max={new Date().toISOString().split('T')[0]}
                className={cn(
                  'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary placeholder-text-muted transition-colors',
                  errors.dateOfBirth
                    ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                    : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                )}
                aria-invalid={errors.dateOfBirth ? 'true' : 'false'}
              />
              {errors.dateOfBirth && (
                <p className="mt-1.5 text-sm text-status-error">{errors.dateOfBirth.message}</p>
              )}
            </div>
            <div>
              <label htmlFor="phone" className="block text-label-md text-text-primary mb-1.5">
                Phone <span className="text-status-error">*</span>
              </label>
              <input
                {...register('phone')}
                type="tel"
                id="phone"
                autoComplete="tel"
                placeholder="(555) 123-4567"
                className={cn(
                  'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary placeholder-text-muted transition-colors',
                  errors.phone
                    ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                    : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                )}
                aria-invalid={errors.phone ? 'true' : 'false'}
              />
              {errors.phone && (
                <p className="mt-1.5 text-sm text-status-error">{errors.phone.message}</p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="email" className="block text-label-md text-text-primary mb-1.5">
              Email
            </label>
            <input
              {...register('email')}
              type="email"
              id="email"
              autoComplete="email"
              placeholder="patient@example.com"
              className={cn(
                'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary placeholder-text-muted transition-colors',
                errors.email
                  ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                  : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
              )}
              aria-invalid={errors.email ? 'true' : 'false'}
            />
            {errors.email && (
              <p className="mt-1.5 text-sm text-status-error">{errors.email.message}</p>
            )}
          </div>
        </fieldset>

        {/* Emergency Contact */}
        <fieldset className="space-y-4 border-t border-border-subtle pt-6">
          <legend className="text-title-sm text-text-primary mb-4">
            Emergency Contact (Optional)
          </legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="emergencyContactName"
                className="block text-label-md text-text-primary mb-1.5"
              >
                Contact Name
              </label>
              <input
                {...register('emergencyContactName')}
                type="text"
                id="emergencyContactName"
                className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary placeholder-text-muted focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
              />
            </div>
            <div>
              <label
                htmlFor="emergencyContactPhone"
                className="block text-label-md text-text-primary mb-1.5"
              >
                Contact Phone
              </label>
              <input
                {...register('emergencyContactPhone')}
                type="tel"
                id="emergencyContactPhone"
                placeholder="(555) 123-4567"
                className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary placeholder-text-muted focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
              />
            </div>
          </div>
        </fieldset>

        {/* Medical Alerts */}
        <fieldset className="space-y-4 border-t border-border-subtle pt-6">
          <legend className="text-title-sm text-text-primary mb-4">
            Medical Alerts (Optional)
          </legend>
          <div>
            <label htmlFor="medicalAlerts" className="block text-label-md text-text-primary mb-1.5">
              Allergies, Conditions, Medications
            </label>
            <textarea
              {...register('medicalAlerts')}
              id="medicalAlerts"
              rows={4}
              placeholder="Enter any medical alerts, allergies, or conditions..."
              className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary placeholder-text-muted focus:border-brand-primary focus:ring-brand-primary/20 transition-colors resize-y"
            />
          </div>
        </fieldset>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 border-t border-border-subtle pt-6">
          <Link
            to={`/patients/${id}` as any}
            className="px-4 py-2.5 rounded-lg border border-border-default text-text-secondary hover:bg-bg-elevated font-medium transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <svg
                  className="animate-spin w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                  <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
                </svg>
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Changes
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
