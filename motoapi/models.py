import requests
import hmac
import base64
import hashlib
from bs4 import BeautifulSoup
from passlib.hash import pbkdf2_sha512 as sha512
import datetime
import random
import string
from sqlalchemy.sql import func
from flask_sqlalchemy import BaseQuery
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.ext.declarative import declared_attr


from motoapi import db
from config import Config


def encode_string(_string):
    if isinstance(_string, str):
        _string = _string.encode("utf-8")
    return _string


def get_hmac(password):
    salt = Config.PASSWORD_SALT
    if salt is None:
        raise RuntimeError(
            "The configuration value `PASSWORD_SALT` must "
            "not be None "
        )
    h = hmac.new(encode_string(salt), encode_string(password), hashlib.sha512)
    return base64.b64encode(h.digest())


def get_random_string(length):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))


class QueryWithSoftDelete(BaseQuery):
    _with_deleted = False

    def __new__(cls, *args, **kwargs):
        obj = super(QueryWithSoftDelete, cls).__new__(cls)
        obj._with_deleted = kwargs.pop('_with_deleted', False)
        if len(args) > 0:
            super(QueryWithSoftDelete, obj).__init__(*args, **kwargs)
            return obj.filter_by(
                deleted_at=None) if not obj._with_deleted else obj
        return obj

    def __init__(self, *args, **kwargs):
        pass

    def with_deleted(self):
        return self.__class__(db.class_mapper(self._mapper_zero().class_),
            session=db.session(), _with_deleted=True)

    def _get(self, *args, **kwargs):
        # this calls the original query.get function from the base class
        return super(QueryWithSoftDelete, self).get(*args, **kwargs)

    def get(self, *args, **kwargs):
        # the query.get method does not like it if there is a filter clause
        # pre-loaded, so we need to implement it using a workaround
        obj = self.with_deleted()._get(*args, **kwargs)
        return (obj if obj is None or
            self._with_deleted or not obj.deleted else None)


class TimestampsMixin(object):
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=datetime.datetime.utcnow,
    )
    created_at = db.Column(db.DateTime,
        nullable=False, server_default=func.now())
    deleted_at = db.Column(db.DateTime)


class Brand(db.Model, TimestampsMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    variations = db.relationship('Variation', backref='brand', lazy=True)


class Variation(db.Model, TimestampsMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    year = db.Column(db.Integer)
    model_year = db.Column(db.Integer)
    cubic = db.Column(db.String)
    engine = db.Column(db.String)
    fuel = db.Column(db.String)
    image = db.Column(db.String)
    max_speed = db.Column(db.String)
    power = db.Column(db.String)
    weight = db.Column(db.String)
    price = db.Column(db.Float)
    refiregeration = db.Column(db.String)
    valves = db.Column(db.String)

    fetch_state = db.Column(db.String)
    fetch_date = db.Column(db.DateTime)

    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'),
        nullable=False)

    def get_url(self):
        return ('https://fichasmotor.com/%s/%s-%s-%s' % (
            self.brand.name,
            self.brand.name,
            "-".join(self.name.split(' ')),
            self.model_year)).lower()

    def update_data(self):
        page = requests.get(self.get_url())
        soup = BeautifulSoup(page.content, 'html.parser')
        try:
            self.image = soup.find("div", {"class": "p10"}).find('img')['src']
            data = soup.findAll("div", {
                "class": "table-responsive"})[1].findAll('td')
            self.cubic = data[1].get_text()
            self.engine = data[3].get_text()
            self.power = data[5].get_text()
            self.valves = data[11].get_text()
            if len(data) >= 15:
                self.refrigeration = data[15].get_text()
                self.transmition = data[17].get_text()
            self.weight = soup.findAll("div", {
                "class": "table-responsive"})[2].findAll('td')[1].get_text()
            self.max_speed = soup.findAll("div", {
                "class": "table-responsive"})[3].findAll('td')[1].get_text()
            self.fetch_date = datetime.datetime.now()
            self.fetch_state = "success"
        except (AttributeError, IndexError) as e:
            self.fetch_state = "error"


class TokenBlacklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String, nullable=False)
    token_type = db.Column(db.String, nullable=False)
    user_identity = db.Column(db.String, nullable=False)
    revoked = db.Column(db.Boolean, nullable=False)
    expires = db.Column(db.DateTime, nullable=False)

    def to_dict(self):
        return {
            'token_id': self.id,
            'jti': self.jti,
            'token_type': self.token_type,
            'user_identity': self.user_identity,
            'revoked': self.revoked,
            'expires': self.expires
        }

roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer, db.ForeignKey('user.id')),
    db.Column("role_id", db.Integer, db.ForeignKey('role.id')),
)


class User(db.Model, TimestampsMixin):
    query_class = QueryWithSoftDelete

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean(), nullable=False, default=True)

    name = db.Column(db.String)
    phone_number = db.Column(db.String(128), nullable=True)
    gender = db.Column(db.String)
    language = db.Column(db.String, default='es')

    # confirmable
    confirmed_at = db.Column(db.DateTime)

    # recovery code
    recovery_code = db.Column(db.String)
    recovery_code_expiration = db.Column(db.DateTime)

    @declared_attr
    def roles(cls):
        # The first arg is a class name, the backref is a column name
        return db.relationship(
            "Role",
            secondary=roles_users,
            backref=db.backref("users", lazy="dynamic"),
        )

    @staticmethod
    def generate_hash(password):
        password = get_hmac(password)
        return sha512.hash(password)

    @staticmethod
    def verify_hash(password, hash):
        password = get_hmac(password)
        return sha512.verify(password, hash)

    def __repr__(self):
        return '<User {}>'.format(self.id)


class Role(db.Model, TimestampsMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    # A comma separated list of strings
    permissions = db.Column(db.UnicodeText, nullable=True)
    update_datetime = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=datetime.datetime.utcnow,
    )
