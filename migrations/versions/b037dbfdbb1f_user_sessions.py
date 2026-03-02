"""user_sessions

Revision ID: b037dbfdbb1f
Revises: 4538d2612939
Create Date: 2026-03-02 12:32:01.365622

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = 'b037dbfdbb1f'
down_revision: Union[str, Sequence[str], None] = '4538d2612939'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
