import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle, Edit, Lock, Mail, Plus, Save, Shield, User, UserCog, X } from 'lucide-react';
import { useState } from 'react';
import { type SubmitHandler, useForm } from 'react-hook-form';
import { z } from 'zod';
import { useCreateStaff, useStaff, useUpdateStaff } from '@/lib/hooks';
import { cn } from '@/lib/utils';
import type { StaffRole } from '@/types/api';

const staffSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .optional()
    .or(z.literal('')),
  fullName: z.string().min(1, 'Full name is required'),
  role: z.enum(['ADMIN', 'RECEPTIONIST', 'DENTIST']),
  isActive: z.boolean(),
});

type StaffForm = z.infer<typeof staffSchema>;

export function StaffPage() {
  const { data: staff, isLoading, refetch } = useStaff();
  const createMutation = useCreateStaff();
  const updateMutation = useUpdateStaff();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingStaff, setEditingStaff] = useState<any>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const createForm = useForm<StaffForm>({
    resolver: zodResolver(staffSchema),
    defaultValues: { email: '', password: '', fullName: '', role: 'RECEPTIONIST', isActive: true },
  });

  const updateForm = useForm<StaffForm>({
    resolver: zodResolver(staffSchema),
    defaultValues: { email: '', password: '', fullName: '', role: 'RECEPTIONIST', isActive: true },
  });

  const handleCreate: SubmitHandler<StaffForm> = async (data) => {
    setSubmitError(null);
    try {
      await createMutation.mutateAsync({
        email: data.email,
        password: data.password || 'TempPass123!',
        fullName: data.fullName,
        role: data.role as StaffRole,
      });
      setShowCreateModal(false);
      createForm.reset();
      refetch();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Failed to create staff');
    }
  };

  const handleUpdate: SubmitHandler<StaffForm> = async (data) => {
    if (!editingStaff) return;
    setSubmitError(null);
    try {
      await updateMutation.mutateAsync({
        id: editingStaff.id,
        data: {
          fullName: data.fullName,
          role: data.role,
          isActive: data.isActive,
        },
      });
      setEditingStaff(null);
      updateForm.reset();
      refetch();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Failed to update staff');
    }
  };

  const startEditing = (member: any) => {
    setEditingStaff(member);
    updateForm.reset({
      email: member.email,
      password: '',
      fullName: member.fullName,
      role: member.role,
      isActive: member.isActive,
    });
  };

  const roleConfig: Record<
    StaffRole,
    { icon: React.ComponentType<{ className?: string }>; color: string; bgColor: string }
  > = {
    ADMIN: { icon: Shield, color: 'text-brand-primary', bgColor: 'bg-brand-primary/10' },
    RECEPTIONIST: { icon: User, color: 'text-status-info', bgColor: 'bg-status-info-bg' },
    DENTIST: { icon: UserCog, color: 'text-status-success', bgColor: 'bg-status-success-bg' },
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-headline-lg text-text-primary">Staff Management</h1>
          <p className="text-text-secondary text-body-md">
            Manage clinic staff accounts and permissions
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Staff Member
        </button>
      </div>

      {/* Staff Table */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-brand-primary border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-text-secondary">Loading staff...</p>
          </div>
        ) : staff?.length === 0 ? (
          <div className="p-12 text-center">
            <UserCog className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-headline-md text-text-primary mb-2">No staff members</h3>
            <p className="text-text-secondary mb-4">
              Get started by adding your first staff member.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 mx-auto px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add First Staff Member
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border-subtle bg-bg-elevated/50">
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Staff Member
                  </th>
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                    Role
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
                {staff?.map((member) => {
                  const config = roleConfig[member.role];
                  const Icon = config.icon;
                  return (
                    <tr
                      key={member.id}
                      className="border-b border-border-subtle/50 hover:bg-bg-elevated/50 transition-colors"
                    >
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div
                            className={cn(
                              'w-10 h-10 rounded-lg flex items-center justify-center',
                              config.bgColor
                            )}
                          >
                            <Icon className={cn('w-5 h-5', config.color)} />
                          </div>
                          <div>
                            <p className="font-medium text-text-primary">{member.fullName}</p>
                            <p className="text-body-xs text-text-muted">
                              {member.id.slice(0, 8)}...
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-body-md text-text-secondary flex items-center gap-2">
                        <Mail className="w-4 h-4 text-text-muted" />
                        {member.email}
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={cn(
                            'px-2.5 py-1 rounded-full text-label-xs font-medium',
                            config.bgColor,
                            config.color
                          )}
                        >
                          {member.role}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={cn(
                            'px-2.5 py-1 rounded-full text-label-xs font-medium',
                            member.isActive
                              ? 'bg-status-success-bg text-status-success'
                              : 'bg-status-error-bg text-status-error'
                          )}
                        >
                          {member.isActive ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => startEditing(member)}
                            className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-brand-primary"
                            aria-label="Edit staff"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
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
              <h2 className="text-headline-md text-text-primary">Add Staff Member</h2>
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
                <label htmlFor="email" className="block text-label-md text-text-primary mb-1.5">
                  Email <span className="text-status-error">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                  <input
                    {...createForm.register('email')}
                    type="email"
                    id="email"
                    className={cn(
                      'w-full pl-10 pr-4 py-3 rounded-lg border bg-bg-card text-text-primary transition-colors',
                      createForm.formState.errors.email
                        ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                        : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                    )}
                  />
                </div>
                {createForm.formState.errors.email && (
                  <p className="mt-1.5 text-sm text-status-error">
                    {createForm.formState.errors.email.message}
                  </p>
                )}
              </div>
              <div>
                <label htmlFor="password" className="block text-label-md text-text-primary mb-1.5">
                  Password <span className="text-status-error">*</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                  <input
                    {...createForm.register('password')}
                    type="password"
                    id="password"
                    className={cn(
                      'w-full pl-10 pr-4 py-3 rounded-lg border bg-bg-card text-text-primary transition-colors',
                      createForm.formState.errors.password
                        ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                        : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                    )}
                  />
                </div>
                {createForm.formState.errors.password && (
                  <p className="mt-1.5 text-sm text-status-error">
                    {createForm.formState.errors.password.message}
                  </p>
                )}
                <p className="mt-1.5 text-body-xs text-text-muted">Min 8 characters</p>
              </div>
              <div>
                <label htmlFor="fullName" className="block text-label-md text-text-primary mb-1.5">
                  Full Name <span className="text-status-error">*</span>
                </label>
                <input
                  {...createForm.register('fullName')}
                  type="text"
                  id="fullName"
                  className={cn(
                    'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary transition-colors',
                    createForm.formState.errors.fullName
                      ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                      : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                  )}
                />
                {createForm.formState.errors.fullName && (
                  <p className="mt-1.5 text-sm text-status-error">
                    {createForm.formState.errors.fullName.message}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="role" className="block text-label-md text-text-primary mb-1.5">
                    Role <span className="text-status-error">*</span>
                  </label>
                  <select
                    {...createForm.register('role')}
                    id="role"
                    className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                  >
                    <option value="RECEPTIONIST">Receptionist</option>
                    <option value="DENTIST">Dentist</option>
                    <option value="ADMIN">Admin</option>
                  </select>
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
                      Add Staff Member
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingStaff && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-bg-card rounded-2xl shadow-elev-2 w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-headline-md text-text-primary">Edit Staff Member</h2>
              <button
                onClick={() => setEditingStaff(null)}
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
                <label
                  htmlFor="edit-email"
                  className="block text-label-md text-text-primary mb-1.5"
                >
                  Email
                </label>
                <input
                  id="edit-email"
                  type="email"
                  value={editingStaff.email}
                  disabled
                  className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-elevated text-text-muted cursor-not-allowed"
                />
                <p className="mt-1.5 text-body-xs text-text-muted">Email cannot be changed</p>
              </div>
              <div>
                <label
                  htmlFor="edit-fullName"
                  className="block text-label-md text-text-primary mb-1.5"
                >
                  Full Name <span className="text-status-error">*</span>
                </label>
                <input
                  {...updateForm.register('fullName')}
                  type="text"
                  id="edit-fullName"
                  className={cn(
                    'w-full px-4 py-3 rounded-lg border bg-bg-card text-text-primary transition-colors',
                    updateForm.formState.errors.fullName
                      ? 'border-status-error focus:border-status-error focus:ring-status-error/20'
                      : 'border-border-default focus:border-brand-primary focus:ring-brand-primary/20'
                  )}
                />
                {updateForm.formState.errors.fullName && (
                  <p className="mt-1.5 text-sm text-status-error">
                    {updateForm.formState.errors.fullName.message}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="edit-role"
                    className="block text-label-md text-text-primary mb-1.5"
                  >
                    Role <span className="text-status-error">*</span>
                  </label>
                  <select
                    {...updateForm.register('role')}
                    id="edit-role"
                    className="w-full px-4 py-3 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
                  >
                    <option value="RECEPTIONIST">Receptionist</option>
                    <option value="DENTIST">Dentist</option>
                    <option value="ADMIN">Admin</option>
                  </select>
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
                  onClick={() => setEditingStaff(null)}
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
