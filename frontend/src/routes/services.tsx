import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle, Edit, Package, Plus, Save, Trash2, X } from 'lucide-react';
import { useState } from 'react';
import { type SubmitHandler, useForm } from 'react-hook-form';
import { z } from 'zod';
import { useCreateService, useServices, useUpdateService } from '@/lib/hooks';
import { cn } from '@/lib/utils';

const serviceSchema = z.object({
  name: z.string().min(1, 'Service name is required'),
  description: z.string().optional(),
  durationMinutes: z
    .number()
    .min(1, 'Duration must be at least 1 minute')
    .max(480, 'Duration cannot exceed 480 minutes'),
  isActive: z.boolean(),
});

type ServiceForm = z.infer<typeof serviceSchema>;

export function ServicesPage() {
  const { data: services, isLoading, refetch } = useServices();
  const createMutation = useCreateService();
  const updateMutation = useUpdateService();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingService, setEditingService] = useState<any>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const createForm = useForm<ServiceForm>({
    resolver: zodResolver(serviceSchema),
    defaultValues: { name: '', description: '', durationMinutes: 30, isActive: true },
  });

  const updateForm = useForm<ServiceForm>({
    resolver: zodResolver(serviceSchema),
    defaultValues: { name: '', description: '', durationMinutes: 30, isActive: true },
  });

  const handleCreate: SubmitHandler<ServiceForm> = async (data) => {
    setSubmitError(null);
    try {
      await createMutation.mutateAsync(data);
      setShowCreateModal(false);
      createForm.reset();
      refetch();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Failed to create service');
    }
  };

  const handleUpdate: SubmitHandler<ServiceForm> = async (data) => {
    if (!editingService) return;
    setSubmitError(null);
    try {
      await updateMutation.mutateAsync({ id: editingService.id, data });
      setEditingService(null);
      updateForm.reset();
      refetch();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Failed to update service');
    }
  };

  const handleDelete = async (_id: string) => {
    if (confirm('Are you sure you want to delete this service? This action cannot be undone.')) {
      try {
        // Note: No delete endpoint in API, would need to implement soft delete via update
        alert('Delete functionality not yet implemented in API');
      } catch (error) {
        console.error('Failed to delete service:', error);
        alert('Failed to delete service');
      }
    }
  };

  const startEditing = (service: any) => {
    setEditingService(service);
    updateForm.reset({
      name: service.name,
      description: service.description || '',
      durationMinutes: service.durationMinutes,
      isActive: service.isActive,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-headline-lg text-text-primary">Dental Services</h1>
          <p className="text-text-secondary text-body-md">Manage the dental service catalog</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Service
        </button>
      </div>

      {/* Services Table */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-brand-primary border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-text-secondary">Loading services...</p>
          </div>
        ) : services?.length === 0 ? (
          <div className="p-12 text-center">
            <Package className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-headline-md text-text-primary mb-2">No services yet</h3>
            <p className="text-text-secondary mb-4">
              Get started by adding your first dental service.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 mx-auto px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add First Service
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border-subtle bg-bg-elevated/50">
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Service
                  </th>
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-right text-label-xs text-text-muted uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {services?.map((service) => (
                  <tr
                    key={service.id}
                    className="border-b border-border-subtle/50 hover:bg-bg-elevated/50 transition-colors"
                  >
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-brand-primary/10 flex items-center justify-center">
                          <Package className="w-5 h-5 text-brand-primary" />
                        </div>
                        <div>
                          <p className="font-medium text-text-primary">{service.name}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-body-md text-text-secondary max-w-xs truncate">
                      {service.description || <span className="text-text-muted">—</span>}
                    </td>
                    <td className="px-4 py-4 text-body-md text-text-primary tabular-nums">
                      {service.durationMinutes} min
                    </td>
                    <td className="px-4 py-4">
                      <span
                        className={cn(
                          'px-2.5 py-1 rounded-full text-label-xs font-medium',
                          service.isActive
                            ? 'bg-status-success-bg text-status-success'
                            : 'bg-status-error-bg text-status-error'
                        )}
                      >
                        {service.isActive ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => startEditing(service)}
                          className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-brand-primary"
                          aria-label="Edit service"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(service.id)}
                          className="p-2 rounded-lg hover:bg-status-error/10 transition-colors text-text-muted hover:text-status-error"
                          aria-label="Delete service"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-bg-card rounded-2xl shadow-elev-2 w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-headline-md text-text-primary">New Service</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={createForm.handleSubmit(handleCreate)} className="space-y-4">
              {submitError && (
                <div className="p-4 rounded-lg bg-status-error-bg text-status-error border border-status-error/20 flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <p>{submitError}</p>
                </div>
              )}
              <div>
                <label htmlFor="name" className="block text-label-md text-text-primary mb-1.5">
                  Service Name <span className="text-status-error">*</span>
                </label>
                <input
                  {...createForm.register('name')}
                  type="text"
                  id="name"
                  className={cn(
                    'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary transition-colors',
                    createForm.formState.errors.name
                      ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                      : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                  )}
                />
                {createForm.formState.errors.name && (
                  <p className="mt-1.5 text-sm text-status-error">
                    {createForm.formState.errors.name.message}
                  </p>
                )}
              </div>
              <div>
                <label
                  htmlFor="description"
                  className="block text-label-md text-text-primary mb-1.5"
                >
                  Description
                </label>
                <textarea
                  {...createForm.register('description')}
                  id="description"
                  rows={3}
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors resize-y"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="durationMinutes"
                    className="block text-label-md text-text-primary mb-1.5"
                  >
                    Duration (minutes) <span className="text-status-error">*</span>
                  </label>
                  <input
                    {...createForm.register('durationMinutes', { valueAsNumber: true })}
                    type="number"
                    id="durationMinutes"
                    min="1"
                    max="480"
                    className={cn(
                      'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary transition-colors',
                      createForm.formState.errors.durationMinutes
                        ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                        : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                    )}
                  />
                  {createForm.formState.errors.durationMinutes && (
                    <p className="mt-1.5 text-sm text-status-error">
                      {createForm.formState.errors.durationMinutes.message}
                    </p>
                  )}
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      {...createForm.register('isActive')}
                      type="checkbox"
                      className="w-4 h-4 rounded border-border-default text-brand-primary focus:ring-brand-primary"
                    />
                    <span className="text-label-md text-text-primary">Active</span>
                  </label>
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2.5 rounded-lg border border-border-default text-text-secondary hover:bg-bg-elevated font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createForm.formState.isSubmitting}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors disabled:opacity-50"
                >
                  {createForm.formState.isSubmitting ? (
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
                      Creating...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      Create Service
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingService && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-bg-card rounded-2xl shadow-elev-2 w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-headline-md text-text-primary">Edit Service</h2>
              <button
                onClick={() => setEditingService(null)}
                className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={updateForm.handleSubmit(handleUpdate)} className="space-y-4">
              {submitError && (
                <div className="p-4 rounded-lg bg-status-error-bg text-status-error border border-status-error/20 flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <p>{submitError}</p>
                </div>
              )}
              <div>
                <label htmlFor="edit-name" className="block text-label-md text-text-primary mb-1.5">
                  Service Name <span className="text-status-error">*</span>
                </label>
                <input
                  {...updateForm.register('name')}
                  type="text"
                  id="edit-name"
                  className={cn(
                    'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary transition-colors',
                    updateForm.formState.errors.name
                      ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                      : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                  )}
                />
                {updateForm.formState.errors.name && (
                  <p className="mt-1.5 text-sm text-status-error">
                    {updateForm.formState.errors.name.message}
                  </p>
                )}
              </div>
              <div>
                <label
                  htmlFor="edit-description"
                  className="block text-label-md text-text-primary mb-1.5"
                >
                  Description
                </label>
                <textarea
                  {...updateForm.register('description')}
                  id="edit-description"
                  rows={3}
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors resize-y"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="edit-durationMinutes"
                    className="block text-label-md text-text-primary mb-1.5"
                  >
                    Duration (minutes) <span className="text-status-error">*</span>
                  </label>
                  <input
                    {...updateForm.register('durationMinutes', { valueAsNumber: true })}
                    type="number"
                    id="edit-durationMinutes"
                    min="1"
                    max="480"
                    className={cn(
                      'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary transition-colors',
                      updateForm.formState.errors.durationMinutes
                        ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                        : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                    )}
                  />
                  {updateForm.formState.errors.durationMinutes && (
                    <p className="mt-1.5 text-sm text-status-error">
                      {updateForm.formState.errors.durationMinutes.message}
                    </p>
                  )}
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      {...updateForm.register('isActive')}
                      type="checkbox"
                      className="w-4 h-4 rounded border-border-default text-brand-primary focus:ring-brand-primary"
                    />
                    <span className="text-label-md text-text-primary">Active</span>
                  </label>
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setEditingService(null)}
                  className="px-4 py-2.5 rounded-lg border border-border-default text-text-secondary hover:bg-bg-elevated font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateForm.formState.isSubmitting}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors disabled:opacity-50"
                >
                  {updateForm.formState.isSubmitting ? (
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
        </div>
      )}
    </div>
  );
}
