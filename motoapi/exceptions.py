from flask import jsonify
from werkzeug.exceptions import MethodNotAllowed, NotFound

from motoapi import motoapi


@motoapi.errorhandler(MethodNotAllowed)
def handle_method_not_allowed_error(err):
    response = {
            'success': 0,
            'error': {
                'message': 'Method not allowed',
                'error_code': 103,
            }}
    return jsonify(response), 401


@motoapi.errorhandler(NotFound)
def handle_not_found(err):
    response = {
            'success': 0,
            'error': {
                'message': 'Resource not found',
                'error_code': 104,
            }}
    return jsonify(response), 404


@motoapi.errorhandler(Exception)
def server_error_handler(error):
    raise error
    message = {
            'success': 0,
            'error': {
                'message': 'Internal server error',
                'error_code': 999,
            },
            }
    if motoapi.debug:
        message = {
                'success': 0,
                'error': {'message': error.args[0] if error.args else ''},
                }
    return jsonify(message), e00


@motoapi.errorhandler(400)
def client_error_handler(error):
    response = {
            'success': 0,
            'error': {},
            }
    if hasattr(error, 'data'):
        for data in error.data:
            if data == 'message' and len(error.data.keys()) == 1:
                text = [elem for elem in error.data[data].values()][0]
                if ('cannot be blank!' in text or
                        'Missing required parameter' in text):
                    response['error']['error_code'] = 106
            response['error'][data] = error.data[data]
    else:
        response['error'] = error.get_description()
    return jsonify(response), 400


class TokenNotFound(Exception):
    """
    Indicates that a token could not be found in the database
    """
    pass


class NotAuthorizedError(Exception):
    """
    Indicates that the user does not have the right permissions to access
    """

    def __init__(self, message='You dont have permissions to access.'):
        super().__init__(message)
    pass
