"""empty message

Revision ID: e74ba710e5fb
Revises: 5589d5ff6c5a
Create Date: 2020-06-12 18:01:16.673627

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'e74ba710e5fb'
down_revision = '5589d5ff6c5a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('questionnaires',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=32), nullable=False),
    sa.Column('desc', sa.String(length=128), nullable=True),
    sa.Column('datetime', sa.DateTime(), nullable=True),
    sa.Column('deadline', sa.DateTime(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(('team_id',), ['teams.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('q_questions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('qid', mysql.TINYINT(), nullable=False),
    sa.Column('desc', sa.String(length=32), nullable=False),
    sa.Column('type', mysql.TINYINT(), nullable=False),
    sa.Column('questionnaire_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(('questionnaire_id',), ['questionnaires.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('q_options',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('oid', mysql.TINYINT(), nullable=False),
    sa.Column('desc', sa.String(length=32), nullable=False),
    sa.Column('question_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(('question_id',), ['q_questions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('q_options')
    op.drop_table('q_questions')
    op.drop_table('questionnaires')
    # ### end Alembic commands ###
