from flask import Flask
from router import main_bp
from router.report import report_bp # report_bp 임포트
from flask_bcrypt import Bcrypt
import lib.inject as inject
import lib.mysql_db as mysql_db
from lib.bg_service import BackgroundService
from lib.report_service import ReportService # ReportService 임포트
import atexit

app = Flask(__name__)
app.secret_key = 'D.A.I.L.Y_Secret_Key_v1.0'

app.before_first_request(mysql_db.create_db_pool)
app.before_first_request(lambda: setattr(app, 'bcrypt', Bcrypt(app)))

app.before_request(inject.check_login_status)

app.context_processor(inject.user)
app.context_processor(inject.sidebar_data)

app.register_blueprint(main_bp)
app.register_blueprint(report_bp, url_prefix='/report') # report_bp 등록

if __name__ == '__main__':
    bg_service = BackgroundService()
    bg_service.start()
    print("Background service started.")
    
    report_service = ReportService(app) # ReportService 인스턴스 생성
    report_service.start() # ReportService 시작
    print("Report service started.")

    # 애플리케이션 종료 시 백그라운드 서비스가 안전하게 중지되도록 등록
    atexit.register(lambda bgs=bg_service: bgs and bgs.stop() and bgs.join())
    atexit.register(lambda rs=report_service: rs and rs.stop() and rs.join()) # ReportService 등록

    # Flask 개발 서버는 기본적으로 단일 스레드이므로, threaded=True 옵션을 추가하여
    # 백그라운드 스레드가 Flask 요청 처리와 독립적으로 실행될 수 있도록 합니다.
    # use_reloader=False는 개발 서버가 코드 변경 시 자동으로 재시작되는 것을 방지하여
    # 백그라운드 스레드가 예기치 않게 종료되는 것을 막습니다.
    # 그러나 실제 프로덕션 환경에서는 Gunicorn, uWSGI와 같은 WSGI 서버를 사용해야 합니다.
    # debug=True는 Flask 개발 서버에서 두 개의 프로세스를 생성하여 백그라운드 스레드와 충돌할 수 있습니다.
    # 따라서 백그라운드 스레드가 지속적으로 동작하도록 debug=False로 설정합니다。
    app.run(debug=False, threaded=True, use_reloader=False)
