"""Create vehicle digital twin tables.

Revision ID: 20260912_0002
Revises: 20260912_0001
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_0002"
down_revision: str | None = "20260912_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_VEHICLE_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("make", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("powertrain", sa.String(length=30), nullable=False),
        sa.Column("vin_hash", sa.String(length=128), nullable=True),
        sa.Column("mileage_km", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("mileage_km >= 0", name="ck_vehicles_mileage_nonnegative"),
        sa.CheckConstraint("year BETWEEN 1886 AND 2100", name="ck_vehicles_year"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicles_user_id", "vehicles", ["user_id"], unique=False)

    op.create_table(
        "vehicle_states",
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("speed_kph", sa.Float(), nullable=False),
        sa.Column("gear", sa.String(length=1), nullable=False),
        sa.Column("battery_soc", sa.Float(), nullable=False),
        sa.Column("range_km", sa.Float(), nullable=False),
        sa.Column("climate_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("seat_heat_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("window_position_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("door_state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("light_state", sa.String(length=20), nullable=False),
        sa.Column("charge_status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("battery_soc BETWEEN 0 AND 100", name="ck_vehicle_states_battery_soc"),
        sa.CheckConstraint("gear IN ('P', 'R', 'N', 'D')", name="ck_vehicle_states_gear"),
        sa.CheckConstraint("range_km >= 0", name="ck_vehicle_states_range_nonnegative"),
        sa.CheckConstraint("speed_kph >= 0", name="ck_vehicle_states_speed_nonnegative"),
        sa.CheckConstraint("version >= 0", name="ck_vehicle_states_version_nonnegative"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("vehicle_id"),
    )

    op.create_table(
        "vehicle_state_audits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("property_name", sa.String(length=40), nullable=False),
        sa.Column("zone", sa.String(length=20), nullable=True),
        sa.Column("old_value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("new_value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vehicle_state_audits_request_id",
        "vehicle_state_audits",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_vehicle_state_audits_vehicle_created",
        "vehicle_state_audits",
        ["vehicle_id", "created_at"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO vehicles
                (id, user_id, make, model, year, powertrain, vin_hash, mileage_km)
            VALUES
                (CAST(:id AS uuid), NULL, 'AutoMind', 'Demo EV', 2026, 'BEV', NULL, 0)
            """
        ).bindparams(id=DEMO_VEHICLE_ID)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO vehicle_states
                (vehicle_id, speed_kph, gear, battery_soc, range_km,
                 climate_json, seat_heat_json, window_position_json, door_state_json,
                 light_state, charge_status, version)
            VALUES
                (CAST(:id AS uuid), 0, 'P', 78, 421,
                 CAST(:climate AS jsonb), CAST(:seat_heat AS jsonb),
                 CAST(:windows AS jsonb), CAST(:doors AS jsonb),
                 'OFF', 'IDLE', 0)
            """
        ).bindparams(
            id=DEMO_VEHICLE_ID,
            climate='{"driver": 22, "passenger": 22}',
            seat_heat='{"driver": 0, "passenger": 0}',
            windows='{"driver": 0, "passenger": 0}',
            doors='{"driver": "CLOSED", "passenger": "CLOSED"}',
        )
    )


def downgrade() -> None:
    op.drop_index("ix_vehicle_state_audits_vehicle_created", table_name="vehicle_state_audits")
    op.drop_index("ix_vehicle_state_audits_request_id", table_name="vehicle_state_audits")
    op.drop_table("vehicle_state_audits")
    op.drop_table("vehicle_states")
    op.drop_index("ix_vehicles_user_id", table_name="vehicles")
    op.drop_table("vehicles")
