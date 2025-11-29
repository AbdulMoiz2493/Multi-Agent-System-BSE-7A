"""Add AI models - insights and chatbot logs

Revision ID: add_ai_models
Revises: 
Create Date: 2025-11-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_ai_models'
down_revision = '001_initial_schema'  # Depends on initial schema
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create insighttype enum (only if it doesn't exist)
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'insighttype')"
    )).scalar()
    if not result:
        op.execute("CREATE TYPE insighttype AS ENUM ('consistency', 'performance', 'recommendation', 'warning')")
    
    # Create insights table using raw SQL to avoid SQLAlchemy trying to create enum
    op.execute("""
        CREATE TABLE insights (
            id SERIAL NOT NULL,
            user_id INTEGER NOT NULL,
            insight_type insighttype NOT NULL,
            title VARCHAR NOT NULL,
            message TEXT NOT NULL,
            confidence_score INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)
    op.create_index(op.f('ix_insights_id'), 'insights', ['id'], unique=False)
    
    # Create chatbotactiontype enum (only if it doesn't exist)
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chatbotactiontype')"
    )).scalar()
    if not result:
        op.execute("CREATE TYPE chatbotactiontype AS ENUM ('log_study', 'get_status', 'trigger_reminder', 'get_insights')")
    
    # Create chatbot_logs table using raw SQL to avoid SQLAlchemy trying to create enum
    op.execute("""
        CREATE TABLE chatbot_logs (
            id SERIAL NOT NULL,
            user_id INTEGER NOT NULL,
            action_type chatbotactiontype NOT NULL,
            request_data TEXT,
            response_data TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """)
    op.create_index(op.f('ix_chatbot_logs_id'), 'chatbot_logs', ['id'], unique=False)


def downgrade() -> None:
    # Drop chatbot_logs table
    op.drop_index(op.f('ix_chatbot_logs_id'), table_name='chatbot_logs')
    op.drop_table('chatbot_logs')
    # Drop enum only if it exists
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chatbotactiontype')"
    )).scalar()
    if result:
        op.execute('DROP TYPE chatbotactiontype')
    
    # Drop insights table
    op.drop_index(op.f('ix_insights_id'), table_name='insights')
    op.drop_table('insights')
    # Drop enum only if it exists
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'insighttype')"
    )).scalar()
    if result:
        op.execute('DROP TYPE insighttype')
