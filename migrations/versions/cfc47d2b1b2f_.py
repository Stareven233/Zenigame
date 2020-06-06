"""empty message

Revision ID: cfc47d2b1b2f
Revises: 
Create Date: 2020-06-06 13:00:27.772579

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'cfc47d2b1b2f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('schedules', 'desc')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('schedules', sa.Column('desc', mysql.VARCHAR(length=32), nullable=False))
    # ### end Alembic commands ###