"""changed File Model for title.

Revision ID: 96e9f20dadd8
Revises: 9609fa9a5d5c
Create Date: 2025-02-10 19:19:55.266470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96e9f20dadd8'
down_revision: Union[str, None] = '9609fa9a5d5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('files', 'title')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('files', sa.Column('title', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    # ### end Alembic commands ###
