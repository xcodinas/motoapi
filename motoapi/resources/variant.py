from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required
from flask import request
from motoapi import db
from motoapi.models import Variation, LikedVariant, DislikedVariant
from motoapi.utils import current_user, query_with_paging, str2bool, abort
from motoapi.fields import variant_fields, integer
from motoapi.utils import current_user
from sqlalchemy.sql.expression import func, select
import re


variant_parser = reqparse.RequestParser()
variant_parser.add_argument('variant', type=integer())

tinder_parser = reqparse.RequestParser()
tinder_parser.add_argument('variant', type=integer(), required=True)
tinder_parser.add_argument('liked', type=str2bool)
tinder_parser.add_argument('disliked', type=str2bool)


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

def get_average_preferences(ids_liked):
    handler = AttributeHandler(None, None)
    fill_handler(handler, variations=Variation.query.filter(
        Variation.id.in_(ids_liked)).all())
    return handler.get_average_bikes()

def tinder_recommendation():
    ids_liked = set()
    for like in LikedVariant.query.filter_by(user_id=current_user().id):
        ids_liked.add(like.variant_id)
    id_disliked = set()
    for like in DislikedVariant.query.filter_by(user_id=current_user().id):
        id_disliked.add(like.variant_id)
    
    LIMIT = 5
    if not ids_liked:
        variations = Variation.query.order_by(func.random()).limit(5)
        return [variant_fields(v) for v in variations]
    preferences = get_average_preferences(ids_liked)
    response = recommendation_response(preferences)
    filtered_response = []
    for item in response:
        id = item['id']
        if not (id in ids_liked) and not (id in id_disliked):
            filtered_response.append(item)
    
    return filtered_response[:LIMIT]




recommendation_parser = reqparse.RequestParser()
recommendation_parser.add_argument('year', type=integer())
recommendation_parser.add_argument('model_year', type=integer())
recommendation_parser.add_argument('displacement', type=integer())
recommendation_parser.add_argument('top_speed', type=integer())
recommendation_parser.add_argument('power', type=integer())
recommendation_parser.add_argument('fuel_capacity', type=integer())
recommendation_parser.add_argument('weight', type=integer())
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
        if attr == 'weight_incl._oil,_gas,_etc':
            attr = 'weight'
        if attr in ['year', 'model_year']:
            return attr, value
        if 'displacement' == attr:
            return attr, float(value.split()[0])
        if 'valves_per_cylinder' == attr:
            return attr, int(value)
        if attr in ['top_speed', 'fuel_capacity', 'weight']:
            return attr, float(value.split()[0])
        if 'power' == attr:
            if 'kW' not in value:
                return attr, float(value.split()[0])
            value = float(re.search('(\d+\.\d+)\s*kW', value).group(1))
            return attr, value
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
                return attr, value
            except:
                return attr, CAT_IN.index(value)
        raise ValueError('Empty')

    def get_average_bikes(self):
        response = {}
        for attr in self.min_attributes:
            avg = 0
            for bike in self.bikes.values():
                avg += bike[attr]
            avg /= len(self.bikes)
            response[attr] = avg
        return response

    def add_attribute(self, id, attribute, value):
        attribute, value = self._parse_attribute(attribute, value)
        if self.list_attributes is not None and attribute not in self.list_attributes:
            return
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

    def get_recommendations(self):
        distance_d = []
        min_distance = 99999999
        max_distance = 0
        for i, (bike_id, bike) in enumerate(self.bikes.items()):
            distance = 0
            for attr in self.list_attributes:
                mx = self.max_attributes[attr]
                mn = self.min_attributes[attr]

                def clap(value):
                    num = (value - mn)
                    div = (mx - mn)
                    if div != 0:
                        num /= div
                    return num
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
        return distance_d


def fill_handler(handler, variations=None):
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
    if variations is None:
        variations = Variation.query.all()
    for variation in variations:
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

def recommendation_response(preference):
    handler = AttributeHandler(preference.keys(), preference)
    fill_handler(handler)
    LIMIT = 50
    recommendations = handler.get_recommendations()[:LIMIT]
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

class Recommendation(Resource):

    # decorators = [jwt_required]

    def get(self):
        args = recommendation_parser.parse_args()
        return recommendation_response({k: float(v) for k, v in request.args.items()})

class TinderSwinger(Resource):

    decorators = [jwt_required]

    def get(self):
        return tinder_recommendation()

    def post(self):
        args = tinder_parser.parse_args()
        variant = Variation.query.filter_by(id=args.variant).first()
        if not variant:
            return abort(400, message="Variant not found")
        if args.liked:
            db.session.add(LikedVariant(
                variant=variant, user=current_user()))
        elif args.disliked:
            db.session.add(DislikedVariant(
                variant=variant, user=current_user()))
        db.session.commit()
        return tinder_recommendation()
