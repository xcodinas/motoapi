from flask_restful import Resource

from flask_jwt_extended import jwt_required
from motoapi.utils import current_user
from motoapi.fields import user_fields


class UserResource(Resource):

    def get(self):
        return []


class MeResource(Resource):

    decorators = [jwt_required]

    def get(self):
        user = current_user()
        return user_fields(current_user())
