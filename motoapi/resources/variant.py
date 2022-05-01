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
        variations = Variation.query.filter_by(fetch_state="success").order_by(func.random()).limit(150)
        response = [variant_fields(v) for v in variations]
        # print('bbb')
    else:
        preferences = get_average_preferences(ids_liked)
        # print('ccc', len(preferences))
        response = recommendation_response(preferences, limit=None)
    filtered_response = []
    for item in response:
        id = item['id']
        if (id in ids_liked) or (id in id_disliked):
            continue
        filtered_response.append(item)
    # print('aaaa', len(filtered_response))
    # print(filtered_response, response)
    filtered_response = filtered_response[:LIMIT]
    # print(list(map(lambda x: x['id'], filtered_response)), ids_liked, id_disliked)
    return filtered_response




recommendation_parser = reqparse.RequestParser()
# recommendation_parser.add_argument('year', type=integer())
recommendation_parser.add_argument('model_year', type=integer())
recommendation_parser.add_argument('displacement', type=integer())
recommendation_parser.add_argument('top_speed', type=integer())
recommendation_parser.add_argument('power', type=integer())
recommendation_parser.add_argument('fuel_capacity', type=integer())
recommendation_parser.add_argument('weight', type=integer())
recommendation_parser.add_argument('valves_per_cylinder', type=integer())
recommendation_parser.add_argument('category', type=integer())


class AttributeHandler:
    CATEGORIES = [
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
            CAT_IN = AttributeHandler.CATEGORIES
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
            div = (max_distance - min_distance)
            if div == 0: div = 1
            distance = ((distance - min_distance) / div) * 100
            distance_d[i] = bike_id, distance

        distance_d.sort(key=lambda x: x[1], reverse=True)
        return distance_d


def fill_handler(handler, variations=None):
    attrs = ['model_year']
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
        variations = Variation.query.filter_by(fetch_state='success')
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

def recommendation_response(preference, limit=50):
    handler = AttributeHandler(preference.keys(), preference)
    fill_handler(handler)
    recommendations = handler.get_recommendations()
    if limit is not None:
        recommendations = recommendations[:limit]
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

class DashBoard(Resource):

    # decorators = [jwt_required]

    def get(self):
        from sqlalchemy import func
        most_liked = LikedVariant.query.with_entities(LikedVariant.variant_id, func.count(LikedVariant.variant_id)).group_by(LikedVariant.variant_id).all()
        most_liked.sort(key=lambda x: x[1])
        most_liked, most_likes = most_liked[0]
        most_liked = Variation.query.filter_by(id=most_liked).first()
        most_liked = variant_fields(most_liked)
        most_liked['likes'] = most_likes

        most_disliked = DislikedVariant.query.with_entities(DislikedVariant.variant_id, func.count(DislikedVariant.variant_id)).group_by(DislikedVariant.variant_id).all()
        most_disliked.sort(key=lambda x: x[1])
        most_disliked, most_dislikes = most_disliked[0]
        most_disliked = Variation.query.filter_by(id=most_disliked).first()
        most_disliked = variant_fields(most_disliked)
        most_disliked['dislikes'] = most_dislikes

        def fill(d, ClsV):
            for cat in AttributeHandler.CATEGORIES:
                d[cat] = 0
                st = db.session().query(
                    Variation, 
                    ClsV, 
                ).filter(
                    Variation.id == ClsV.variant_id
                ).all()
                for variation, liked_variation in st:
                    if variation.extra_data is not None and 'category' in variation.extra_data:
                        if variation.extra_data['category'] == cat:
                            d[cat] += 1

        like_cat = {}
        fill(like_cat, LikedVariant)
        dislike_cat = {}
        fill(dislike_cat, DislikedVariant)
        
        response = {
            'num_likes': len(LikedVariant.query.all()),
            'num_dislikes': len(DislikedVariant.query.all()),
            'most_liked': most_liked,
            'most_disliked': most_disliked,
            'like_categories': like_cat,
            'dislike_categories': dislike_cat
        }
        return response
