from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import mysql_db

auth_bp = Blueprint('auth', __name__)

def check_qb_id(uid, pwd):
    # 이 함수는 외부 시스템(QB) ID를 확인하는 용도로 가정합니다.
    # 여기서는 단순히 하드코딩된 값으로 True를 반환합니다.
    # 실제 구현에서는 외부 API 호출 등을 통해 ID/PWD를 검증해야 합니다.
    if uid == "test2" and pwd == "test":
        return True
    return False

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uid = request.form['uid']
        pwd = request.form['pwd']
        
        conn = None
        cursor = None
        try:
            conn = mysql_db.get_conn()
            cursor = conn.cursor(dictionary=True)

            # 일반 로그인 (bcrypt 암호화 비교)
            cursor.execute("SELECT * FROM daily_db_users WHERE uid = %s", (uid,))
            user = cursor.fetchone()
            print(current_app.bcrypt.generate_password_hash(pwd))
            if user and (check_qb_id(uid, pwd) or current_app.bcrypt.check_password_hash(user['pwd'], pwd)):
                session['user_uid'] = user['uid'] # 세션에 사용자 ID 저장
                #flash('로그인 성공!', 'success')
                return redirect(url_for('main.index')) # 메인 페이지로 리다이렉트
            else:
                flash('아이디 또는 비밀번호가 올바르지 않습니다.', 'danger')
        except Exception as e:
            flash(f'로그인 중 오류 발생: {e}', 'danger')
        finally:
            if cursor:
                cursor.close()
            if conn:
                mysql_db.close_conn(conn)
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user_uid', None)
    #flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('main.auth.login'))
