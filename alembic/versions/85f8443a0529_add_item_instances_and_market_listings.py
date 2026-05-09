"""add item_instances and market_listings

Revision ID: 85f8443a0529
Revises: 716c0314518d
Create Date: 2026-05-09 23:49:19.934961
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '85f8443a0529'
down_revision: Union[str, None] = '716c0314518d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'item_instances',
        sa.Column('id',            postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('owner_id',      postgresql.UUID(as_uuid=True), sa.ForeignKey('characters.id'), nullable=False),
        sa.Column('definition_id', sa.String(20),  nullable=False),
        sa.Column('item_name',     sa.String(100), nullable=False),
        sa.Column('item_type',     sa.String(20),  nullable=False),
        sa.Column('rarity',        sa.String(20),  nullable=False),
        sa.Column('enhance_level', sa.Integer(),   default=0),
        sa.Column('is_bound',      sa.Boolean(),   default=False),
        sa.Column('is_equipped',   sa.Boolean(),   default=False),
        sa.Column('is_in_market',  sa.Boolean(),   default=False),
        sa.Column('created_at',    sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'market_listings',
        sa.Column('id',               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('seller_id',        postgresql.UUID(as_uuid=True), sa.ForeignKey('characters.id'), nullable=False),
        sa.Column('item_instance_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('item_instances.id'), nullable=False),
        sa.Column('price_gold',       sa.BigInteger(), nullable=False),
        sa.Column('item_name',        sa.String(100), nullable=False),
        sa.Column('item_type',        sa.String(20),  nullable=False),
        sa.Column('rarity',           sa.String(20),  nullable=False),
        sa.Column('enhance_level',    sa.Integer(),   default=0),
        sa.Column('listed_at',        sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at',       sa.DateTime(timezone=True), nullable=False),
        sa.Column('status',           sa.String(20),  default='ACTIVE'),
    )


def downgrade() -> None:
    op.drop_table('market_listings')
    op.drop_table('item_instances')