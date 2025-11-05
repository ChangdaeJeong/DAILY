from flask import Flask, render_template, flash, redirect, url_for, session
import mysql_db
from router import main_bp
from flask_bcrypt import Bcrypt # Flask-Bcrypt 임포트
from lib.inject import check_login_status, inject_sidebar_data, inject_user # inject 함수 임포트

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # Flash 메시지를 위해 secret_key 설정
app.bcrypt = Bcrypt(app) # Bcrypt 초기화 및 app 인스턴스에 직접 할당

@app.before_first_request
def initialize_db_pool():
    mysql_db.create_db_pool()

app.register_blueprint(main_bp)

# 애플리케이션 전역에 before_request 핸들러 등록
app.before_request(check_login_status)
app.before_request(inject_sidebar_data)

# context_processor 등록
app.context_processor(inject_user)

if __name__ == '__main__':
    app.run(debug=True)
