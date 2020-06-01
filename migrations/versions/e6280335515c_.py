"""empty message

Revision ID: e6280335515c
Revises: 696291d72caf
Create Date: 2020-06-01 17:45:21.222861

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'e6280335515c'
down_revision = '696291d72caf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('schedules', sa.Column('urgency', mysql.ENUM('1', '2', '3'), nullable=True))
    op.alter_column('schedules', 'end',
               existing_type=sa.DATE(),
               nullable=False)
    op.alter_column('schedules', 'start',
               existing_type=sa.DATE(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('schedules', 'start',
               existing_type=sa.DATE(),
               nullable=True)
    op.alter_column('schedules', 'end',
               existing_type=sa.DATE(),
               nullable=True)
    op.drop_column('schedules', 'urgency')
    # ### end Alembic commands ###
