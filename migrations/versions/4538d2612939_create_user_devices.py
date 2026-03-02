"""create_user_devices

Revision ID: 4538d2612939
Revises: 87919323c62e
Create Date: 2026-03-02 12:29:34.625950

"""
from typing import Sequence, Union

from migrations.helper import run_sql_down, run_sql_up



# revision identifiers, used by Alembic.
revision: str = '4538d2612939'
down_revision: Union[str, Sequence[str], None] = '87919323c62e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    run_sql_up("create_user_devices")



def downgrade() -> None:
    run_sql_down("create_user_devices")
