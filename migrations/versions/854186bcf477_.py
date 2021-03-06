"""empty message

Revision ID: 854186bcf477
Revises: b7654c0e872f
Create Date: 2022-04-30 03:35:45.178454

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '854186bcf477'
down_revision = 'b7654c0e872f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('role',
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('permissions', sa.UnicodeText(), nullable=True),
    sa.Column('update_datetime', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('token_blacklist',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('jti', sa.String(), nullable=False),
    sa.Column('token_type', sa.String(), nullable=False),
    sa.Column('user_identity', sa.String(), nullable=False),
    sa.Column('revoked', sa.Boolean(), nullable=False),
    sa.Column('expires', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user',
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password', sa.String(length=255), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('bio', sa.String(), nullable=True),
    sa.Column('location', sa.String(), nullable=True),
    sa.Column('phone_number', sa.String(length=128), nullable=True),
    sa.Column('gender', sa.String(), nullable=True),
    sa.Column('language', sa.String(), nullable=True),
    sa.Column('interests', sa.String(), nullable=True),
    sa.Column('image_highlights', sa.String(), nullable=True),
    sa.Column('birthday_date', sa.DateTime(), nullable=True),
    sa.Column('profile_image', sa.String(length=255), nullable=True),
    sa.Column('header_image', sa.String(length=255), nullable=True),
    sa.Column('instagram', sa.String(length=255), nullable=True),
    sa.Column('verified_at', sa.DateTime(), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(), nullable=True),
    sa.Column('last_login_at', sa.DateTime(), nullable=True),
    sa.Column('current_login_at', sa.DateTime(), nullable=True),
    sa.Column('last_login_ip', sa.String(length=64), nullable=True),
    sa.Column('current_login_ip', sa.String(length=64), nullable=True),
    sa.Column('login_count', sa.Integer(), nullable=True),
    sa.Column('recovery_code', sa.String(), nullable=True),
    sa.Column('recovery_code_expiration', sa.DateTime(), nullable=True),
    sa.Column('public_address', sa.String(), nullable=True),
    sa.Column('nonce', sa.String(), nullable=True),
    sa.Column('facebook', sa.Boolean(), nullable=True),
    sa.Column('apple', sa.Boolean(), nullable=True),
    sa.Column('configuration', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_table('roles_users',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('role_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['role_id'], ['role.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('roles_users')
    op.drop_table('user')
    op.drop_table('token_blacklist')
    op.drop_table('role')
    # ### end Alembic commands ###
