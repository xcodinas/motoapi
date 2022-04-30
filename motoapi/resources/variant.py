from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required
from motoapi.models import Variation
from motoapi.utils import query_with_paging, abort
from motoapi.fields import variant_fields, integer


variant_parser = reqparse.RequestParser()
variant_parser.add_argument('variant', type=integer())


class VariantResource(Resource):

    def get(self):
        args = variant_parser.parse_args()
        if args.variant:
            variant = Variation.query.filter_by(id=args.variant).first()
            if not variant:
                return abort(400, message='Variant not found')
            return variant_fields(variant)
        return [variant_fields(v) for v in query_with_paging(
            Variation.query.filter_by(fetch_state='success'))]
