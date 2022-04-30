import random
import string
import datetime
import re
import requests
from functools import wraps, lru_cache

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity, decode_token
from flask_jwt_extended.exceptions import NoAuthorizationError
from flask_restful import reqparse

from motoapi import motoapi, db, jwt, babel
from motoapi.models import User, TokenBlacklist, Role
from motoapi.fields import user_fields, integer
from motoapi.exceptions import TokenNotFound
from config import Config


def get_random_string(length):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))


def get_random_integer(length):
    numbers = '1234567890'
    return ''.join(random.choice(numbers) for i in range(length))


def current_user():
    user = User.query.filter_by(id=get_jwt_identity()).first()
    if not user:
        raise Exception('Unknown user check that the auth token is correct.')
    return user


def roles_required(*roles):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user = current_user()
            for role_name in roles:
                role = Role.query.filter_by(name=role_name).first()
                if not role or role not in user.roles:
                    raise NoAuthorizationError
            return function(*args, **kwargs)
        return wrapper
    return decorator


def roles_accepted(*roles):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user = current_user()
            for role_name in roles:
                role = Role.query.filter_by(name=role_name).first()
                if role and role in user.roles:
                    return function(*args, **kwargs)
            raise NoAuthorizationError
        return wrapper
    return decorator


@motoapi.after_request
def after_request(response):
    try:
        save_user_ip()
    except Exception:
        pass

    # https://stackoverflow.com/questions/30241911/psycopg2-error-databaseerror-error-with-no-message-from-the-libpq
    db.engine.dispose()

    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers',
        'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods',
        'GET,PUT,POST,DELETE')
    return response


@lru_cache(99999)
def str2bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, int) and v == 1:
        return True
    elif isinstance(v, int) and v == 0:
        return False
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        return None


def valid_email(email):
    if re.match('^[_a-zA-Z0-9-]+(\.[_a-zA-Z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*'
            + '(\.[a-z]{2,4})$', email) == None:
        return False
    return True


def valid_birthday_date(birthday_date):
    today = datetime.date.today()
    age = today.year - birthday_date.year - ((today.month, today.day) < (
            birthday_date.month, birthday_date.day))
    return True if age >= 18 else False


def valid_username(username):
    if re.match(
            '^[a-zA-Z0-9]+(?:[_ -]?[a-zA-Z0-9])*$', username) == None:
        return False
    return True


def add_token_to_database(encoded_token, identity_claim):
    """
    Adds a new token to the database. It is not revoked when it is added.
    :param identity_claim:
    """
    decoded_token = decode_token(encoded_token)
    db_token = TokenBlacklist(
        jti=decoded_token['jti'],
        token_type=decoded_token['type'],
        user_identity=decoded_token[identity_claim],
        expires=datetime.datetime.fromtimestamp(decoded_token['exp']),
        revoked=False,
    )
    db.session.add(db_token)
    db.session.commit()


def is_token_revoked(decoded_token):
    """
    Checks if the given token is revoked or not. Because we are adding all the
    tokens that we create into this database, if the token is not present
    in the database we are going to consider it revoked, as we don't know where
    it was created.
    """
    jti = decoded_token['jti']
    token = TokenBlacklist.query.filter_by(jti=jti).first()
    return token.revoked if token else True


def get_user_tokens(user_identity):
    """
    Returns all of the tokens, revoked and unrevoked, that are stored for the
    given user
    """
    return TokenBlacklist.query.filter_by(user_identity=user_identity).all()


def revoke_token(token_id, user):
    """
    Revokes the given token. Raises a TokenNotFound error if the token does
    not exist in the database
    """
    token = TokenBlacklist.query.filter_by(id=token_id,
        user_identity=str(user)).first()
    if not token:
        raise TokenNotFound("Could not find the token {}".format(token_id))
    token.revoked = True
    db.session.commit()


def unrevoke_token(token_id, user):
    """
    Unrevokes the given token. Raises a TokenNotFound error if the token does
    not exist in the database
    """
    token = TokenBlacklist.query.filter_by(id=token_id,
        user_identity=user).first()
    if not token:
        raise TokenNotFound("Could not find the token {}".format(token_id))
    token.revoked = False
    db.session.commit()


@jwt.token_in_blacklist_loader
def check_if_token_revoked(decoded_token):
    return is_token_revoked(decoded_token)


def abort(code, json=False, *args, **kwargs):
    response = {
            'success': 0,
            'error': {}}
    response['error'] = kwargs
    return jsonify(response) if json else response, code


paging_parser = reqparse.RequestParser()
paging_parser.add_argument('page', type=integer(allow_negative=False))
paging_parser.add_argument('page_size', type=integer(allow_negative=False))


def query_with_paging(query):
    paging_args = paging_parser.parse_args()
    if paging_args.page_size:
        query = query.limit(paging_args.page_size)
        if paging_args.page:
            query = query.offset(paging_args.page * paging_args.page_size)
    return query
