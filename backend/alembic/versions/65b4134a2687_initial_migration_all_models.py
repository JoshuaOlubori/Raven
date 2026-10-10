"""Initial migration: all models

Revision ID: 65b4134a2687
Revises:
Create Date: 2026-10-10 06:54:06.066676

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "65b4134a2687"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # staff table
    op.create_table(
        "staff",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_staff"),
        sa.UniqueConstraint("email", name="uq_staff_email"),
    )
    op.create_index("ix_staff_email", "staff", ["email"], unique=True)
    op.create_index("ix_staff_role", "staff", ["role"], unique=False)

    # dental_services table
    op.create_table(
        "dental_services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dental_services"),
        sa.UniqueConstraint("name", name="uq_dental_services_name"),
    )
    op.create_index("ix_dental_services_name", "dental_services", ["name"], unique=True)
    op.create_index(
        "ix_dental_services_is_active", "dental_services", ["is_active"], unique=False
    )

    # patients table
    op.create_table(
        "patients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("emergency_contact_name", sa.String(), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(), nullable=True),
        sa.Column("medical_alerts", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_patients"),
    )
    op.create_index(
        "ix_patients_last_first", "patients", ["last_name", "first_name"], unique=False
    )
    op.create_index("ix_patients_phone", "patients", ["phone"], unique=False)
    op.create_index("ix_patients_is_active", "patients", ["is_active"], unique=False)

    # working_shifts table
    op.create_table(
        "working_shifts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dentist_id", sa.Uuid(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_working_shifts"),
        sa.ForeignKeyConstraint(
            ["dentist_id"],
            ["staff.id"],
            ondelete="CASCADE",
            name="fk_working_shifts_dentist_id_staff",
        ),
        sa.UniqueConstraint(
            "dentist_id", "day_of_week", "start_time", name="uq_dentist_day_start"
        ),
    )
    op.create_index(
        "ix_working_shifts_dentist_id", "working_shifts", ["dentist_id"], unique=False
    )

    # time_off_blocks table
    op.create_table(
        "time_off_blocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dentist_id", sa.Uuid(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_time_off_blocks"),
        sa.ForeignKeyConstraint(
            ["dentist_id"],
            ["staff.id"],
            ondelete="CASCADE",
            name="fk_time_off_blocks_dentist_id_staff",
        ),
    )
    op.create_index(
        "ix_time_off_blocks_dentist_id", "time_off_blocks", ["dentist_id"], unique=False
    )
    op.create_index(
        "ix_time_off_blocks_start_time", "time_off_blocks", ["start_time"], unique=False
    )
    op.create_index(
        "ix_time_off_blocks_end_time", "time_off_blocks", ["end_time"], unique=False
    )
    op.create_index(
        "ix_time_off_blocks_dentist_start_end",
        "time_off_blocks",
        ["dentist_id", "start_time", "end_time"],
        unique=False,
    )

    # appointments table
    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("dentist_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="SCHEDULED"),
        sa.Column("cancellation_reason", sa.String(), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            ondelete="CASCADE",
            name="fk_appointments_patient_id_patients",
        ),
        sa.ForeignKeyConstraint(
            ["dentist_id"],
            ["staff.id"],
            ondelete="CASCADE",
            name="fk_appointments_dentist_id_staff",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["dental_services.id"],
            ondelete="CASCADE",
            name="fk_appointments_service_id_dental_services",
        ),
    )
    op.create_index(
        "ix_appointments_patient_id", "appointments", ["patient_id"], unique=False
    )
    op.create_index(
        "ix_appointments_dentist_id", "appointments", ["dentist_id"], unique=False
    )
    op.create_index(
        "ix_appointments_service_id", "appointments", ["service_id"], unique=False
    )
    op.create_index(
        "ix_appointments_start_time", "appointments", ["start_time"], unique=False
    )
    op.create_index(
        "ix_appointments_end_time", "appointments", ["end_time"], unique=False
    )
    op.create_index("ix_appointments_status", "appointments", ["status"], unique=False)
    op.create_index(
        "ix_appointments_dentist_start_end_status",
        "appointments",
        ["dentist_id", "start_time", "end_time", "status"],
        unique=False,
    )
    op.create_index(
        "ix_appointments_reminder_sent_at",
        "appointments",
        ["reminder_sent_at"],
        unique=False,
    )

    # appointment_audit_logs table
    op.create_table(
        "appointment_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(), nullable=True),
        sa.Column("to_status", sa.String(), nullable=True),
        sa.Column("old_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_appointment_audit_logs"),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            ondelete="CASCADE",
            name="fk_appointment_audit_logs_appointment_id_appointments",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["staff.id"], name="fk_appointment_audit_logs_actor_id_staff"
        ),
    )
    op.create_index(
        "ix_appointment_audit_logs_appointment_id",
        "appointment_audit_logs",
        ["appointment_id"],
        unique=False,
    )
    op.create_index(
        "ix_appointment_audit_logs_actor_id",
        "appointment_audit_logs",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_appointment_created",
        "appointment_audit_logs",
        ["appointment_id", "created_at"],
        unique=False,
    )

    # alembic_version table is managed by alembic automatically


def downgrade() -> None:
    op.drop_index(
        "ix_audit_logs_appointment_created", table_name="appointment_audit_logs"
    )
    op.drop_index(
        "ix_appointment_audit_logs_actor_id", table_name="appointment_audit_logs"
    )
    op.drop_index(
        "ix_appointment_audit_logs_appointment_id", table_name="appointment_audit_logs"
    )
    op.drop_table("appointment_audit_logs")

    op.drop_index("ix_appointments_reminder_sent_at", table_name="appointments")
    op.drop_index("ix_appointments_dentist_start_end_status", table_name="appointments")
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_end_time", table_name="appointments")
    op.drop_index("ix_appointments_start_time", table_name="appointments")
    op.drop_index("ix_appointments_service_id", table_name="appointments")
    op.drop_index("ix_appointments_dentist_id", table_name="appointments")
    op.drop_index("ix_appointments_patient_id", table_name="appointments")
    op.drop_table("appointments")

    op.drop_index("ix_time_off_blocks_dentist_start_end", table_name="time_off_blocks")
    op.drop_index("ix_time_off_blocks_end_time", table_name="time_off_blocks")
    op.drop_index("ix_time_off_blocks_start_time", table_name="time_off_blocks")
    op.drop_index("ix_time_off_blocks_dentist_id", table_name="time_off_blocks")
    op.drop_table("time_off_blocks")

    op.drop_index("ix_working_shifts_dentist_id", table_name="working_shifts")
    op.drop_table("working_shifts")

    op.drop_index("ix_patients_is_active", table_name="patients")
    op.drop_index("ix_patients_phone", table_name="patients")
    op.drop_index("ix_patients_last_first", table_name="patients")
    op.drop_table("patients")

    op.drop_index("ix_dental_services_is_active", table_name="dental_services")
    op.drop_index("ix_dental_services_name", table_name="dental_services")
    op.drop_table("dental_services")

    op.drop_index("ix_staff_role", table_name="staff")
    op.drop_index("ix_staff_email", table_name="staff")
    op.drop_table("staff")
