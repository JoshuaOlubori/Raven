import { Link } from '@tanstack/react-router';
import { format } from 'date-fns';
import { Edit, Eye, Plus, Search, Trash2, Users } from 'lucide-react';
import { useState } from 'react';
import { useDeletePatient, usePatients } from '@/lib/hooks';
import { cn } from '@/lib/utils';

export function PatientsPage() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(50);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading, refetch } = usePatients({ search, page, size });
  const deleteMutation = useDeletePatient();

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to deactivate this patient? This action can be reversed.')) {
      try {
        await deleteMutation.mutateAsync(id);
        refetch();
      } catch (error) {
        console.error('Failed to delete patient:', error);
        alert('Failed to deactivate patient');
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-headline-lg text-text-primary">Patients</h1>
          <p className="text-text-secondary text-body-md">
            Manage patient records and demographics
          </p>
        </div>
        <Link
          to="/patients/new"
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Patient
        </Link>
      </div>

      {/* Search and filters */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle p-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
            <input
              type="text"
              placeholder="Search patients by name, email, phone..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border-default bg-bg-card text-text-primary placeholder-text-muted focus:border-brand-primary focus:ring-brand-primary/20 transition-colors"
            />
          </div>

          <div className="flex items-center gap-3">
            <label htmlFor="page-size" className="text-label-sm text-text-muted">
              Per page
            </label>
            <select
              id="page-size"
              value={size}
              onChange={(e) => {
                setSize(Number(e.target.value));
                setPage(1);
              }}
              className="px-3 py-2.5 rounded-lg border border-border-default bg-bg-card text-text-primary focus:border-brand-primary focus:ring-brand-primary/20 transition-colors w-36"
            >
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </div>
        </div>
      </div>

      {/* Patients Table */}
      <div className="bg-bg-card rounded-xl shadow-elev-1 border border-border-subtle overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-brand-primary border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-text-secondary">Loading patients...</p>
          </div>
        ) : data?.items.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-headline-md text-text-primary mb-2">No patients found</h3>
            <p className="text-text-secondary">
              {search
                ? 'Try adjusting your search criteria.'
                : 'Get started by adding a new patient.'}
            </p>
            {!search && (
              <Link
                to="/patients/new"
                className="mt-4 inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-primary text-brand-on-primary font-medium hover:bg-brand-primary-hover transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add First Patient
              </Link>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border-subtle bg-bg-elevated/50">
                    <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                      Patient
                    </th>
                    <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                      DOB / Age
                    </th>
                    <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                      Contact
                    </th>
                    <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-label-xs text-text-muted uppercase tracking-wider">
                      Last Visit
                    </th>
                    <th className="px-4 py-3 text-right text-label-xs text-text-muted uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map((patient) => (
                    <tr
                      key={patient.id}
                      className={cn(
                        'border-b border-border-subtle/50 hover:bg-bg-elevated/50 transition-colors',
                        selectedId === patient.id && 'bg-brand-primary/5'
                      )}
                      onClick={() => setSelectedId(selectedId === patient.id ? null : patient.id)}
                    >
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-brand-primary/10 flex items-center justify-center">
                            <Users className="w-5 h-5 text-brand-primary" />
                          </div>
                          <div>
                            <p className="font-medium text-text-primary">{patient.fullName}</p>
                            <p className="text-body-xs text-text-muted">
                              {patient.email || 'No email'}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-body-md text-text-secondary">
                        {format(new Date(patient.dateOfBirth), 'MMM d, yyyy')}
                        <span className="text-text-muted">
                          {' '}
                          ({calculateAge(patient.dateOfBirth)})
                        </span>
                      </td>
                      <td className="px-4 py-4 text-body-md text-text-secondary">
                        {patient.phone}
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={cn(
                            'px-2.5 py-1 rounded-full text-label-xs font-medium',
                            patient.isActive
                              ? 'bg-status-success-bg text-status-success'
                              : 'bg-status-error-bg text-status-error'
                          )}
                        >
                          {patient.isActive ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-body-md text-text-secondary">
                        {patient.updatedAt
                          ? format(new Date(patient.updatedAt), 'MMM d, yyyy')
                          : '—'}
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            to={`/patients/${patient.id}` as any}
                            onClick={(e) => e.stopPropagation()}
                            className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-brand-primary"
                            aria-label="View patient"
                          >
                            <Eye className="w-4 h-4" />
                          </Link>
                          <Link
                            to={`/patients/${patient.id}/edit` as any}
                            onClick={(e) => e.stopPropagation()}
                            className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-muted hover:text-brand-primary"
                            aria-label="Edit patient"
                          >
                            <Edit className="w-4 h-4" />
                          </Link>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDelete(patient.id);
                            }}
                            className="p-2 rounded-lg hover:bg-status-error/10 transition-colors text-text-muted hover:text-status-error"
                            aria-label="Deactivate patient"
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

            {/* Pagination */}
            {data && data.pages > 1 && (
              <div className="px-4 py-4 border-t border-border-subtle flex items-center justify-between">
                <p className="text-sm text-text-muted">
                  Showing {(page - 1) * size + 1} to {Math.min(page * size, data.total)} of{' '}
                  {data.total} patients
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 rounded-lg border border-border-default hover:bg-bg-elevated disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                    disabled={page === data.pages}
                    className="px-3 py-1.5 rounded-lg border border-border-default hover:bg-bg-elevated disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
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
