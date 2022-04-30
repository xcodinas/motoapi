import datetime

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import ignore_logger
from werkzeug.exceptions import HTTPException, BadRequest, MethodNotAllowed
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_babelex import Babel
from flask_babelex import format_datetime as babel_datetime
from flask_mail import Mail
from flask_restful import Api as _Api
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import Config

ignore_logger('engineio.server')

sentry_sdk.init(
    dsn=Config.SENTRY_CDN,
    integrations=[FlaskIntegration()],
    ignore_errors=(BadRequest, MethodNotAllowed),
)


motoapi = Flask(__name__)
motoapi.config.from_object(Config)
motoapi.secret_key = b'fefefy2L"F4Q8z\n\xec]/'
motoapi.jinja_env.globals.update(getattr=getattr)


class Api(_Api):
    def error_router(self, original_handler, e):
        if self._has_fr_route() and isinstance(e, HTTPException):
            try:
                return self.handle_error(e)
            except Exception:
                pass
        return original_handler(e)

# Flask Sqlalchemy
db = SQLAlchemy(motoapi)
# Flask Migrate
migrate = Migrate(motoapi, db)
# Flask Babel
babel = Babel(motoapi)
# Falsk Mail
mail = Mail(motoapi)
# Flask CORS
cors = CORS(motoapi, resources={r"/*": {"origins": "*"}})
# Token
jwt = JWTManager(motoapi)


# Flask Restful
api = Api(motoapi)
from motoapi.resources.user import (
    UserResource,
    MeResource,
    )
from motoapi.resources.variant import (
    Recommendation,
    VariantResource,
    TinderSwinger,
    )

# User
api.add_resource(UserResource, '/api/user')
api.add_resource(MeResource, '/api/user/me')

# Variant
api.add_resource(VariantResource, '/api/variant')
api.add_resource(Recommendation, '/api/variant/recommendation')
api.add_resource(TinderSwinger, '/api/variant/swinger')

from motoapi import models, routes, exceptions, utils
assert utils
assert models
assert exceptions

# Blueprints
motoapi.register_blueprint(routes.api_blueprint, url_prefix='/api')


@motoapi.template_filter('formatdatetime')
def format_datetime(value, format="yyyy-MM-dd H:mm"):
    """Format a date time to (Default): d Mon YYYY HH:MM P"""
    if value is None:
        return ""
    # Temporal fix of docker wrong time
    value = value + datetime.timedelta(hours=2)
    return babel_datetime(value, format)


def date_today(type=None):
    if type and type == 'datetime':
        return datetime.datetime.now()
    return datetime.date.today()


motoapi.jinja_env.globals.update(date_today=date_today)
motoapi.jinja_env.globals.update(len=len)
