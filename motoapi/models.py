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
from re import sub


from motoapi import db
from config import Config


def encode_string(_string):
    if isinstance(_string, str):
        _string = _string.encode("utf-8")
    return _string


def snake_case(s):
    return '_'.join(
        sub('([A-Z][a-z]+)', r' \1',
        sub('([A-Z]+)', r' \1',
        s.replace('-', ' '))).split()).lower()


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
    image = db.Column(db.String)
    price = db.Column(db.Float)
    extra_data = db.Column(db.JSON)

    fetch_state = db.Column(db.String)
    fetch_date = db.Column(db.DateTime)

    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'),
        nullable=False)

    liked_by = db.relationship('LikedVariant',
        foreign_keys='LikedVariant.variant_id',
        backref='variant', lazy='dynamic')
    disliked_by = db.relationship('DislikedVariant',
        foreign_keys='DislikedVariant.variant_id',
        backref='variant', lazy='dynamic')

    def get_url(self, year=None, use_year=False):
        if year:
            return ('https://bikez.com/motorcycles/%s_%s_%s.php' % (
                self.brand.name,
                "_".join(self.name.split(' ')).lower(),
                str(year),
            )).lower()
        elif use_year:
            return ('https://bikez.com/motorcycles/%s_%s_%s.php' % (
                self.brand.name,
                "_".join(self.name.split(' ')).lower(),
                self.year,
            )).lower()
        return ('https://bikez.com/models/%s_%s.php' % (
            self.brand.name,
            "_".join(self.name.split(' ')))).lower()

    def update_data(self):
        try:
            page = requests.get(self.get_url())
            soup = BeautifulSoup(page.content, 'html.parser')
            models = [
                i.find('img')['alt'] for i in soup.findAll('td')[-12].findAll(
                    'td')]
            years = [int(m.split(' ')[0]) if m.split(' ')[0].isnumeric()
                     else 0 for m in models]
            url = self.get_url(use_year=True)
            if years and self.model_year:
                closer_year = min(years, key=lambda x: abs(x - int(
                    self.model_year)))
                url = self.get_url(closer_year)
            moto_page = requests.get(url)
            moto_soup = BeautifulSoup(moto_page.content, 'html.parser')
            caracteristics = moto_soup.findAll("table", {
                "class": "Grid"})[0].findAll('td')
            self.extra_data = {}
            ignored_data = [
                'rating',
                'update_specs',
                'insurance_costs',
                'finance_options',
                'parts_finder',
                'maintenance',
                'ask_questions',
                'related_bikes'
            ]
            self.extra_data['rating'] = caracteristics[7].getText()[0:2]
            self.image = moto_soup.findAll("table")[1].find('a').find(
                'img')['src']
            for i, car in enumerate(caracteristics):
                key = snake_case(car.getText())
                if (i % 2 == 0 and (i + 1) < len(caracteristics)
                        and key not in ignored_data):
                    self.extra_data[key] = caracteristics[i + 1].getText()
            self.fetch_date = datetime.datetime.now()
            self.fetch_state = "success"
        except (Exception) as e:
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

    liked_variants = db.relationship('LikedVariant',
        foreign_keys='LikedVariant.user_id',
        backref='user', lazy='dynamic')

    disliked_variants = db.relationship('DislikedVariant',
        foreign_keys='DislikedVariant.user_id',
        backref='user', lazy='dynamic')

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


class LikedVariant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
        nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('variation.id'),
        nullable=False)


class DislikedVariant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
        nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('variation.id'),
        nullable=False)
