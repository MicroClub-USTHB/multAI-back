"""user_sessions

Revision ID: b037dbfdbb1f
Revises: 4538d2612939
Create Date: 2026-03-02 12:32:01.365622

"""
from typing import Sequence, Union

from migrations.helper import run_sql_down, run_sql_up



# revision identifiers, used by Alembic.
revision: str = 'b037dbfdbb1f'
down_revision: Union[str, Sequence[str], None] = '4538d2612939'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    run_sql_up("user_sessions")


def downgrade() -> None:
    run_sql_down("user_sessions")
