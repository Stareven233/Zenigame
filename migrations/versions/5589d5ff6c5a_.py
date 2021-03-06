"""empty message

Revision ID: 5589d5ff6c5a
Revises: 62b3ef735c99
Create Date: 2020-06-10 16:42:23.894913

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '5589d5ff6c5a'
down_revision = '62b3ef735c99'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=32), nullable=False),
    sa.Column('desc', sa.String(length=64), nullable=True),
    sa.Column('assignee', sa.Integer(), nullable=False),
    sa.Column('datetime', sa.DateTime(), nullable=True),
    sa.Column('deadline', sa.DateTime(), nullable=False),
    sa.Column('finish', sa.BOOLEAN(), nullable=True),
    sa.Column('team_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(('team_id',), ['teams.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_datetime'), 'tasks', ['datetime'], unique=False)
    op.create_table('archives',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=32), nullable=False),
    sa.Column('type', mysql.TINYINT(), nullable=False),
    sa.Column('filename', sa.String(length=40), nullable=False),
    sa.Column('datetime', sa.DateTime(), nullable=True),
    sa.Column('content', mysql.TEXT(), nullable=True),
    sa.Column('task_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(('task_id',), ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_archives_filename'), 'archives', ['filename'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_archives_filename'), table_name='archives')
    op.drop_table('archives')
    op.drop_index(op.f('ix_tasks_datetime'), table_name='tasks')
    op.drop_table('tasks')
    # ### end Alembic commands ###
