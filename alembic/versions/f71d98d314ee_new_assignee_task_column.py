"""new_assignee_task_column

Revision ID: f71d98d314ee
Revises: cca6266c6c33
Create Date: 2026-08-06 18:06:43.654110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f71d98d314ee'
down_revision: Union[str, Sequence[str], None] = 'cca6266c6c33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

task_status_enum = sa.Enum('IN_PROGRESS', 'COMPLETED', 'REVIEW', 'TODO', name='taskstatus')


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create the taskstatus enum type first
    task_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Convert status column from BOOLEAN to taskstatus enum
    op.alter_column('tasks', 'status',
               existing_type=sa.BOOLEAN(),
               type_=task_status_enum,
               existing_nullable=False,
               postgresql_using="CASE WHEN status IS TRUE THEN 'COMPLETED'::taskstatus ELSE 'TODO'::taskstatus END")

    # 3. Add assignee_id column with FK
    op.add_column('tasks', sa.Column('assignee_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_tasks_assignee_id', 'tasks', 'users', ['assignee_id'], ['public_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Drop FK and assignee_id column
    op.drop_constraint('fk_tasks_assignee_id', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'assignee_id')

    # 2. Convert status column from ENUM back to BOOLEAN
    op.alter_column('tasks', 'status',
               existing_type=task_status_enum,
               type_=sa.BOOLEAN(),
               existing_nullable=False,
               postgresql_using="CASE WHEN status::text = 'COMPLETED' THEN TRUE ELSE FALSE END")

    # 3. Drop taskstatus enum type
    task_status_enum.drop(op.get_bind(), checkfirst=True)
