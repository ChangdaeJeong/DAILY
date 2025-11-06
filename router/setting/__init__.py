from flask import Blueprint, request, render_template, session, redirect, url_for, flash
import lib.mysql_db as mysql_db

setting_bp = Blueprint('setting', __name__, url_prefix='/setting')

@setting_bp.route('/')
def setting_page():
    logged_in_user_id = session.get('user', {}).get('user', {}).get('id')

    conn = mysql_db.get_conn()
    cursor = conn.cursor(dictionary=True)

    setting_config = None
    try:
        cursor.execute("SELECT * FROM daily_db_setting_config WHERE user_id = %s", (logged_in_user_id,))
        setting_config = cursor.fetchone()
        if setting_config:
            # timedelta 객체를 HH:MM:SS 형식의 문자열로 변환하여 템플릿에서 쉽게 사용
            def format_timedelta_to_hhmmss(td):
                if not td:
                    return None
                total_seconds = int(td.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{hours:02}:{minutes:02}:{seconds:02}"

            if 'operation_time_start' in setting_config and setting_config['operation_time_start']:
                setting_config['operation_time_start'] = format_timedelta_to_hhmmss(setting_config['operation_time_start'])
            if 'operation_time_end' in setting_config and setting_config['operation_time_end']:
                setting_config['operation_time_end'] = format_timedelta_to_hhmmss(setting_config['operation_time_end'])
            if 'report_send_time' in setting_config and setting_config['report_send_time']:
                setting_config['report_send_time'] = format_timedelta_to_hhmmss(setting_config['report_send_time'])
    except Exception as e:
        flash(f"설정 정보를 불러오는 중 오류가 발생했습니다: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    print(setting_config)

    return render_template('setting/setting.html', setting_config=setting_config)

@setting_bp.route('/save', methods=['POST'])
def save_setting():
    logged_in_user_id = session.get('user', {}).get('user', {}).get('id')

    # 폼 데이터 가져오기
    operation_days = request.form.getlist('operation_days') # 리스트로 받아옴
    operation_days_str = ','.join(operation_days) if operation_days else ''
    operation_time_start = request.form['operation_time_start']
    operation_time_end = request.form['operation_time_end']
    ai_request_per_hour = int(request.form['ai_request_per_hour'])
    max_retry_attempts = int(request.form['max_retry_attempts'])

    report_daily = 'report_daily' in request.form
    report_weekly = 'report_weekly' in request.form
    report_monthly = 'report_monthly' in request.form
    report_send_time = request.form['report_send_time']
    report_recipients = request.form['report_recipients']

    conn = mysql_db.get_conn()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id FROM daily_db_setting_config WHERE user_id = %s", (logged_in_user_id,))
        existing_setting = cursor.fetchone()

        if existing_setting:
            # 업데이트
            cursor.execute(
                """
                UPDATE daily_db_setting_config
                SET operation_days = %s, operation_time_start = %s, operation_time_end = %s,
                    ai_request_per_hour = %s, max_retry_attempts = %s,
                    report_daily = %s, report_weekly = %s, report_monthly = %s,
                    report_send_time = %s, report_recipients = %s
                WHERE user_id = %s
                """,
                (operation_days_str, operation_time_start, operation_time_end,
                 ai_request_per_hour, max_retry_attempts,
                 report_daily, report_weekly, report_monthly,
                 report_send_time, report_recipients, logged_in_user_id)
            )
            flash('설정 정보가 성공적으로 업데이트되었습니다.', 'success')
        else:
            # 삽입
            cursor.execute(
                """
                INSERT INTO daily_db_setting_config
                (user_id, operation_days, operation_time_start, operation_time_end,
                 ai_request_per_hour, max_retry_attempts,
                 report_daily, report_weekly, report_monthly,
                 report_send_time, report_recipients)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (logged_in_user_id, operation_days_str, operation_time_start, operation_time_end,
                 ai_request_per_hour, max_retry_attempts,
                 report_daily, report_weekly, report_monthly,
                 report_send_time, report_recipients)
            )
            flash('설정 정보가 성공적으로 저장되었습니다.', 'success')
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"설정 정보를 저장하는 중 오류가 발생했습니다: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('main.setting.setting_page'))
