"""empty message

Revision ID: 4f8ec1884351
Revises: 6fdcfe3bb7b7
Create Date: 2020-05-30 10:33:22.925797

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f8ec1884351'
down_revision = '6fdcfe3bb7b7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('teams', sa.Column('inv_code', sa.String(length=16), nullable=True))
    op.create_unique_constraint(None, 'teams', ['inv_code'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'teams', type_='unique')
    op.drop_column('teams', 'inv_code')
    # ### end Alembic commands ###
