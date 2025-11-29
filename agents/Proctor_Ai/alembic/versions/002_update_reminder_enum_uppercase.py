"""Update reminderstatus enum to uppercase

Revision ID: 002_update_reminder_enum_uppercase
Revises: add_ai_models
Create Date: 2025-11-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_enum_uppercase'
down_revision = 'add_ai_models'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if enum exists
    conn = op.get_bind()
    enum_exists = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reminderstatus')"
    )).scalar()
    
    if enum_exists:
        # Check if enum already has uppercase values
        enum_values = conn.execute(sa.text("""
            SELECT enumlabel 
            FROM pg_enum 
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reminderstatus')
            ORDER BY enumsortorder
        """)).fetchall()
        
        # Check if first value is uppercase (assuming PENDING is first)
        if enum_values and enum_values[0][0] == 'PENDING':
            # Enum already has uppercase values, nothing to do
            return
        
        # Enum has lowercase values, need to update
        # First, update any existing data
        table_exists = conn.execute(sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'reminders')"
        )).scalar()
        
        if table_exists:
            # Temporarily change column to text, update values, then change back
            op.execute("ALTER TABLE reminders ALTER COLUMN status TYPE text")
            op.execute("UPDATE reminders SET status = UPPER(status)")
            op.execute("DROP TYPE reminderstatus CASCADE")
            op.execute("CREATE TYPE reminderstatus AS ENUM ('PENDING', 'SENT', 'DELIVERED', 'FAILED')")
            op.execute("ALTER TABLE reminders ALTER COLUMN status TYPE reminderstatus USING status::reminderstatus")
        else:
            # No table, just recreate enum
            op.execute("DROP TYPE reminderstatus CASCADE")
            op.execute("CREATE TYPE reminderstatus AS ENUM ('PENDING', 'SENT', 'DELIVERED', 'FAILED')")
    else:
        # Enum doesn't exist, create it with uppercase values
        op.execute("CREATE TYPE reminderstatus AS ENUM ('PENDING', 'SENT', 'DELIVERED', 'FAILED')")


def downgrade() -> None:
    # Revert to lowercase enum values
    conn = op.get_bind()
    has_data = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM reminders LIMIT 1)"
    )).scalar()
    
    if has_data:
        op.execute("UPDATE reminders SET status = LOWER(status)::text::reminderstatus")
    
    op.execute("DROP TYPE reminderstatus CASCADE")
    op.execute("CREATE TYPE reminderstatus AS ENUM ('pending', 'sent', 'delivered', 'failed')")
    
    conn = op.get_bind()
    table_exists = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'reminders')"
    )).scalar()
    
    if not table_exists:
        op.execute("""
            CREATE TABLE reminders (
                id SERIAL NOT NULL,
                user_id INTEGER NOT NULL,
                scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
                message VARCHAR NOT NULL,
                status reminderstatus,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                PRIMARY KEY (id),
                FOREIGN KEY(user_id) REFERENCES users (id)
            )
        """)
        op.create_index('ix_reminders_id', 'reminders', ['id'], unique=False)

