from functools import wraps
from flask import request, Flask
from exceptions import LogicError
import inspect

app = Flask(__name__)

def requires_post_params(paramList):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if(request.data):
                if not all(key in request.form for key in paramList):
                    raise LogicError({"code": "Request Error caught in decorator", "description": "Bad request, key input not supplied"}, 400)
            return f(*args, **kwargs)
        return decorated
    return decorator

def requires_w3_access(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated