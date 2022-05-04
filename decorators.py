"""Decorators used in the Flask app, exception made from those related to authentication which are defined in the auth0 module.

    .. moduleAuthor:: Nicolas Gach <nicolas@e-nitium.com>

"""
from exceptions import LogicError
from flask import request, Flask
from functools import wraps

#app = Flask(__name__)

def requires_post_params(paramList):
    """Decorator method verifying if a given list of parameters is included in a POST request form-data body.

    :param paramList: The list of parameters name to be looked for.
    :type paramList: String[]
    :raises LogicError: 400 exception, Bad request, key input not supplied - if an expected param in paramList is missing from the POST request form-data body

    |
    
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if(request.data):
                if not all(key in request.form for key in paramList):
                    raise LogicError({"code": "Request Error caught in decorator", "description": "Bad request, key input not supplied"}, 400)
            return f(*args, **kwargs)
        return decorated
    return decorator