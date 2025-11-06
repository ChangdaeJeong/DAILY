from flask import request
from functools import wraps

def non_static_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.endpoint and request.endpoint == 'static':
            return
        return f(*args, **kwargs)
    return decorated_function

def require_debug_mode(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import current_app
        if not current_app.config.get('DEBUG', False):
            return "This feature is only available in DEBUG mode.", 403
        return f(*args, **kwargs)
    return decorated_function