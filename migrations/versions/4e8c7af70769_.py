"""empty message

Revision ID: 4e8c7af70769
Revises: e74ba710e5fb
Create Date: 2020-06-13 20:42:53.766520

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '4e8c7af70769'
down_revision = 'e74ba710e5fb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('q_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=16), nullable=False),
    sa.Column('datetime', sa.DateTime(), nullable=True),
    sa.Column('questionnaire_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(('questionnaire_id',), ['questionnaires.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('q_answers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('qid', mysql.TINYINT(), nullable=False),
    sa.Column('type', mysql.TINYINT(), nullable=False),
    sa.Column('ans', sa.String(length=512), nullable=False),
    sa.Column('record_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(('record_id',), ['q_records.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.alter_column('archives', 'name',
               existing_type=mysql.VARCHAR(length=32),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('archives', 'name',
               existing_type=mysql.VARCHAR(length=32),
               nullable=False)
    op.drop_table('q_answers')
    op.drop_table('q_records')
    # ### end Alembic commands ###
