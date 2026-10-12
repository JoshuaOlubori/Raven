import { HttpResponse, http } from 'msw';
import { setupWorker } from 'msw/browser';

type StaffRole = 'ADMIN' | 'RECEPTIONIST' | 'DENTIST';

interface Staff {
  id: string;
  email: string;
  fullName: string;
  role: StaffRole;
  isActive: boolean;
  createdAt: string;
  hashedPassword?: string;
}

interface Patient {
  id: string;
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  phone: string;
  email: string | null;
  emergencyContactName: string | null;
  emergencyContactPhone: string | null;
  medicalAlerts: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

interface Service {
  id: string;
  name: string;
  description: string | null;
  durationMinutes: number;
  isActive: boolean;
  createdAt: string;
}

interface Appointment {
  id: string;
  patientId: string;
  dentistId: string;
  serviceId: string;
  startTime: string;
  endTime: string;
  status: string;
  cancellationReason: string | null;
  reminderSentAt: string | null;
  createdAt: string;
  updatedAt: string;
  patient?: Patient;
  dentist?: Staff;
  service?: Service;
}

interface Shift {
  id: string;
  dentistId: string;
  dayOfWeek: number;
  startTime: string;
  endTime: string;
}

interface TimeOffBlock {
  id: string;
  dentistId: string;
  startTime: string;
  endTime: string;
  reason: string | null;
  createdAt: string;
}

// Mock data
const mockStaff: Staff[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    email: 'admin@ravendental.internal',
    fullName: 'Dr. Sarah Admin',
    role: 'ADMIN',
    isActive: true,
    createdAt: '2024-01-15T08:00:00Z',
    hashedPassword: 'hashed',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    email: 'reception@ravendental.internal',
    fullName: 'Maria Receptionist',
    role: 'RECEPTIONIST',
    isActive: true,
    createdAt: '2024-01-20T08:00:00Z',
    hashedPassword: 'hashed',
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    email: 'dr.smith@ravendental.internal',
    fullName: 'Dr. James Smith',
    role: 'DENTIST',
    isActive: true,
    createdAt: '2024-01-10T08:00:00Z',
    hashedPassword: 'hashed',
  },
  {
    id: '44444444-4444-4444-4444-444444444444',
    email: 'dr.jones@ravendental.internal',
    fullName: 'Dr. Emily Jones',
    role: 'DENTIST',
    isActive: true,
    createdAt: '2024-02-01T08:00:00Z',
    hashedPassword: 'hashed',
  },
];

const mockPatients: Patient[] = [
  {
    id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    firstName: 'John',
    lastName: 'Doe',
    dateOfBirth: '1985-03-15',
    phone: '(555) 123-4567',
    email: 'john.doe@example.com',
    emergencyContactName: 'Jane Doe',
    emergencyContactPhone: '(555) 123-4568',
    medicalAlerts: 'Allergic to penicillin',
    isActive: true,
    createdAt: '2024-02-15T10:00:00Z',
    updatedAt: '2024-02-15T10:00:00Z',
  },
  {
    id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    firstName: 'Jane',
    lastName: 'Smith',
    dateOfBirth: '1990-07-22',
    phone: '(555) 234-5678',
    email: 'jane.smith@example.com',
    emergencyContactName: 'Bob Smith',
    emergencyContactPhone: '(555) 234-5679',
    medicalAlerts: null,
    isActive: true,
    createdAt: '2024-03-01T14:30:00Z',
    updatedAt: '2024-03-01T14:30:00Z',
  },
  {
    id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
    firstName: 'Robert',
    lastName: 'Johnson',
    dateOfBirth: '1978-11-08',
    phone: '(555) 345-6789',
    email: 'robert.j@example.com',
    emergencyContactName: 'Mary Johnson',
    emergencyContactPhone: '(555) 345-6780',
    medicalAlerts: 'High blood pressure, takes lisinopril',
    isActive: true,
    createdAt: '2024-03-10T09:15:00Z',
    updatedAt: '2024-03-10T09:15:00Z',
  },
];

const mockServices: Service[] = [
  {
    id: 'dddddddd-dddd-dddd-dddd-dddddddddddd',
    name: 'Comprehensive Exam',
    description: 'Full oral examination with X-rays',
    durationMinutes: 60,
    isActive: true,
    createdAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
    name: 'Cleaning',
    description: 'Prophylaxis cleaning and polishing',
    durationMinutes: 45,
    isActive: true,
    createdAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'ffffffff-ffff-ffff-ffff-ffffffffffff',
    name: 'Filling',
    description: 'Composite resin filling',
    durationMinutes: 30,
    isActive: true,
    createdAt: '2024-01-01T00:00:00Z',
  },
  {
    id: '11111111-2222-3333-4444-555555555555',
    name: 'Crown',
    description: 'Porcelain crown placement',
    durationMinutes: 90,
    isActive: true,
    createdAt: '2024-01-01T00:00:00Z',
  },
  {
    id: '22222222-3333-4444-5555-666666666666',
    name: 'Root Canal',
    description: 'Endodontic therapy',
    durationMinutes: 120,
    isActive: true,
    createdAt: '2024-01-01T00:00:00Z',
  },
];

const mockShifts: Shift[] = [
  {
    id: '33333333-4444-5555-6666-777777777777',
    dentistId: '33333333-3333-3333-3333-333333333333',
    dayOfWeek: 0,
    startTime: '08:00:00',
    endTime: '17:00:00',
  },
  {
    id: '44444444-5555-6666-7777-888888888888',
    dentistId: '33333333-3333-3333-3333-333333333333',
    dayOfWeek: 2,
    startTime: '08:00:00',
    endTime: '17:00:00',
  },
  {
    id: '55555555-6666-7777-8888-999999999999',
    dentistId: '33333333-3333-3333-3333-333333333333',
    dayOfWeek: 4,
    startTime: '08:00:00',
    endTime: '14:00:00',
  },
  {
    id: '66666666-7777-8888-9999-000000000000',
    dentistId: '44444444-4444-4444-4444-444444444444',
    dayOfWeek: 1,
    startTime: '09:00:00',
    endTime: '18:00:00',
  },
  {
    id: '77777777-8888-9999-0000-111111111111',
    dentistId: '44444444-4444-4444-4444-444444444444',
    dayOfWeek: 3,
    startTime: '09:00:00',
    endTime: '18:00:00',
  },
];

const mockTimeOff: TimeOffBlock[] = [
  {
    id: '88888888-9999-0000-1111-222222222222',
    dentistId: '33333333-3333-3333-3333-333333333333',
    startTime: '2024-12-25T08:00:00Z',
    endTime: '2024-12-25T17:00:00Z',
    reason: 'Christmas Holiday',
    createdAt: '2024-12-01T00:00:00Z',
  },
];

const mockAppointments: Appointment[] = [
  {
    id: 'appt-1111-1111-1111-111111111111',
    patientId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    dentistId: '33333333-3333-3333-3333-333333333333',
    serviceId: 'dddddddd-dddd-dddd-dddd-dddddddddddd',
    startTime: '2024-12-15T14:00:00Z',
    endTime: '2024-12-15T15:00:00Z',
    status: 'CONFIRMED',
    cancellationReason: null,
    reminderSentAt: null,
    createdAt: '2024-12-10T10:00:00Z',
    updatedAt: '2024-12-10T10:00:00Z',
    patient: mockPatients[0],
    dentist: mockStaff[2],
    service: mockServices[0],
  },
  {
    id: 'appt-2222-2222-2222-222222222222',
    patientId: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    dentistId: '44444444-4444-4444-4444-444444444444',
    serviceId: 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
    startTime: '2024-12-15T15:30:00Z',
    endTime: '2024-12-15T16:15:00Z',
    status: 'SCHEDULED',
    cancellationReason: null,
    reminderSentAt: null,
    createdAt: '2024-12-10T11:00:00Z',
    updatedAt: '2024-12-10T11:00:00Z',
    patient: mockPatients[1],
    dentist: mockStaff[3],
    service: mockServices[1],
  },
  {
    id: 'appt-3333-3333-3333-333333333333',
    patientId: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
    dentistId: '33333333-3333-3333-3333-333333333333',
    serviceId: 'ffffffff-ffff-ffff-ffff-ffffffffffff',
    startTime: '2024-12-16T10:00:00Z',
    endTime: '2024-12-16T10:30:00Z',
    status: 'SCHEDULED',
    cancellationReason: null,
    reminderSentAt: null,
    createdAt: '2024-12-10T12:00:00Z',
    updatedAt: '2024-12-10T12:00:00Z',
    patient: mockPatients[2],
    dentist: mockStaff[2],
    service: mockServices[2],
  },
];

// Helper functions
function getAuth(request: Request): Staff | null {
  const auth = request.headers.get('Authorization');
  if (!auth?.startsWith('Bearer ')) return null;
  const token = auth.slice(7);
  if (!token.startsWith('mock-token-')) return null;
  const userId = token.split('-')[2];
  return mockStaff.find((s) => s.id === userId) || null;
}

function generateToken(userId: string, role: string): string {
  return `mock-token-${userId}-${role}-${Date.now()}`;
}

async function parseJson<T>(request: Request): Promise<T | null> {
  try {
    return (await request.json()) as T;
  } catch {
    return null;
  }
}

// Request body types
interface LoginBody {
  username: string;
  password: string;
}

interface PatientCreateBody {
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  phone: string;
  email?: string;
  emergencyContactName?: string;
  emergencyContactPhone?: string;
  medicalAlerts?: string;
}

interface StaffCreateBody {
  email: string;
  password: string;
  fullName: string;
  role: StaffRole;
}

interface StaffUpdateBody {
  fullName?: string;
  role?: StaffRole;
  isActive?: boolean;
}

interface ServiceCreateBody {
  name: string;
  description?: string;
  durationMinutes: number;
  isActive?: boolean;
}

interface AppointmentCreateBody {
  patientId: string;
  dentistId: string;
  serviceId: string;
  startTime: string;
}

interface AppointmentRescheduleBody {
  startTime: string;
  dentistId?: string;
}

interface AppointmentCancelBody {
  cancellationReason: string;
}

interface AppointmentStatusBody {
  toStatus: string;
  note?: string;
}

interface TimeOffCreateBody {
  dentistId: string;
  startTime: string;
  endTime: string;
  reason?: string;
}

interface ShiftCreateBody {
  dentistId: string;
  dayOfWeek: number;
  startTime: string;
  endTime: string;
}

export const handlers = [
  // Auth
  http.post('/api/v1/auth/token', async ({ request }) => {
    const body = await parseJson<LoginBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    const user = mockStaff.find((s) => s.email === body.username);
    if (!user?.isActive) {
      return HttpResponse.json(
        { error: 'InvalidCredentialsError', message: 'Invalid email or password' },
        { status: 401 }
      );
    }
    return HttpResponse.json({
      accessToken: generateToken(user.id, user.role),
      tokenType: 'bearer',
      expiresIn: 1800,
      role: user.role,
    });
  }),

  http.get('/api/v1/auth/me', ({ request }) => {
    const user = getAuth(request);
    if (!user) {
      return HttpResponse.json(
        { error: 'Unauthorized', message: 'Invalid or missing token' },
        { status: 401 }
      );
    }
    return HttpResponse.json(user);
  }),

  // Patients
  http.get('/api/v1/patients', ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get('search')?.toLowerCase() || '';
    const page = parseInt(url.searchParams.get('page') || '1', 10);
    const size = parseInt(url.searchParams.get('size') || '50', 10);

    let filtered = mockPatients.filter((p) => p.isActive);
    if (search) {
      filtered = filtered.filter(
        (p) =>
          `${p.firstName} ${p.lastName}`.toLowerCase().includes(search) ||
          p.email?.toLowerCase().includes(search) ||
          p.phone.includes(search)
      );
    }

    const start = (page - 1) * size;
    const items = filtered.slice(start, start + size);

    return HttpResponse.json({
      items: items.map((p) => ({ ...p, fullName: `${p.firstName} ${p.lastName}` })),
      total: filtered.length,
      page,
      size,
      pages: Math.ceil(filtered.length / size),
    });
  }),

  http.get('/api/v1/patients/:id', ({ params }) => {
    const patient = mockPatients.find((p) => p.id === params.id);
    if (!patient) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Patient not found' },
        { status: 404 }
      );
    }
    return HttpResponse.json({ ...patient, fullName: `${patient.firstName} ${patient.lastName}` });
  }),

  http.post('/api/v1/patients', async ({ request }) => {
    const body = await parseJson<PatientCreateBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    const newPatient: Patient = {
      id: crypto.randomUUID(),
      ...body,
      email: body.email || null,
      emergencyContactName: body.emergencyContactName || null,
      emergencyContactPhone: body.emergencyContactPhone || null,
      medicalAlerts: body.medicalAlerts || null,
      isActive: true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    mockPatients.push(newPatient);
    return HttpResponse.json(
      { ...newPatient, fullName: `${newPatient.firstName} ${newPatient.lastName}` },
      { status: 201 }
    );
  }),

  http.patch('/api/v1/patients/:id', async ({ params, request }) => {
    const index = mockPatients.findIndex((p) => p.id === params.id);
    if (index === -1) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Patient not found' },
        { status: 404 }
      );
    }
    const body = await parseJson<Partial<PatientCreateBody>>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    mockPatients[index] = { ...mockPatients[index], ...body, updatedAt: new Date().toISOString() };
    return HttpResponse.json({
      ...mockPatients[index],
      fullName: `${mockPatients[index].firstName} ${mockPatients[index].lastName}`,
    });
  }),

  http.delete('/api/v1/patients/:id', ({ params }) => {
    const index = mockPatients.findIndex((p) => p.id === params.id);
    if (index === -1) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Patient not found' },
        { status: 404 }
      );
    }
    mockPatients[index] = { ...mockPatients[index], isActive: false };
    return new HttpResponse(null, { status: 204 });
  }),

  // Staff
  http.get('/api/v1/staff', ({ request }) => {
    const url = new URL(request.url);
    const role = url.searchParams.get('role');
    let filtered = mockStaff.filter((s) => s.isActive);
    if (role) filtered = filtered.filter((s) => s.role === role);
    return HttpResponse.json(filtered);
  }),

  http.get('/api/v1/staff/:id', ({ params }) => {
    const member = mockStaff.find((s) => s.id === params.id);
    if (!member) {
      return HttpResponse.json({ error: 'NotFound', message: 'Staff not found' }, { status: 404 });
    }
    return HttpResponse.json(member);
  }),

  http.post('/api/v1/staff', async ({ request }) => {
    const body = await parseJson<StaffCreateBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    const existing = mockStaff.find((s) => s.email === body.email);
    if (existing) {
      return HttpResponse.json(
        { error: 'EmailAlreadyExistsError', message: 'Email already exists' },
        { status: 400 }
      );
    }
    const newStaff: Staff = {
      id: crypto.randomUUID(),
      ...body,
      hashedPassword: 'hashed',
      isActive: true,
      createdAt: new Date().toISOString(),
    };
    mockStaff.push(newStaff);
    return HttpResponse.json(newStaff, { status: 201 });
  }),

  http.patch('/api/v1/staff/:id', async ({ params, request }) => {
    const index = mockStaff.findIndex((s) => s.id === params.id);
    if (index === -1) {
      return HttpResponse.json({ error: 'NotFound', message: 'Staff not found' }, { status: 404 });
    }
    const body = await parseJson<StaffUpdateBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    mockStaff[index] = { ...mockStaff[index], ...body };
    return HttpResponse.json(mockStaff[index]);
  }),

  // Services
  http.get('/api/v1/services', ({ request }) => {
    const url = new URL(request.url);
    const activeOnly = url.searchParams.get('active_only') !== 'false';
    let filtered = mockServices;
    if (activeOnly) filtered = filtered.filter((s) => s.isActive);
    return HttpResponse.json(filtered);
  }),

  http.get('/api/v1/services/:id', ({ params }) => {
    const service = mockServices.find((s) => s.id === params.id);
    if (!service) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Service not found' },
        { status: 404 }
      );
    }
    return HttpResponse.json(service);
  }),

  http.post('/api/v1/services', async ({ request }) => {
    const body = await parseJson<ServiceCreateBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    const newService: Service = {
      id: crypto.randomUUID(),
      ...body,
      description: body.description ?? null,
      isActive: body.isActive ?? true,
      createdAt: new Date().toISOString(),
    };
    mockServices.push(newService);
    return HttpResponse.json(newService, { status: 201 });
  }),

  http.patch('/api/v1/services/:id', async ({ params, request }) => {
    const index = mockServices.findIndex((s) => s.id === params.id);
    if (index === -1) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Service not found' },
        { status: 404 }
      );
    }
    const body = await parseJson<Partial<ServiceCreateBody>>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    mockServices[index] = { ...mockServices[index], ...body };
    return HttpResponse.json(mockServices[index]);
  }),

  // Schedules - Shifts
  http.get('/api/v1/schedules/shifts', ({ request }) => {
    const url = new URL(request.url);
    const dentistId = url.searchParams.get('dentistId');
    let filtered = mockShifts;
    if (dentistId) filtered = filtered.filter((s) => s.dentistId === dentistId);
    return HttpResponse.json(filtered);
  }),

  http.post('/api/v1/schedules/shifts', async ({ request }) => {
    const body = await parseJson<ShiftCreateBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    const newShift: Shift = { id: crypto.randomUUID(), ...body };
    mockShifts.push(newShift);
    return HttpResponse.json(newShift, { status: 201 });
  }),

  http.delete('/api/v1/schedules/shifts/:id', ({ params }) => {
    const index = mockShifts.findIndex((s) => s.id === params.id);
    if (index === -1) {
      return HttpResponse.json({ error: 'NotFound', message: 'Shift not found' }, { status: 404 });
    }
    mockShifts.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  // Schedules - Time Off
  http.get('/api/v1/schedules/time-off', ({ request }) => {
    const url = new URL(request.url);
    const dentistId = url.searchParams.get('dentistId');
    const startDate = url.searchParams.get('startDate');
    const endDate = url.searchParams.get('endDate');

    let filtered = mockTimeOff;
    if (dentistId) filtered = filtered.filter((t) => t.dentistId === dentistId);
    if (startDate) filtered = filtered.filter((t) => new Date(t.startTime) >= new Date(startDate));
    if (endDate) filtered = filtered.filter((t) => new Date(t.endTime) <= new Date(endDate));
    return HttpResponse.json(filtered);
  }),

  http.post('/api/v1/schedules/time-off', async ({ request }) => {
    const body = await parseJson<TimeOffCreateBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    const newTimeOff: TimeOffBlock = {
      id: crypto.randomUUID(),
      dentistId: body.dentistId,
      startTime: body.startTime,
      endTime: body.endTime,
      reason: body.reason ?? null,
      createdAt: new Date().toISOString(),
    };
    mockTimeOff.push(newTimeOff);
    return HttpResponse.json(newTimeOff, { status: 201 });
  }),

  http.delete('/api/v1/schedules/time-off/:id', ({ params }) => {
    const index = mockTimeOff.findIndex((t) => t.id === params.id);
    if (index === -1) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Time off not found' },
        { status: 404 }
      );
    }
    mockTimeOff.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  // Schedules - Availability
  http.get('/api/v1/schedules/availability', ({ request }) => {
    const url = new URL(request.url);
    const serviceId = url.searchParams.get('serviceId');
    const date = url.searchParams.get('date');
    const dentistId = url.searchParams.get('dentistId');

    if (!serviceId || !date) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'serviceId and date are required' },
        { status: 400 }
      );
    }

    const service = mockServices.find((s) => s.id === serviceId);
    if (!service) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Service not found' },
        { status: 404 }
      );
    }

    const targetDate = new Date(date);
    const weekday = targetDate.getDay();
    const dayShifts = mockShifts.filter(
      (s) => s.dayOfWeek === weekday && (!dentistId || s.dentistId === dentistId)
    );

    const slots: any[] = [];
    for (const shift of dayShifts) {
      const shiftDate = new Date(targetDate);
      const [startH, startM] = shift.startTime.split(':').map(Number);
      const [endH, endM] = shift.endTime.split(':').map(Number);

      const shiftStart = new Date(shiftDate);
      shiftStart.setHours(startH, startM, 0, 0);

      const shiftEnd = new Date(shiftDate);
      shiftEnd.setHours(endH, endM, 0, 0);

      let current = new Date(shiftStart);
      while (current.getTime() + service.durationMinutes * 60000 <= shiftEnd.getTime()) {
        const slotEnd = new Date(current.getTime() + service.durationMinutes * 60000);
        const hasConflict = mockAppointments.some(
          (a) =>
            a.dentistId === shift.dentistId &&
            new Date(a.startTime) < slotEnd &&
            new Date(a.endTime) > current &&
            !['CANCELLED', 'NO_SHOW'].includes(a.status)
        );

        if (!hasConflict) {
          const dentist = mockStaff.find((d) => d.id === shift.dentistId);
          slots.push({
            startTime: current.toISOString(),
            endTime: slotEnd.toISOString(),
            dentistId: shift.dentistId,
            dentistName: dentist?.fullName || 'Unknown',
          });
        }
        current = new Date(current.getTime() + 15 * 60000);
      }
    }

    return HttpResponse.json({
      date: targetDate.toISOString().split('T')[0],
      serviceId,
      durationMinutes: service.durationMinutes,
      slots,
    });
  }),

  // Appointments
  http.get('/api/v1/appointments', ({ request }) => {
    const url = new URL(request.url);
    const dentistId = url.searchParams.get('dentistId');
    const patientId = url.searchParams.get('patientId');
    const status = url.searchParams.get('status');
    const startDate = url.searchParams.get('startDate');
    const endDate = url.searchParams.get('endDate');

    let filtered = [...mockAppointments];
    if (dentistId) filtered = filtered.filter((a) => a.dentistId === dentistId);
    if (patientId) filtered = filtered.filter((a) => a.patientId === patientId);
    if (status) filtered = filtered.filter((a) => a.status === status);
    if (startDate) filtered = filtered.filter((a) => new Date(a.startTime) >= new Date(startDate));
    if (endDate) filtered = filtered.filter((a) => new Date(a.endTime) <= new Date(endDate));

    filtered.sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime());

    return HttpResponse.json(filtered);
  }),

  http.get('/api/v1/appointments/:id', ({ params }) => {
    const appointment = mockAppointments.find((a) => a.id === params.id);
    if (!appointment) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Appointment not found' },
        { status: 404 }
      );
    }
    return HttpResponse.json(appointment);
  }),

  http.post('/api/v1/appointments', async ({ request }) => {
    const body = await parseJson<AppointmentCreateBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    const service = mockServices.find((s) => s.id === body.serviceId);
    const dentist = mockStaff.find((d) => d.id === body.dentistId);
    const patient = mockPatients.find((p) => p.id === body.patientId);

    if (!service || !dentist || !patient) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid service, dentist, or patient' },
        { status: 400 }
      );
    }

    const startTime = new Date(body.startTime);
    const endTime = new Date(startTime.getTime() + service.durationMinutes * 60000);

    const newAppointment: Appointment = {
      id: `appt-${crypto.randomUUID()}`,
      patientId: body.patientId,
      dentistId: body.dentistId,
      serviceId: body.serviceId,
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString(),
      status: 'SCHEDULED',
      cancellationReason: null,
      reminderSentAt: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      patient,
      dentist,
      service,
    };

    mockAppointments.push(newAppointment);
    return HttpResponse.json(newAppointment, { status: 201 });
  }),

  http.post('/api/v1/appointments/:id/reschedule', async ({ params, request }) => {
    const index = mockAppointments.findIndex((a) => a.id === params.id);
    if (index === -1) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Appointment not found' },
        { status: 404 }
      );
    }

    const body = await parseJson<AppointmentRescheduleBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    const service = mockServices.find((s) => s.id === mockAppointments[index].serviceId);
    const newStartTime = new Date(body.startTime);
    const newEndTime = new Date(newStartTime.getTime() + (service?.durationMinutes || 30) * 60000);

    mockAppointments[index] = {
      ...mockAppointments[index],
      startTime: newStartTime.toISOString(),
      endTime: newEndTime.toISOString(),
      dentistId: body.dentistId || mockAppointments[index].dentistId,
      updatedAt: new Date().toISOString(),
    };

    return HttpResponse.json(mockAppointments[index]);
  }),

  http.post('/api/v1/appointments/:id/cancel', async ({ params, request }) => {
    const index = mockAppointments.findIndex((a) => a.id === params.id);
    if (index === -1) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Appointment not found' },
        { status: 404 }
      );
    }

    const body = await parseJson<AppointmentCancelBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    mockAppointments[index] = {
      ...mockAppointments[index],
      status: 'CANCELLED',
      cancellationReason: body.cancellationReason,
      updatedAt: new Date().toISOString(),
    };

    return HttpResponse.json(mockAppointments[index]);
  }),

  http.post('/api/v1/appointments/:id/status', async ({ params, request }) => {
    const index = mockAppointments.findIndex((a) => a.id === params.id);
    if (index === -1) {
      return HttpResponse.json(
        { error: 'NotFound', message: 'Appointment not found' },
        { status: 404 }
      );
    }

    const body = await parseJson<AppointmentStatusBody>(request);
    if (!body) {
      return HttpResponse.json(
        { error: 'BadRequest', message: 'Invalid request body' },
        { status: 400 }
      );
    }
    const validTransitions: Record<string, string[]> = {
      SCHEDULED: ['CONFIRMED', 'CANCELLED'],
      CONFIRMED: ['CHECKED_IN', 'CANCELLED'],
      CHECKED_IN: ['IN_PROGRESS', 'CANCELLED'],
      IN_PROGRESS: ['COMPLETED', 'CANCELLED'],
    };

    if (!validTransitions[mockAppointments[index].status]?.includes(body.toStatus)) {
      return HttpResponse.json(
        { error: 'InvalidTransition', message: 'Invalid status transition' },
        { status: 400 }
      );
    }

    mockAppointments[index] = {
      ...mockAppointments[index],
      status: body.toStatus,
      updatedAt: new Date().toISOString(),
    };

    return HttpResponse.json(mockAppointments[index]);
  }),

  http.get('/api/v1/appointments/:id/audit-logs', ({ params }) => {
    return HttpResponse.json([
      {
        id: 'audit-1',
        appointmentId: params.id,
        actorId: '11111111-1111-1111-1111-111111111111',
        fromStatus: null,
        toStatus: 'SCHEDULED',
        oldStartTime: null,
        newStartTime: null,
        note: 'Appointment created',
        createdAt: new Date(Date.now() - 86400000).toISOString(),
        actor: mockStaff[0],
        actorName: mockStaff[0].fullName,
      },
      {
        id: 'audit-2',
        appointmentId: params.id,
        actorId: '11111111-1111-1111-1111-111111111111',
        fromStatus: 'SCHEDULED',
        toStatus: 'CONFIRMED',
        oldStartTime: null,
        newStartTime: null,
        note: 'Confirmed by front desk',
        createdAt: new Date().toISOString(),
        actor: mockStaff[0],
        actorName: mockStaff[0].fullName,
      },
    ]);
  }),

  http.post('/api/v1/appointments/reminders/dispatch', () => {
    return HttpResponse.json({
      dispatchedCount: 2,
      checkedWindowStart: new Date(Date.now() - 3600000).toISOString(),
      checkedWindowEnd: new Date().toISOString(),
    });
  }),
];

// Create worker for browser
export const worker = setupWorker(...handlers);
