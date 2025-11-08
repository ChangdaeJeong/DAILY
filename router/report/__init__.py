from flask import render_template, Blueprint, send_from_directory, current_app
import os

report_bp = Blueprint('report', __name__)

@report_bp.route('/')
def report_page():
    return render_template('report.html')

@report_bp.route('/<report_type>/<int:project_id>/<int:batch>/<int:report_id>')
def serve_report(report_type, project_id, batch, report_id):
    # TODO: report_id를 사용하여 daily_db_report_list에서 report_path를 조회
    # 현재는 임시로 report_path를 구성하여 사용
    # 실제 구현에서는 DB에서 report_path를 가져와야 합니다.
    
    # 예시: report_path는 'reports/daily/1/1/1.html'과 같은 형태라고 가정
    # report_path = f"reports/{report_type}/{project_id}/{batch}/{report_id}.html"
    
    # 임시로 report_path를 하드코딩 (실제 DB 연동 후 수정 필요)
    # report_path = os.path.join(current_app.root_path, 'reports', report_type, str(project_id), str(batch), f"{report_id}.html")
    
    # report_path는 DB에 저장된 절대 경로 또는 상대 경로가 될 수 있습니다.
    # 여기서는 'reports' 디렉토리 아래에 저장된다고 가정하고, send_from_directory를 사용합니다.
    
    # 실제 report_path를 DB에서 가져오는 로직이 필요합니다.
    # 예시:
    # from lib.mysql_db import get_db_connection
    # conn = get_db_connection()
    # cursor = conn.cursor()
    # cursor.execute("SELECT report_path FROM daily_db_report_list WHERE id = %s", (report_id,))
    # result = cursor.fetchone()
    # if result:
    #     full_report_path = result[0]
    #     report_dir = os.path.dirname(full_report_path)
    #     report_filename = os.path.basename(full_report_path)
    #     return send_from_directory(report_dir, report_filename)
    # else:
    #     return "Report not found", 404

    # 임시로 'templates/report' 디렉토리에서 파일을 서빙하도록 설정
    # 실제 레포트 파일은 'reports' 디렉토리와 같은 별도의 위치에 저장되어야 합니다.
    # 여기서는 개발 편의를 위해 templates/report에 임시 파일을 가정합니다.
    
    # report_filename = f"{report_type}_{project_id}_{batch}_{report_id}.html"
    # return send_from_directory(os.path.join(current_app.root_path, 'templates', 'report'), report_filename)

    # 실제 레포트 파일이 저장될 경로 (예: DAILY/reports)
    report_base_dir = os.path.join(current_app.root_path, 'reports')
    report_dir = os.path.join(report_base_dir, report_type, str(project_id), str(batch))
    report_filename = f"{report_id}.html" # report_id.html 형태로 저장된다고 가정

    if not os.path.exists(os.path.join(report_dir, report_filename)):
        # DB에서 report_path를 조회하는 로직 추가
        import lib.mysql_db as mysql_db
        conn = mysql_db.get_conn()
        if not conn:
            current_app.logger.error("Failed to get DB connection for serving report.")
            return "Database connection error", 500
        cursor = conn.cursor()
        cursor.execute("SELECT report_path FROM daily_db_report_list WHERE id = %s AND prj_id = %s AND batch = %s AND report_type = %s", (report_id, project_id, batch, report_type))
        result = cursor.fetchone()
        cursor.close()
        mysql_db.close_conn(conn)

        if result and result[0]:
            full_report_path = result[0]
            report_dir = os.path.dirname(full_report_path)
            report_filename = os.path.basename(full_report_path)
            if os.path.exists(os.path.join(report_dir, report_filename)):
                return send_from_directory(report_dir, report_filename)
            else:
                return "Report file not found on disk.", 404
        else:
            return "Report entry not found in database.", 404
    
    return send_from_directory(report_dir, report_filename)
