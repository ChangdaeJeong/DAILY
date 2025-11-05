from flask import render_template, redirect, url_for, request, session, jsonify, g
from . import main_bp
from flask import current_app
import mysql_db
from .auth import auth_bp
from .project import project_bp # categorized_projects_data 임포트 제거
from .report import report_bp
# from lib.decorator import non_static_request # lib.decorator에서 non_static_request import 제거

# 다른 Blueprint들을 main_bp에 등록
main_bp.register_blueprint(auth_bp, url_prefix='/auth')
main_bp.register_blueprint(project_bp, url_prefix='/project')
main_bp.register_blueprint(report_bp, url_prefix='/report')

@main_bp.route('/')
def index():
    return render_template('main/index.html')
