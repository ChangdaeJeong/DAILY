from flask import Flask, render_template, flash, redirect, url_for, session
import mysql_db
from router import main_bp
from flask_bcrypt import Bcrypt # Flask-Bcrypt 임포트

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # Flash 메시지를 위해 secret_key 설정
app.bcrypt = Bcrypt(app) # Bcrypt 초기화 및 app 인스턴스에 직접 할당

@app.before_first_request
def initialize_db_pool():
    mysql_db.create_db_pool()

app.register_blueprint(main_bp)

@app.context_processor
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
            print(f"Error fetching user data for context processor: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                mysql_db.close_conn(conn)
    session['user'] = user_data
    return dict(user=user_data)

@app.context_processor
def inject_projects():
    projects = []
    user_uid = session.get('user_uid')
    if user_uid:
        conn = None
        cursor = None
        user_data = session.get('user', {})
        logged_in_user_id = user_data.get('user', {}).get('id')
        try:
            conn = mysql_db.get_conn()
            cursor = conn.cursor(dictionary=True)
            # user_id가 같은 최신 project 10개를 id desc 순으로 가져옵니다.
            cursor.execute("SELECT id, name, state FROM daily_db_projects WHERE user_id = %s ORDER BY id DESC LIMIT 10", (logged_in_user_id,))
            projects = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching projects for context processor: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                mysql_db.close_conn(conn)
    return dict(projects=projects)

if __name__ == '__main__':
    app.run(debug=True)
