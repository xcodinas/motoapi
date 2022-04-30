from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required
from flask import request
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

recommendation_parser = reqparse.RequestParser()
recommendation_parser.add_argument('year', type=integer())
recommendation_parser.add_argument('model_year', type=integer())
recommendation_parser.add_argument('displacement', type=integer())
recommendation_parser.add_argument('top_speed', type=integer())
recommendation_parser.add_argument('power', type=integer())
recommendation_parser.add_argument('fuel_capacity', type=integer())
recommendation_parser.add_argument('weight_incl._oil,_gas,_etc', type=integer())
recommendation_parser.add_argument('valves_per_cylinder', type=integer())
recommendation_parser.add_argument('category', type=integer())


class AttributeHandler:
    def __init__(self, list_attributes, preference):
        self.list_attributes = list_attributes
        self.min_attributes = {}
        self.max_attributes = {}
        self.preference = preference
        self.bikes = {}

    def _parse_attribute(self, attr, value):
        if attr in ['year', 'model_year']:
            return value
        if 'displacement' == attr:
            return int(value.split()[0])
        if 'valves_per_cylinder' == attr:
            return int(value)
        if attr in ['top_speed', 'fuel_capacity',
                    'weight_incl._oil,_gas,_etc']:
            return float(value.split()[0])
        if 'power' == attr:
            if 'kW' not in value:
                return float(value.split()[0])
            return float(value.split()[-1][1:])
        if 'category' == attr:
            CAT_IN = [
                "Unspecified category",
                "Allround",
                "Super motard",
                "Minibike, cross",
                "Cross / motocross",
                "Enduro / offroad",
                "Trial",
                "Touring",
                "Classic",
                "Custom / cruiser",
                "Scooter",
                "Naked bike",
                "Sport",
                "Sport touring",
                "Speedway",
                "Prototype / concept model"
            ]
            try:
                value = int(value)
                assert 0 <= value
                assert value < len(CAT_IN)
                return value
            except:
                return CAT_IN.index(value)
        raise ValueError('Empty')

    def add_attribute(self, id, attribute, value):
        if attribute not in self.list_attributes:
            return
        value = self._parse_attribute(attribute, value)
        if attribute not in self.min_attributes:
            self.min_attributes[attribute] = value
            self.max_attributes[attribute] = value
        else:
            self.min_attributes[attribute] = min(
                self.max_attributes[attribute], value)
            self.max_attributes[attribute] = max(
                self.max_attributes[attribute], value)
        if id not in self.bikes:
            self.bikes[id] = {}
        self.bikes[id][attribute] = value

    @staticmethod
    def check_all_attributes(obj, attributes):
        for attr in attributes:
            if getattr(obj, attr) is None:
                return False
        return True

    @staticmethod
    def check_all_index(obj, attributes):
        for attr in attributes:
            if attr not in obj or obj[attr] is None:
                return False
        return True

    def get_recommendations(self, limit=50):
        distance_d = []
        min_distance = 99999999
        max_distance = 0
        for i, (bike_id, bike) in enumerate(self.bikes.items()):
            distance = 0
            for attr in self.list_attributes:
                mx = self.max_attributes[attr]
                mn = self.min_attributes[attr]

                def clap(value):
                    return (value - mn) / (mx - mn)
                clap_bike = clap(bike[attr])
                clap_preference = clap(self.preference[attr])
                difference = abs(clap_bike - clap_preference)
                distance += difference
            min_distance = min(min_distance, distance)
            max_distance = max(max_distance, distance)
            distance_d.append((bike_id, distance))

        for i in range(len(distance_d)):
            bike_id, distance = distance_d[i]
            distance = ((distance - min_distance) / (
                max_distance - min_distance)) * 100
            distance_d[i] = bike_id, distance

        distance_d.sort(key=lambda x: x[1], reverse=True)
        return distance_d[limit:]


class Recommendation(Resource):

    # decorators = [jwt_required]

    def get(self):
        args = recommendation_parser.parse_args()
        attrs = ['year', 'model_year']
        extra_attr = [
            'displacement',
            'top_speed',
            'power',
            'fuel_capacity',
            'weight_incl._oil,_gas,_etc',
            'valves_per_cylinder',
            'category'
        ]
        
        preference = {k: float(v) for k, v in request.args.items()}
        handler = AttributeHandler(request.args.keys(), preference)
        for variation in Variation.query.all():
            if not AttributeHandler.check_all_attributes(variation, attrs):
                continue
            if (variation.extra_data is None
                    or not AttributeHandler.check_all_index(
                        variation.extra_data, extra_attr)):
                continue
            for attr in attrs:
                handler.add_attribute(
                    variation.id, attr, getattr(variation, attr))
            for attr in extra_attr:
                handler.add_attribute(
                    variation.id, attr, variation.extra_data[attr])
        recommendations = handler.get_recommendations()
        ids = list(map(lambda x: x[0], recommendations))
        recommendations = {k: v for k, v in recommendations}
        recommendations_obj = Variation.query.filter(
            Variation.id.in_(ids)).all()

        response = []
        for obj in recommendations_obj:
            fields = variant_fields(obj)
            fields['matching'] = recommendations[obj.id]
            response.append(fields)

        return response
