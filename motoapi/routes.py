import datetime
import random

from sqlalchemy import exists, select
from flask import (render_template, redirect, url_for, request, jsonify,
    Blueprint)
from flask_restful import reqparse
# from flask_babelex import gettext as _
from flask_jwt_extended import (jwt_required, create_access_token,
    jwt_refresh_token_required, create_refresh_token, decode_token)

from motoapi.utils import (abort, add_token_to_database, current_user,
    valid_email, valid_username, get_user_tokens, revoke_token, unrevoke_token,
    roles_accepted, roles_required, query_with_paging,
    get_random_integer, get_random_string)

from motoapi import motoapi, db
from motoapi.models import TokenBlacklist, User
from motoapi.utils import (abort, current_user,
    valid_email, valid_username, query_with_paging)
from motoapi.fields import user_fields, string

# Blueprints
api_blueprint = Blueprint('api', __name__, template_folder='templates')


login_parser = reqparse.RequestParser()
login_parser.add_argument('username', type=string(empty=False, lower=True),
    required=True, help="Username cannot be blank!")
login_parser.add_argument('password', type=string(empty=False),
    required=True, help="Password cannot be blank!")


register_parser = reqparse.RequestParser()
register_parser.add_argument('email', type=string(email=True, empty=False,
        strip=True, lower=True),
    required=True, help="Email cannot be blank!")
register_parser.add_argument('username', type=string(empty=False, lower=True,
        strip=True),
    required=True, help="Username cannot be blank!")
register_parser.add_argument('password', type=string(empty=False, min_length=8,
        strip=True),
    required=True,
    help="Password cannot be blank!")
register_parser.add_argument('name', type=string(empty=False),
    required=True,
    help="Name cannot be blank!")


@motoapi.route('/')
@motoapi.route('/index')
def index():
    return {'ping': 'pong'}


@api_blueprint.route('/auth/login', methods=['POST'])
def login():
    args = login_parser.parse_args()
    user = User.query.filter_by(username=args.username).first()
    if not user:
        return abort(400, message="Bad username or password", error_code=204)
    if not User.verify_hash(args.password, user.password):
        return abort(400, message="Bad username or password", error_code=204)

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    add_token_to_database(access_token,
        motoapi.config['JWT_IDENTITY_CLAIM'])
    add_token_to_database(refresh_token,
        motoapi.config['JWT_IDENTITY_CLAIM'])
    return jsonify(
        user=user_fields(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires=datetime.datetime.now() + motoapi.config[
            'JWT_ACCESS_TOKEN_EXPIRES']), 200


@api_blueprint.route('/auth/logout', methods=['POST'])
@jwt_required
def logout():
    user = current_user()
    decoded_token = decode_token(request.headers.get('Authorization')[7:])
    token = TokenBlacklist.query.filter_by(jti=decoded_token['jti']).first()
    revoke_token(token.id, user.id)
    return {'success': 1}, 200


@api_blueprint.route('/auth/register', methods=['POST'])
def register():
    args = register_parser.parse_args()
    if User.query.filter(User.username == args.username).count() != 0:
        return abort(400,
            message={'username': 'Username already taken'},
            error_code=201)
    elif User.query.filter(User.email == args.email).count() != 0:
        return abort(400,
            message={'email': 'Email already taken'},
            error_code=202)
    elif not valid_email(args.email):
        return abort(400,
            message={'email': 'Email is not valid'},
            error_code=101)
    elif not valid_username(args.username):
        return abort(400,
            message={'username': 'Username is not valid'},
            error_code=203)

    user = User(
        username=args.username,
        name=args.name,
        password=User.generate_hash(args.password),
        email=args.email,
        )

    db.session.add(user)
    db.session.commit()
    return user_fields(user)


@api_blueprint.route('/auth/refresh', methods=['POST'])
@jwt_refresh_token_required
def refresh():
    # Do the same thing that we did in the login endpoint here
    user = current_user()
    access_token = create_access_token(identity=user.id)
    add_token_to_database(access_token,
        motoapi.config['JWT_IDENTITY_CLAIM'])
    return jsonify({
        'access_token': access_token,
        'refresh_token': request.headers.get('Authorization')[7:],
        'token_expires': datetime.datetime.now() + motoapi.config[
            'JWT_ACCESS_TOKEN_EXPIRES']
        }), 201
