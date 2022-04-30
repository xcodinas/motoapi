from flask_restful import Resource
from flask_jwt_extended import jwt_required
from motoapi.models import Variation
from motoapi.utils import query_with_paging
from motoapi.fields import variant_fields


class VariantResource(Resource):

    decorators = [jwt_required]

    def get(self):
        return [variant_fields(v) for v in query_with_paging(
            Variation.query)]
