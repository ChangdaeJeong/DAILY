from flask import Blueprint

main_bp = Blueprint('main', __name__)

from . import main_router
# 다른 Blueprint들은 main_router에서 등록됩니다.
