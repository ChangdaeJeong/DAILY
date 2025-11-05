from flask import request, session, redirect, url_for, jsonify, g, current_app
import mysql_db # mysql_db 임포트
from router.project import categorized_projects_data
from lib.decorator import non_static_request

@non_static_request
def check_login_status():
    # 'main.auth.'로 시작하는 엔드포인트는 auth_bp의 라우트입니다.
    if request.endpoint and request.endpoint.startswith('main.auth.'):
        return

    # 로그인되지 않은 상태에서 GET 요청 시 로그인 페이지로 리다이렉트
    if not session.get('user_uid') and request.method == 'GET':
        return redirect(url_for('main.auth.login'))
    
    # 로그인되지 않은 상태에서 POST 요청 시 JSON 에러 반환
    if not session.get('user_uid') and request.method == 'POST':
        return jsonify(success=False, msg='로그인되지 않았습니다.'), 401

@non_static_request
def inject_sidebar_data():
    sidebar_projects_data = {}
    if(session.get('user_uid')):
        logged_in_user_id = session.get('user', {}).get('user', {}).get('id')
        sidebar_projects_data = categorized_projects_data(logged_in_user_id)

    return dict(sidebar_projects_data=sidebar_projects_data)

def inject_user():
    user_data = {
        'username': session['user_uid'] if 'user_uid' in session else '',
        'user': {},
        'logged_in': False
    }
    if user_data['username']:
        conn = None
        cursor = None
        try:
            conn = mysql_db.get_conn()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM daily_db_users WHERE uid = %s and active = %s", (user_data['username'], True))
            user_record = cursor.fetchone()
            if user_record:
                user_data['user'] = user_record # 최신 레코드 전체를 반환
                user_data['logged_in'] = True
            else:
                # 세션에 user_uid가 있지만 DB에서 찾을 수 없는 경우 (예: DB에서 삭제됨)
                session.pop('user_uid', None) # 세션에서 제거
        except Exception as e:
            current_app.logger.error(f"Error fetching user data for context processor: {e}", exc_info=True)
        finally:
            if cursor:
                cursor.close()
            if conn:
                mysql_db.close_conn(conn)
    session['user'] = user_data
    return dict(user=user_data)
