import threading
import time
import os
from datetime import datetime, timedelta
import lib.mysql_db as mysql_db
from flask import render_template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class ReportService(threading.Thread):
    def __init__(self, app):
        super().__init__()
        self._stop_event = threading.Event()
        self.app = app
        self.daemon = True # 메인 스레드가 종료되면 함께 종료되도록 설정
        self.report_base_dir = os.path.join(app.root_path, 'reports')
        os.makedirs(self.report_base_dir, exist_ok=True)

    def run(self):
        with self.app.app_context(): # 스레드 시작 시 app_context 푸시
            mysql_db.create_db_pool() # DB 풀 초기화
            while not self._stop_event.is_set():
                print(f"[{datetime.now()}] Report service is running...")
                self.check_and_insert_report_requests()
                self.process_report_list()
                time.sleep(10) # 10초마다 작업 수행
        # 컨텍스트는 스레드 종료 시 자동으로 팝됩니다.

    def stop(self):
        self._stop_event.set()
        print("Report service stopping...")

    def check_and_insert_report_requests(self):
        conn = mysql_db.get_conn()
        if not conn:
            self.app.logger.error("Failed to get DB connection for report requests.")
            return
        cursor = conn.cursor()
        try:
            # 모든 사용자 설정 가져오기
            cursor.execute("SELECT user_id, report_daily, report_weekly, report_monthly, report_send_time, report_recipients FROM daily_db_setting_config")
            settings = cursor.fetchall()

            for setting in settings:
                user_id, report_daily, report_weekly, report_monthly, report_send_time, report_recipients = setting
                
                # 해당 user_id의 모든 프로젝트 가져오기
                cursor.execute("SELECT id, batch FROM daily_db_projects WHERE user_id = %s", (user_id,))
                projects = cursor.fetchall()

                current_time = datetime.now().time()
                send_time_dt = datetime.strptime(str(report_send_time), '%H:%M:%S').time()

                # 보고서 발송 시간 이후에만 요청 삽입
                if current_time >= send_time_dt:
                    for prj_id, batch in projects:
                        # Daily Report
                        if report_daily:
                            self._insert_report_if_not_exists(cursor, prj_id, batch, 'daily', send_time_dt)
                        # Weekly Report
                        if report_weekly:
                            self._insert_report_if_not_exists(cursor, prj_id, batch, 'weekly', send_time_dt)
                        # Monthly Report
                        if report_monthly:
                            self._insert_report_if_not_exists(cursor, prj_id, batch, 'monthly', send_time_dt)
                        
                        # Final Report (프로젝트 상태가 'done'일 경우)
                        cursor.execute("SELECT state FROM daily_db_projects WHERE id = %s", (prj_id,))
                        project_state = cursor.fetchone()[0]
                        if project_state == 'done':
                            self._insert_report_if_not_exists(cursor, prj_id, batch, 'final', send_time_dt)
            conn.commit()
        except Exception as e:
            self.app.logger.error(f"Error checking and inserting report requests: {e}")
            conn.rollback()
        finally:
            cursor.close()
            mysql_db.close_conn(conn)

    def _insert_report_if_not_exists(self, cursor, prj_id, batch, report_type, send_time_dt):
        # 최종 레포트의 경우, insert_date와 상관없이 해당 프로젝트/배치에 대한 final 레포트가 없으면 삽입
        if report_type == 'final':
            cursor.execute(
                "SELECT id FROM daily_db_report_list WHERE prj_id = %s AND batch = %s AND report_type = %s",
                (prj_id, batch, report_type)
            )
        else:
            # 오늘 날짜의 해당 타입 레포트가 이미 요청되었는지 확인
            today = datetime.now().date()
            cursor.execute(
                "SELECT id FROM daily_db_report_list WHERE prj_id = %s AND batch = %s AND report_type = %s AND DATE(insert_date) = %s",
                (prj_id, batch, report_type, today)
            )
        
        if not cursor.fetchone():
            # 요청 시간 이후에 레코드가 없으면 삽입
            # 실제 발송 시간은 report_send_time을 따르지만, insert_date는 현재 시간으로 기록
            cursor.execute(
                "INSERT INTO daily_db_report_list (prj_id, batch, report_type, state) VALUES (%s, %s, %s, %s)",
                (prj_id, batch, report_type, 'Queued')
            )
            self.app.logger.info(f"Inserted {report_type} report request for project {prj_id}, batch {batch}")

    def process_report_list(self):
        conn = mysql_db.get_conn()
        if not conn:
            self.app.logger.error("Failed to get DB connection for processing report list.")
            return
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, prj_id, batch, report_type FROM daily_db_report_list WHERE state = 'Queued' ORDER BY insert_date ASC")
            queued_reports = cursor.fetchall()

            for report_id, prj_id, batch, report_type in queued_reports:
                cursor.execute("UPDATE daily_db_report_list SET state = 'Generating' WHERE id = %s", (report_id,))
                conn.commit()
                
                report_path = self.generate_report(report_id, prj_id, batch, report_type)
                print("Generating report...", report_id, prj_id, batch, report_type, report_path)
                if report_path:
                    cursor.execute("UPDATE daily_db_report_list SET report_path = %s, state = 'Completed' WHERE id = %s", (report_path, report_id,))
                    conn.commit()
                    self.app.logger.info(f"Report {report_type} for project {prj_id}, batch {batch} generated at {report_path}")
                    
                    # 메일 전송 (임시)
                    self.send_report_email(report_id, prj_id, batch, report_type, report_path)
                    cursor.execute("UPDATE daily_db_report_list SET state = 'Sent' WHERE id = %s", (report_id,))
                    conn.commit()
                else:
                    cursor.execute("UPDATE daily_db_report_list SET state = 'Failed' WHERE id = %s", (report_id,))
                    conn.commit()
                    self.app.logger.error(f"Failed to generate {report_type} report for project {prj_id}, batch {batch}")
        except Exception as e:
            self.app.logger.error(f"Error processing report list: {e}")
            conn.rollback()
        finally:
            cursor.close()
            mysql_db.close_conn(conn)

    def generate_report(self, report_id, prj_id, batch, report_type):
        with self.app.app_context(): # generate_report 함수 전체를 app_context 내에서 실행
            # 레포트 데이터를 DB에서 가져오는 로직
            conn = mysql_db.get_conn()
            if not conn:
                self.app.logger.error("Failed to get DB connection for generating report.")
                return None
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("SELECT * FROM daily_db_projects WHERE id = %s", (prj_id,))
                project = cursor.fetchone()

                if not project:
                    self.app.logger.error(f"Project {prj_id} not found for report generation.")
                    return None

                # 파일 업데이트 시간 기준으로 데이터 필터링
                end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                start_date = None

                if report_type == 'daily':
                    start_date = end_date - timedelta(days=1)
                elif report_type == 'weekly':
                    # 월요일 00:00 기준
                    start_date = end_date - timedelta(days=end_date.weekday()) - timedelta(weeks=1)
                    end_date = end_date - timedelta(days=end_date.weekday())
                elif report_type == 'monthly':
                    # 이달 1일 00:00 기준
                    start_date = end_date.replace(day=1) - timedelta(days=1)
                    start_date = start_date.replace(day=1)
                    end_date = end_date.replace(day=1)
                elif report_type == 'final':
                    # 프로젝트의 모든 배치 파일
                    start_date = datetime.min # 모든 시간 포함
                    end_date = datetime.max # 모든 시간 포함
                else:
                    self.app.logger.error(f"Unknown report type: {report_type}")
                    return None

                # daily_db_project_files와 daily_db_project_task_file_analysis를 조인하여 파일 정보 및 분석 결과 가져오기
                if report_type == 'final':
                    cursor.execute(
                        """
                        SELECT
                            dpf.*,
                            dptfa.flaw_detail,
                            dptfa.patch_msgs,
                            dptfa.execute_type,
                            dptfa.execute_succeed,
                            dptfa.execute_msgs
                        FROM daily_db_project_files dpf
                        LEFT JOIN daily_db_project_task_file_analysis dptfa ON dpf.id = dptfa.file_id
                        WHERE dpf.prj_id = %s AND dpf.batch = %s
                        ORDER BY dpf.id, dptfa.insert_date DESC
                        """,
                        (prj_id, batch)
                    )
                else:
                    cursor.execute(
                        """
                        SELECT
                            dpf.*,
                            dptfa.flaw_detail,
                            dptfa.patch_msgs,
                            dptfa.execute_type,
                            dptfa.execute_succeed,
                            dptfa.execute_msgs
                        FROM daily_db_project_files dpf
                        LEFT JOIN daily_db_project_task_file_analysis dptfa ON dpf.id = dptfa.file_id
                        WHERE dpf.prj_id = %s AND dpf.batch = %s AND dpf.update_date >= %s AND dpf.update_date < %s
                        ORDER BY dpf.id, dptfa.insert_date DESC
                        """,
                        (prj_id, batch, start_date, end_date)
                    )
                raw_files_data = cursor.fetchall()

                # 파일별로 분석 결과를 그룹화
                files_data = {}
                print(raw_files_data)
                for row in raw_files_data:
                    file_id = row['id']
                    if file_id not in files_data:
                        files_data[file_id] = {
                            'id': row['id'],
                            'prj_id': row['prj_id'],
                            'batch': row['batch'],
                            'filepath': row['filepath'],
                            'result': row['result'],
                            'flaws': row['flaws'],
                            'insert_date': row['insert_date'],
                            'update_date': row['update_date'],
                            'analysis_results': []
                        }
                    if row['flaw_detail']: # 분석 결과가 있는 경우에만 추가
                        files_data[file_id]['analysis_results'].append({
                            'flaw_detail': row['flaw_detail'],
                            'patch_msgs': row['patch_msgs'],
                            'execute_type': row['execute_type'],
                            'execute_succeed': row['execute_succeed'],
                            'execute_msgs': row['execute_msgs']
                        })
                files = list(files_data.values())

                # 파일 처리 상태 요약 집계
                total_files = len(files)
                completed_files = sum(1 for f in files if f['result'] == 'Completed')
                skipped_files = sum(1 for f in files if f['result'] == 'Skipped')
                failed_files = sum(1 for f in files if f['result'] == 'Failed')
                queued_files = sum(1 for f in files if f['result'] == 'Queued')

                file_summary = {
                    'total': total_files,
                    'completed': completed_files,
                    'skipped': skipped_files,
                    'failed': failed_files,
                    'queued': queued_files
                }

                # 레포트 HTML 파일 저장 경로 설정
                report_dir = os.path.join(self.report_base_dir, report_type, str(prj_id), str(batch))
                os.makedirs(report_dir, exist_ok=True)
                report_filename = f"{report_id}.html"
                report_filepath = os.path.join(report_dir, report_filename)

                # Flask의 render_template를 사용하여 HTML 생성
                # 이 부분은 실제 레포트 템플릿과 데이터 구조에 따라 달라집니다.
                # templates/report/report_template.html 파일을 사용한다고 가정
                # 이 템플릿은 standalone하게 동작할 수 있도록 CSS/JS를 내장하거나 CDN 링크를 사용해야 합니다.
                
                # 임시 데이터
                report_data = {
                    'project': project,
                    'batch': batch,
                    'report_type': report_type,
                    'files': files,
                    'file_summary': file_summary, # 파일 요약 정보 추가
                    'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'start_date': start_date.strftime('%Y-%m-%d %H:%M:%S') if start_date else 'N/A',
                    'end_date': end_date.strftime('%Y-%m-%d %H:%M:%S') if end_date else 'N/A'
                }

                # test_request_context를 사용하여 가짜 요청 컨텍스트 제공
                with self.app.test_request_context():
                    rendered_html = render_template(f'report/{report_type}_report_template.html', data=report_data)
                
                with open(report_filepath, 'w', encoding='utf-8') as f:
                    f.write(rendered_html)
                
                return report_filepath
            except Exception as e:
                self.app.logger.error(f"Error generating report for project {prj_id}, batch {batch}, type {report_type}: {e}")
                return None
            finally:
                cursor.close()
                mysql_db.close_conn(conn)

    def send_report_email(self, report_id, prj_id, batch, report_type, report_path):
        conn = mysql_db.get_conn()
        if not conn:
            self.app.logger.error("Failed to get DB connection for sending report email.")
            return
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT dusc.report_recipients, dusc.report_send_time, du.uid as user_email
                FROM daily_db_report_list dbrl
                JOIN daily_db_projects dbp ON dbrl.prj_id = dbp.id
                JOIN daily_db_users du ON dbp.user_id = du.id
                JOIN daily_db_setting_config dusc ON du.id = dusc.user_id
                WHERE dbrl.id = %s
            """, (report_id,))
            result = cursor.fetchone()

            if result:
                recipients_str, send_time, user_email = result
                recipients = [user_email] # 기본적으로 사용자 본인 포함
                if recipients_str:
                    recipients.extend([r.strip() for r in recipients_str.split(',') if r.strip()])
                recipients = list(set(recipients)) # 중복 제거

                subject = f"[{report_type.upper()} Report] Project {prj_id} - Batch {batch}"
                body = f"""
                <html>
                <body>
                    <p>안녕하세요,</p>
                    <p>요청하신 {report_type} 레포트가 생성되었습니다.</p>
                    <p>프로젝트 ID: {prj_id}</p>
                    <p>배치: {batch}</p>
                    <p>레포트 타입: {report_type}</p>
                    <p>레포트 파일 경로: <a href="file:///{report_path}">{report_path}</a></p>
                    <p>웹에서 보기: <a href="http://localhost:5000/report/{report_type}/{prj_id}/{batch}/{report_id}">레포트 보기</a></p>
                    <p>감사합니다.</p>
                </body>
                </html>
                """
                self._send_email_actual(recipients, subject, body)
                self.app.logger.info(f"Report email sent for report {report_id} to {recipients}")
            else:
                self.app.logger.warning(f"Could not find recipient info for report {report_id}")
        except Exception as e:
            self.app.logger.error(f"Error sending report email for report {report_id}: {e}")
        finally:
            cursor.close()
            mysql_db.close_conn(conn)

    def _send_email_actual(self, recipients, subject, body):
        # 실제 이메일 전송 로직 (SMTP 서버 설정 필요)
        # 이 부분은 실제 환경에 맞게 설정해야 합니다.
        sender_email = "your_email@example.com" # 실제 발신 이메일 주소
        sender_password = "your_email_password" # 실제 발신 이메일 비밀번호 (보안상 환경 변수 사용 권장)
        smtp_server = "smtp.example.com" # 실제 SMTP 서버 주소
        smtp_port = 587 # 실제 SMTP 포트

        msg = MIMEMultipart("alternative")
        msg['From'] = sender_email
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        try:
            # with smtplib.SMTP(smtp_server, smtp_port) as server:
            #     server.starttls()
            #     server.login(sender_email, sender_password)
            #     server.send_message(msg)
            self.app.logger.info(f"Simulated email sent to {recipients} with subject: {subject}")
        except Exception as e:
            self.app.logger.error(f"Failed to send email: {e}")
