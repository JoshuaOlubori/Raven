# Google Stitch screen prompts — Raven

**Purpose:** Turn the approved Raven Dental Clinic Appointment Tracker requirements into a coherent staff-facing web application concept in Google Stitch.

**Product grounding:** This repository currently contains the backend and approved PRD/specs, not an existing frontend. Treat the prompts below as proposed UI views for the API-defined v1. They are desktop-first because reception and clinical staff use shared clinic workstations; make core layouts responsive down to tablet widths.

## How to use these prompts

1. Attach the site image you provide as the visual reference.
2. Start with the **Shared visual direction** prompt to establish a consistent design language.
3. Generate each numbered screen as a separate screen in the same project, keeping the shared navigation, components, typography, and colors consistent.
4. Use realistic fictional patient and staff data. Do not use real medical information.

Replace `[ATTACHED AESTHETIC REFERENCE IMAGE]` with the image attachment in Stitch if it requires an explicit reference instruction.

## Shared visual direction prompt

> Design a polished internal web application for **Raven Dental**, a single-location dental clinic appointment and operations system used by receptionists, dentists, and office managers. Use the attached image **[ATTACHED AESTHETIC REFERENCE IMAGE]** as an aesthetic reference only: derive its color mood, typography character, contrast, corner treatment, spacing rhythm, and surface/shadow style. Do not copy its subject matter, content, brand, or page composition. Keep the result calm, trustworthy, precise, and approachable for a busy clinical workplace. Prioritize legibility, fast scanning, predictable controls, and clear status communication over decorative graphics.
>
> Create a desktop-first responsive staff application with a persistent left navigation rail/sidebar, compact top bar with page title, date/context controls, notifications/connection state where relevant, and signed-in user/role menu. Use a restrained clinical palette sampled from the reference; reserve strong semantic colors for appointment states and medical alerts. Use a consistent 8-point spacing rhythm, clear type hierarchy, accessible contrast, visible keyboard focus, minimum comfortable control sizes, and compact but readable tables. Use realistic fictional content. The clinic is one physical location and all schedule times are shown in the clinic's local time.
>
> App areas: Today, Appointments, Patients, and (for Admin) Services, Schedules, Staff. Dentists see their own clinical schedule and time-off tools. Receptionists can manage patients and bookings but cannot manage staff, edit services, or change clinical treatment data. Admins can manage staff, service catalog, and provider shifts. Do not show navigation or actions that the current role cannot use.
>
> The product has no patient-facing portal or patient login. Do not invent patient self-booking, billing, insurance, prescriptions, treatment notes, charting, or clinical record editing. The backend supports appointment status updates and optional status-transition notes, but there is no dedicated treatment-notes feature. Appointment audit history is available per appointment; there is no global audit-log screen. Booking confirmations and reminders are automatic system behavior; there is no notification-settings screen. Show these limits in the generated product concept rather than implying those features exist.
>
> Build reusable components for: status badges, appointment rows/cards, patient identity, medical-alert callouts, dentist/service selectors, date navigation, search, filter chips, confirmation dialogs, empty/loading/error states, and permission-aware actions. Keep patient medical alerts visually prominent in patient and appointment contexts without making the whole interface alarming. Use fictional names and dates.

## 1. Staff sign-in

> Create the Raven Dental staff sign-in screen. Use the attached aesthetic reference **[ATTACHED AESTHETIC REFERENCE IMAGE]** for the visual style, not its content. This is an internal staff portal, not a public dental marketing site. Show a quiet Raven Dental wordmark area, a concise “Staff sign in” heading, email/username field, password field with show/hide control, primary Sign in button, and a clear inline invalid-credentials/inactive-account error state. Keep any help text understated; do not invent sign-up, patient login, social login, or password reset flows because those are not defined in v1. Make the form centered and focused with sufficient contrast and keyboard focus states. Include a subtle clinic operations descriptor and fictional, non-sensitive background details only if they support the reference aesthetic.

## 2. Today operations dashboard — Admin and Receptionist

> Design the signed-in Raven Dental front-desk “Today” dashboard for an Admin or Receptionist, using **[ATTACHED AESTHETIC REFERENCE IMAGE]** as style inspiration. The goal is to scan today's clinic activity and act quickly. Use a persistent staff sidebar and a main content area with date navigation, a prominent “New appointment” action, and a subtle live connection indicator for appointment updates.
>
> Show a compact summary row (appointments today, checked in, currently in progress, and next available/next visit if meaningful), then an operational schedule grouped by dentist or a clear chronological timeline. Each appointment should show local start/end time, patient name, service, dentist, and status badge. Add a waiting/check-in section for arrivals and clear actions such as Open appointment, Check in, and Mark no-show only where valid. Include useful filters for date, dentist, and status. Include a medical-alert icon/summary when the patient has alerts, without exposing excessive detail in the overview.
>
> Show realistic mixed states: scheduled, confirmed, checked in, in progress, completed, cancelled, and no-show. Cancelled appointments should be visually quiet and must not appear bookable/active. Include an empty-day state, loading skeleton, and a “Connection interrupted — refresh schedule” banner variant; a reconnect/resync may require refetching current appointments. No billing, treatment notes, or unsupported metrics.

## 3. Appointments calendar

> Create Raven Dental’s Appointments calendar screen for staff. Follow the attached reference **[ATTACHED AESTHETIC REFERENCE IMAGE]** for visual language. Use a dense but readable day/week calendar with a date picker and previous/next/today controls, day/week toggle, dentist filter, and status filter. Distinguish each dentist’s lane with accessible color coding and labeled names; appointments appear as blocks sized by their actual duration and show patient, service, and status. A 45-minute procedure should visibly occupy more time than a 15-minute visit. Indicate working hours and blocked time-off in the relevant lane; keep cancelled items muted and separate from availability.
>
> Provide a compact agenda/list alternative for smaller screens. Clicking an appointment opens the shared appointment detail view; selecting an open time may start booking with date, time, and dentist prefilled. Keep booking availability authoritative: open-looking gaps are not guaranteed until the app requests dynamic availability. Use clinic-local time. Include loading, no-results, and failed-refresh states. Receptionists/Admins see booking actions; a dentist’s view is restricted to their own schedule. Do not imply drag-and-drop rescheduling unless clearly labeled as a design concept requiring a later UI capability.

## 4. New appointment — booking flow

> Design a multi-step “Book appointment” flow for Raven Dental receptionists and admins, styled using **[ATTACHED AESTHETIC REFERENCE IMAGE]**. The flow must make it difficult to book the wrong patient, service, dentist, or time. Use a clear stepper: (1) Patient, (2) Service and provider, (3) Date and available time, (4) Review and book. Keep a visible summary panel of chosen patient, service duration, dentist, and local appointment time as selections are made.
>
> Patient step: searchable active patient picker with name and phone, plus “Add new patient” entry point. Service/provider step: active service cards or a compact selector showing name and duration; dentist selector can be “Any available dentist” or a specific dentist. Date/time step: date navigation and slots returned by live availability; every slot shows local start time and dentist name. Show a helpful no-slots state with date/provider alternatives. Review step: verify patient, date, time, duration/end time, provider, and any medical-alert summary before a prominent “Confirm appointment” action. New booking begins as Scheduled.
>
> Include validation and conflict states: required patient/service/time, slot became unavailable / conflict (409) with a clear retry path, and successful booking confirmation with a link to open appointment details. Do not present a slot as reserved before successful booking. Do not add insurance, payment, patient self-service, or clinical notes. Only Admin and Receptionist can book.

## 5. Appointment detail and audit history

> Create the shared Raven Dental appointment detail screen, preferably as a spacious side panel or dedicated detail page that can open from the Today dashboard, calendar, or patient history. Use **[ATTACHED AESTHETIC REFERENCE IMAGE]** for its visual style. Present a strong header with patient name, current status badge, service, and local appointment date/time. Include dentist/provider, scheduled duration, contact details appropriate to staff, and a prominent medical-alert callout when alerts exist.
>
> Below the summary, show a chronological appointment activity timeline populated from the per-appointment audit history: status changes, reschedules, cancellation reason, actor, timestamp, and any recorded transition note. Separate current appointment facts from historical activity. Show role- and state-aware actions: Admin/Receptionist may reschedule or cancel eligible scheduled/confirmed appointments, check in eligible arrivals, or mark no-show where valid; Dentist may begin treatment from Checked in and complete from In progress. Cancellation opens a required-reason dialog. Terminal states (Completed, Cancelled, No-show) have no further state actions. Do not show delete appointment.
>
> Include loading, missing record, and audit-history-empty states. Keep the action labels explicit and require confirmation for cancellation. Do not add clinical treatment notes, global audit navigation, or edit controls for medical alerts from this view.

## 6. Patient directory

> Design the Raven Dental Patients directory for authenticated staff, using **[ATTACHED AESTHETIC REFERENCE IMAGE]** for aesthetics. Provide a page title, prominent patient search that matches name or phone, “Add patient” action for Admin/Receptionist, and a readable paginated table/list. Suggested columns: patient, phone, date of birth/age, medical alert indicator, and record status. Make search and pagination visible and efficient; active patients are shown by default. Clicking a row opens the patient profile. Medical-alert indicators should be clear but reveal only a concise preview until staff open the record.
>
> Dentist users may search and view patient information but cannot create, edit, or archive patient records. Receptionists and Admins can add, edit, and soft-archive a patient. Include initial, loading, no-match, and request-error states. Use fictional patient data. Do not show patient logins, billing, insurance, or unsupported filters.

## 7. Patient profile and visit history

> Create a Raven Dental patient profile screen with the style of **[ATTACHED AESTHETIC REFERENCE IMAGE]**. Show patient full name, date of birth, primary phone, email, emergency contact, active/archived status, and a highly visible medical-alert section near the top. Avoid clutter and make critical allergy/condition text easy to scan. Provide Edit and Archive actions only for Admin/Receptionist; Dentists are read-only.
>
> Add an Appointment history section using the appointment list filtered by patient. Show date/time, service, dentist, and lifecycle status with a link to each appointment detail. Include a “Book appointment” action for Admin/Receptionist that opens booking with this patient already selected. For archived patients, make the archived state explicit and do not offer new booking. Include empty history, loading, and unavailable-record states. The backend does not expose clinical notes or a medical chart, so do not fabricate either.

## 8. Create/edit patient form

> Design one reusable Raven Dental patient form screen with create and edit variants, using **[ATTACHED AESTHETIC REFERENCE IMAGE]** as the visual reference. Group the form into “Patient details” (first name, last name, date of birth, primary phone, email), “Emergency contact” (name and phone), and “Medical alerts” (allergies, conditions, important notes as a concise text area). Clearly mark required fields: first name, last name, date of birth, and phone. Use helpful phone/date formats, inline validation, and visible save/cancel actions.
>
> This form is for Admins and Receptionists only. In edit mode, show existing information; do not expose backend IDs or technical fields. On save, show success and return to the profile. Include validation errors for missing/invalid required information and a save-failure state that preserves entered data. Patient archiving is a separate confirmed action, not part of this form. Do not include treatment notes, prescriptions, insurance, or billing fields.

## 9. Dental services catalog

> Create the Admin-only Raven Dental Services catalog screen, styled from **[ATTACHED AESTHETIC REFERENCE IMAGE]**. Show a manageable table or card list of service name, short description, duration in minutes, and Active/Inactive state. Add a primary “Add service” action and clear edit/deactivate controls. An edit/create dialog or detail screen should include service name, description, duration, active toggle, and validation (duration must be a positive number no greater than 480 minutes). Use duration chips or another easy-to-scan treatment for common lengths such as 15, 30, 45, 60, and 90 minutes.
>
> Deactivation is a soft catalog state: explain that inactive services remain on historical appointments but cannot be selected for new booking. Receptionists and Dentists can view the active catalog for booking/consultation but do not see management controls. Include empty, loading, duplicate-name/validation, and save-error states. Do not add pricing, insurance codes, treatment plans, or clinical content.

## 10. Provider schedules and time off — Admin

> Design an Admin schedule-management screen for Raven Dental, guided visually by **[ATTACHED AESTHETIC REFERENCE IMAGE]**. Provide dentist selector and a weekly recurring shift grid (Monday–Sunday) with each working interval shown as local start/end time. Admin can add a shift by choosing dentist, weekday, start, and end; can remove a shift with confirmation. Make overlapping/invalid ranges understandable. Clearly distinguish this recurring template from one-off time-off blocks.
>
> Add a date-range view/list of the selected dentist’s time-off blocks, with start/end, reason, and remove action. Admin may add time off for any dentist. Show availability preview for a chosen service/date by listing the dynamically returned open slots; communicate that appointments and time off are excluded from availability. Include no-shifts, no-time-off, loading, and validation/error states. Use clinic-local time and avoid suggesting that staff can directly create appointments from the shift template. Dentists cannot manage other providers’ recurring shifts.

## 11. Dentist workspace — own day and time off

> Design a focused Raven Dental dentist workspace for a Dentist role, using the visual mood of **[ATTACHED AESTHETIC REFERENCE IMAGE]**. This is a clinical day/operatory view, not a full practice-admin dashboard. Start with “My schedule” and date navigation; show only the signed-in dentist’s appointments in a clear chronological agenda with time, patient name, service, status, and medical-alert indicator. Make the next/current appointment easy to identify, and show check-in readiness.
>
> For eligible appointments, provide the supported transitions: Checked in → “Start appointment” (In progress), and In progress → “Complete appointment”. Keep prior completed/cancelled/no-show visits visible but quiet and read-only. Include a “Request/add time off” action that creates a block for the dentist’s own schedule, with date/time and optional reason, plus a list of their upcoming blocks and removal action where supported. The dentist can view/search patient records but cannot edit patient profiles, book/reschedule/cancel appointments, manage service catalog, create staff, or edit recurring shifts. Include empty-day, loading, live-update/reconnect, and error states. Do not invent charting or treatment-note entry.

## 12. Staff management

> Create the Admin-only Raven Dental Staff screen, using **[ATTACHED AESTHETIC REFERENCE IMAGE]** as aesthetic direction. Show a searchable/filtered list of active staff with name, email, role (Admin, Receptionist, Dentist), and account status. Provide “Add staff” and edit actions for Admin. The create/edit form includes full name, email, role, and password only for account creation; show password requirements without displaying or returning a password after save. For existing staff, allow only fields exposed by the backend and make active/inactive status clear. Do not invent invitation emails, password reset, profile photos, or access controls not present in v1.
>
> Receptionists may view the staff list/detail but cannot create or edit accounts; Dentists do not need staff-management navigation. Include empty, validation, duplicate email, loading, and save-error states. Use realistic fictional clinic staff.

## Screen consistency and interaction notes

- Keep the shared navigation and components consistent across all prompts; tailor visible pages and actions by role.
- Appointment states are **Scheduled, Confirmed, Checked in, In progress, Completed, Cancelled, No-show**. Only show transitions allowed by the current state.
- The core receptionist journey is: find/create patient → select service and dentist → request available slots for a date → review → book → see appointment on Today/calendar → check in → inspect history as needed.
- The core dentist journey is: open own daily schedule → review patient/medical alert → start a checked-in visit → complete it → manage own time off.
- The core admin journey includes all appointment/patient operations plus staff, catalog, recurring shifts, and provider time-off management.
- Use clinic local time throughout. Appointment intervals derive from the selected service duration; dynamic availability is authoritative.
- Confirmation/reminder notifications are automatic backend behavior and need no staff-facing management page.
- Do not imply features that are absent from the API: patient portal, booking by patients, clinical chart/treatment notes, billing, insurance, pricing, a global audit screen, notification preferences, or permanent appointment deletion.
