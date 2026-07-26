"""add file_shares table

Revision ID: add_file_shares_0001
Revises: 1e5a45c6b00a
Create Date: 2026-07-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_file_shares_0001'
down_revision = '1e5a45c6b00a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'file_shares',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_name', sa.String(length=512), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=True, default=0),
        sa.Column('password_hash', sa.String(length=256), nullable=True),
        sa.Column('max_downloads', sa.Integer(), nullable=True),
        sa.Column('download_count', sa.Integer(), nullable=True, default=0, server_default='0'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['admins.id'], name=op.f('fk_file_shares_created_by_id_admins')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_file_shares')),
    )
    op.create_index(op.f('ix_file_shares_token'), 'file_shares', ['token'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_file_shares_token'), table_name='file_shares')
    op.drop_table('file_shares')
