# Glossary

Terms and definitions established during PRD grilling and spec design to maintain a shared domain vocabulary.

- **Clinic**: A single physical dental practice location operating in a designated canonical timezone (`CLINIC_TIMEZONE`).
- **Staff**: An internal user with credentials (`ADMIN`, `RECEPTIONIST`, or `DENTIST`).
- **Patient**: An individual receiving dental care, identified by demographics (name, DOB, phone, email, emergency contact) and medical alert flags (allergies, medical conditions). Patients have no login accounts in v1.
- **Dental Service**: A specific procedure (e.g., Routine Cleaning, Extraction) with a default duration in minutes and active status.
- **Working Shift**: A recurring weekly schedule interval during which a Dentist is on duty and available for appointments.
- **Time-Off Block**: An ad-hoc interval (e.g., vacation, lunch, sick leave) during which a Dentist is unavailable.
- **Available Slot**: A dynamically computed open time window within a Dentist's working shift not occupied by an active appointment or blocked time, matching a service duration.
- **Appointment**: A booked visit linking a Patient, Dentist, and Dental Service to a specific start and end time.
- **Appointment State**: The lifecycle phase of an appointment: `SCHEDULED`, `CONFIRMED`, `CHECKED_IN`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, or `NO_SHOW`.
- **Cancellation Reason**: Mandatory free-text or categorized explanation required whenever an appointment transitions to `CANCELLED`.
- **Appointment Audit Log**: An append-only historical log recording every appointment reschedule, cancellation, and status transition along with the acting staff ID and timestamp.
- **Notification**: An asynchronous message (booking confirmation or 24h pre-visit reminder) dispatched to the patient via a pluggable notification adapter.
