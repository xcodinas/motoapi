import os
import datetime

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.environ.get('MOTOAPI_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BABEL_DEFAULT_LOCALE = 'es'
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_SSL = False
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    SENTRY_CDN = os.environ.get('SENTRY_CDN') or None

    TEST_ENV = os.environ.get('TEST_ENV') or False

    SECURITY_US_ENABLED_METHODS = ('email', 'username')
    SECURITY_PASSWORD_HASH = 'sha512_crypt'
    SECURITY_PASSWORD_SALT = '918fjfjwaofjwoi29'

    PASSWORD_HASH = os.environ.get('PASSWORD_HASH') or 'sha512_crypt'
    PASSWORD_SALT = os.environ.get('PASSWORD_SALT') or SECURITY_PASSWORD_SALT
