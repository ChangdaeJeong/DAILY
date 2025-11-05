from flask import render_template, redirect, url_for, request, session, jsonify
from . import main_bp
from flask import current_app
import mysql_db
from .auth import auth_bp
from .project import project_bp
from .report import report_bp

# 다른 Blueprint들을 main_bp에 등록
main_bp.register_blueprint(auth_bp, url_prefix='/auth')
main_bp.register_blueprint(project_bp, url_prefix='/project')
main_bp.register_blueprint(report_bp, url_prefix='/report')

@main_bp.before_app_request
def check_login_status():
    # 로그인 라우트와 정적 파일은 로그인 체크를 건너뜁니다.
    # 'main.auth.'로 시작하는 엔드포인트는 auth_bp의 라우트입니다.
    if request.endpoint and (request.endpoint.startswith('main.auth.') or request.endpoint == 'static'):
        return

    # 로그인되지 않은 상태에서 GET 요청 시 로그인 페이지로 리다이렉트
    if not session.get('user_uid') and request.method == 'GET':
        return redirect(url_for('main.auth.login'))
    
    # 로그인되지 않은 상태에서 POST 요청 시 JSON 에러 반환
    if not session.get('user_uid') and request.method == 'POST':
        return jsonify(success=False, msg='로그인되지 않았습니다.'), 401

@main_bp.route('/')
def index():
    conn = mysql_db.get_conn()
    if conn:
        mysql_db.close_conn(conn)
    
    return render_template('main/index.html')

@main_bp.route('/loading')
def loading():
    return render_template('main/loading.html')
