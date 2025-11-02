from flask import Blueprint

main_bp = Blueprint('main', __name__)

from . import main_router
from .request import request_bp
from .report import report_bp
