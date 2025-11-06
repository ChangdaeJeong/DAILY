from flask import Blueprint, render_template
from .auth import auth_bp
from .project import project_bp
from .setting import setting_bp
from .report import report_bp
from .message import message_bp

main_bp = Blueprint('main', __name__)

# 다른 Blueprint들을 main_bp에 등록
main_bp.register_blueprint(auth_bp, url_prefix='/auth')
main_bp.register_blueprint(project_bp, url_prefix='/project')
main_bp.register_blueprint(report_bp, url_prefix='/report')
main_bp.register_blueprint(setting_bp, url_prefix='/setting')
main_bp.register_blueprint(message_bp, url_prefix='/message')

@main_bp.route('/')
def index():
    return render_template('main/index.html')
