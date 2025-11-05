from flask import request
from functools import wraps

def non_static_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.endpoint and request.endpoint == 'static':
            return
        return f(*args, **kwargs)
    return decorated_function
