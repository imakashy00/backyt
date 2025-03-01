"""Removed Accounts table.

Revision ID: 5496e1ba2fe4
Revises: 1fee33d03712
Create Date: 2025-02-06 03:44:15.899624

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5496e1ba2fe4'
down_revision: Union[str, None] = '1fee33d03712'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('accounts')
    op.add_column('users', sa.Column('google_id', sa.String(length=255), nullable=False))
    op.create_unique_constraint(None, 'users', ['google_id'])
    op.drop_column('users', 'email_verified')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('email_verified', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'google_id')
    op.create_table('accounts',
    sa.Column('id', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('provider', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('provider_account_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('refresh_token', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('expires_at', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='accounts_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='accounts_pkey')
    )
    # ### end Alembic commands ###
