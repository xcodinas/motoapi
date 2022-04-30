from functools import wraps


def datetime_to_string(date):
    return date.strftime("%a, %d %b %Y %H:%M:%S -0000")


def string(max_length=None, min_length=None, empty=True, email=False,
        lower=False, strip=False):
    def validate(s):
        if max_length and len(s) > max_length:
            raise ValueError(
                "The string length is too long, its limit is %s" % max_length)
        if min_length and len(s) < min_length:
            raise ValueError(
                "The string length is too short, it must be at least %s " %
                min_length)
        if not empty and not s:
            raise ValueError("Must not be empty string")
        if email and '@gmail.com' in s:
            s = s[:-10].replace('.', '') + '@gmail.com'
        if lower:
            s = s.lower()
        if strip:
            s = ''.join(s.strip().split())
        return s
    return validate


def integer(allow_negative=True):
    def validate(i):
        try:
            i = int(i)
        except ValueError:
            raise ValueError("Parameter should be an integer")
        if not allow_negative and i < 0:
            raise ValueError("Negative numbers are not allowed")
        return i
    return validate


def record_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not args[0]:
            return {}
        return func(*args, **kwargs)
    return wrapper


@record_required
def user_fields(user):
    response = {
        'id': user.id,
        'username': user.username,
        'name': user.name,
        }
    return response


@record_required
def variant_fields(variant):
    response = {
        'id': variant.id,
        'name': variant.name,
        'model_year': variant.model_year,
        'cubic': variant.cubic,
        'engine': variant.engine,
        'fuel': variant.fuel,
        'image': variant.image,
        'max_speed': variant.max_speed,
        'power': variant.power,
        'weight': variant.weight,
        'price': variant.price,
        'refiregeration': variant.refiregeration,
        'valves': variant.valves,
        'fetch_state': variant.fetch_state,
        'fetch_date': datetime_to_string(
            variant.fetch_date) if variant.fetch_date else '',
    }
    return response
