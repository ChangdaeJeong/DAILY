import threading
import time
import datetime
import lib.mysql_db as mysql_db # get_conn, close_conn, create_db_pool을 mysql_db.함수명 형태로 사용
import json # 사용자 config를 읽을 때 필요할 수 있습니다.
import importlib.util
import sys
import os
import subprocess # 패치 적용을 위해 추가
import lib.gemini as gemini # Gemini API 호출을 위해 추가
import run_if # run_if.py 모듈 임포트
import lib.message as message # 메시지 추가를 위해 추가

class BackgroundService(threading.Thread):
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()
        self.daemon = True # 메인 스레드가 종료되면 함께 종료되도록 설정

    def run(self):
        mysql_db.create_db_pool() # DB 풀 초기화
        while not self._stop_event.is_set():
            print(f"[{datetime.datetime.now()}] Background service is running...")
            self.process_daily_tasks()
            time.sleep(5) # 5초마다 작업 수행

    def stop(self):
        self._stop_event.set()
        print("Background service stopping...")

    def process_daily_tasks(self):
        conn = None
        cursor = None
        try:
            conn = mysql_db.get_conn()
            if not conn:
                print("Failed to get DB connection.")
                return

            cursor = conn.cursor(dictionary=True) # 딕셔너리 형태로 결과를 받기 위해 dictionary=True 설정

            # 1. 사용자별 config를 읽고, 현재 시간에 해당되는 사용자들의 list를 뽑는다.
            current_time = datetime.datetime.now().time()
            current_day = datetime.datetime.now().strftime('%a') # Mon, Tue 등 요일 약어

            # TODO: daily_db_setting_config 테이블에서 현재 시간에 해당하는 사용자들을 조회하는 쿼리 작성
            # 예시: SELECT u.id, u.uid, s.operation_days, s.operation_time_start, s.operation_time_end
            #       FROM daily_db_users u JOIN daily_db_setting_config s ON u.id = s.user_id
            #       WHERE TIME(NOW()) BETWEEN s.operation_time_start AND s.operation_time_end
            #       AND FIND_IN_SET(DAYOFWEEK(NOW()), 'Mon,Tue,Wed,Thu,Fri,Sat,Sun') > 0 (요일 체크)
            #       (실제 쿼리는 MySQL의 FIND_IN_SET 함수와 DAYOFWEEK 함수를 활용하여 구현해야 합니다.)
            
            # 1. 사용자별 config를 읽고, 현재 시간에 해당되는 사용자들의 list를 뽑는다.
            current_time_str = current_time.strftime('%H:%M:%S')
            
            cursor.execute("""
                SELECT u.id, u.uid, s.operation_days, s.operation_time_start, s.operation_time_end, s.max_retry_attempts
                FROM daily_db_users u
                JOIN daily_db_setting_config s ON u.id = s.user_id
                WHERE TIME(%s) BETWEEN s.operation_time_start AND s.operation_time_end
                AND FIND_IN_SET(%s, s.operation_days) > 0
            """, (current_time_str, current_day))
            users_to_process = cursor.fetchall()

            if not users_to_process:
                print(f"[{datetime.datetime.now()}] No users found for current time ({current_time_str}) and day ({current_day}).")
                return

            user_ids = [user['id'] for user in users_to_process]
            if not user_ids:
                print(f"[{datetime.datetime.now()}] No active user IDs to process.")
                return

            # 2. 사용자 리스트에 해당하는 프로젝트 중 init이나 doing인 프로젝트 정보를 뽑는다.
            # 3. 해당 프로젝트의 daily_db_project_files 파일 중 Queued인 것을 하나 찾는다. (id가 가장 빠른)
            # 이 두 단계를 하나의 쿼리로 합칩니다.
            cursor.execute("""
                SELECT
                    dp.id AS prj_id, dp.name AS prj_name, dp.root_dir,
                    dp.batch AS prj_batch, dp.user_id, dp.state AS prj_state,
                    dpf.id AS file_id, dpf.filepath, dpf.flaws, dpf.batch AS file_batch
                FROM
                    daily_db_projects dp
                JOIN
                    daily_db_project_files dpf ON dp.id = dpf.prj_id AND dp.batch = dpf.batch
                WHERE
                    dp.user_id IN (%s) AND (dp.state = 'init' OR dp.state = 'doing')
                    AND dpf.result = 'Queued'
                ORDER BY
                    dpf.id ASC
                LIMIT 1
            """ % ','.join(['%s'] * len(user_ids)), tuple(user_ids))
            
            file_to_analyze_info = cursor.fetchone()

            if file_to_analyze_info:
                print(f"    Found file to analyze: {file_to_analyze_info['filepath']} (Project ID: {file_to_analyze_info['prj_id']}, File ID: {file_to_analyze_info['file_id']})")
                # project 정보와 file_info를 재구성하여 analyze_and_patch_file 호출
                project_data = {
                    'id': file_to_analyze_info['prj_id'],
                    'name': file_to_analyze_info['prj_name'],
                    'root_dir': os.path.normpath(file_to_analyze_info['root_dir']),
                    'batch': file_to_analyze_info['prj_batch'],
                    'user_id': file_to_analyze_info['user_id']
                }
                file_data = {
                    'id': file_to_analyze_info['file_id'],
                    'filepath': os.path.normpath(file_to_analyze_info['filepath'].lstrip('/')),
                    'flaws': file_to_analyze_info['flaws'],
                    'batch': file_to_analyze_info['file_batch']
                }
                # print(project_data, file_data)
                self.analyze_and_patch_file(conn, cursor, project_data, file_data)
            else:
                print(f"    No Queued files found for any active projects.")
            
            # 8. 모든 사용자 및 프로젝트 파일 처리가 완료된 후, 모든 프로젝트에 대해 상태 업데이트를 확인
            self.check_and_update_all_projects_state(conn, cursor)

        except mysql_db.Error as e: # Error를 mysql_db.Error로 변경
            print(f"Database error in process_daily_tasks: {e}")
        except Exception as e:
            print(f"An unexpected error occurred in process_daily_tasks: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                mysql_db.close_conn(conn)

    def analyze_and_patch_file(self, conn, cursor, project_info, file_info):
        file_id = file_info['id']
        root_dir = project_info['root_dir']
        project_root_dir = os.path.abspath(os.path.join('workspace', root_dir))
        filepath = file_info['filepath']
        current_flaws = file_info['flaws']
        project_id = project_info['id'] # project_id를 변수로 저장

        full_filepath = os.path.join(project_root_dir, filepath) # 절대 경로 생성
        print(full_filepath)
        source_code = ""
        if os.path.exists(full_filepath):
            with open(full_filepath, 'r', encoding='utf-8') as f:
                source_code = f.read()
        else:
            print(f"      Failed to open source {filepath}")
            cursor.execute("UPDATE daily_db_project_files SET flaws = %s, result = %s WHERE id = %s", ('File is not found', 'Failed', file_id,))
            conn.commit()
            return

        # 5.1 AI 서비스 호출하여 중대한 문제점 1가지 요청 후 flaws 업데이트
        ai_review = self.call_ai_for_flaw(filepath, source_code) # AI 서비스 호출 (래퍼 함수)
        ai_flaw_str = "No flaw detected by AI." # 기본값 설정
        if ai_review and 'issue_analysis' in ai_review:
            analysis = ai_review.get('issue_analysis')
            if analysis:
                ai_flaw_str = f"Summary: {analysis.get('issue_summary', 'N/A')}\nType: {analysis.get('vulnerability_type', 'N/A')}\nImpact: {analysis.get('impact_and_severity', 'N/A')}"
                # print(f"      AI review result: {ai_flaw_str}")
                # flaws 업데이트
                cursor.execute("UPDATE daily_db_project_files SET flaws = %s WHERE id = %s", (ai_flaw_str, file_id))
                conn.commit()
                current_flaws = ai_flaw_str
                print(f"      Updated flaws for file {filepath}: {ai_flaw_str}")
                message.add_message(project_id, "AI Flaw Detection", f"File {filepath}: Flaw detected and updated.")
            else:
                print(f"      AI did not return a valid issue_analysis content for file {filepath}.")
        else:
            print(f"      AI did not return a valid flaw analysis for file {filepath}.")
            # AI가 문제점을 찾지 못했으면, 이 파일은 일단 스킵하거나 다음 단계로 진행하지 않을 수 있습니다.
            # 여기서는 일단 다음 단계로 진행하여 'no patch'를 시도하도록 합니다.

        # 5.2 해당 file에 대한 마지막 analysis 레코드가 있다면 가져와서 execute_type과 msgs를 가져온다.
        last_analysis = self.get_last_analysis_record(cursor, file_id)
        last_patch_msgs = last_analysis['patch_msgs'] if last_analysis else None
        last_execute_type = last_analysis['execute_type'] if last_analysis else None
        last_execute_msgs = last_analysis['execute_msgs'] if last_analysis else None
        
        print(f"      Last analysis for {filepath}: Type={last_execute_type}, Msgs={last_execute_msgs}")

        # 6. 문제점과 analysis 레코드의 execute type, msg정보를 추가해 패치 생성 요청
        patch_msgs, patch_explanation = self.call_ai_for_patch(filepath, source_code, last_patch_msgs, f"type: {last_execute_type}\nmsg: {last_execute_msgs}") # AI 서비스 호출 (래퍼 함수)

        new_analysis_id = None
        if not patch_msgs or patch_msgs.strip() == "No patch needed.": # 6.1 수정할 내용이 없다면 execute_type을 no patch로 저장
            execute_type = 'no patch'
            execute_succeed = True
            execute_msgs = 'AI determined no patch was needed.'
            new_analysis_id = self.insert_analysis_record(conn, cursor, file_id, patch_explanation, patch_msgs, execute_type, execute_succeed, execute_msgs)
            print(f"      No patch generated for {filepath}. Analysis ID: {new_analysis_id}")
            message.add_message(project_id, "AI Patch Generation", f"File {filepath}: No patch needed.")
        else: # 6.2 패치가 나온다면 type은 패치로 저장
            execute_type = 'patch'
            execute_succeed = False # 초기값은 실패로 설정
            execute_msgs = 'Patch generation initiated.'
            new_analysis_id = self.insert_analysis_record(conn, cursor, file_id, patch_explanation, patch_msgs, execute_type, execute_succeed, execute_msgs)
            print(f"      Patch generated for {filepath}. Analysis ID: {new_analysis_id}")
            message.add_message(project_id, "AI Patch Generation", f"File {filepath}: Patch generated. Analysis ID: {new_analysis_id}")

            # 6.3 각 patch 적용, build, run 테스트 수행
            # 패치 적용
            patch_succeed, patch_result_msg = self.apply_patch(project_root_dir, filepath, patch_msgs)
            self.update_analysis_record(conn, cursor, new_analysis_id, 'patch', patch_succeed, patch_result_msg)
            if not patch_succeed:
                print(f"        Patch application failed for {filepath}: {patch_result_msg}")
                message.add_message(project_id, "Patch Application", f"File {filepath}: Patch application FAILED. Reason: {patch_result_msg}")
                self.check_and_update_file_state(conn, cursor, file_id, project_info['user_id']) # 7번 로직 호출
                return
            message.add_message(project_id, "Patch Application", f"File {filepath}: Patch applied successfully.")
            # 빌드
            build_succeed, build_result_msg = self.build_project(project_root_dir)
            self.update_analysis_record(conn, cursor, new_analysis_id, 'build', build_succeed, build_result_msg)
            if not build_succeed:
                print(f"        Build failed for {filepath}: {build_result_msg}")
                message.add_message(project_id, "Project Build", f"File {filepath}: Build FAILED. Reason: {build_result_msg}")
                self.check_and_update_file_state(conn, cursor, file_id, project_info['user_id']) # 7번 로직 호출
                return
            message.add_message(project_id, "Project Build", f"File {filepath}: Build succeeded.")

            # 실행
            run_succeed, run_result_msg = self.run_project(project_root_dir)
            self.update_analysis_record(conn, cursor, new_analysis_id, 'run', run_succeed, run_result_msg)
            if not run_succeed:
                print(f"        Run failed for {filepath}: {run_result_msg}")
                message.add_message(project_id, "Project Run", f"File {filepath}: Run FAILED. Reason: {run_result_msg}")
                self.check_and_update_file_state(conn, cursor, file_id, project_info['user_id']) # 7번 로직 호출
                return
            message.add_message(project_id, "Project Run", f"File {filepath}: Run succeeded.")
            
            # 6.4 모든 절차가 성공하면 execute_type은 done으로 저장
            self.update_analysis_record(conn, cursor, new_analysis_id, 'done', True, 'All steps completed successfully.')
            print(f"      All steps succeeded for {filepath}.")
            message.add_message(project_id, "File Analysis & Patch", f"File {filepath}: All steps completed successfully.")

        # 7. 해당 파일의 analysis가 done이면, file record의 state는 Completed, 아니라면 analysis 갯수를 체크하고 user config retry 설정보다 갯수가 많거나 같으면 Failed 처리한다.
        self.check_and_update_file_state(conn, cursor, file_id, project_info['user_id'])

    def call_ai_for_flaw(self, filepath, source_code):
        return {'issue_analysis': {'issue_summary': 'The script attempts to perform a division by zero operation, which will invariably result in an unhandled `ZeroDivisionError` and immediate program termination.', 'vulnerability_type': 'Runtime Error / Logic Error (ZeroDivisionError)', 'impact_and_severity': "The program will crash and exit prematurely every time it is executed, rendering it completely non-functional and preventing any intended subsequent operations from completing. This leads to a loss of availability for the script's intended function. If this code were embedded within a larger application (e.g., a server process, a data processing pipeline, or a critical service), this unhandled exception would cause the specific task or process to fail, potentially leading to a Denial of Service (DoS) for users or dependent systems. The severity is High because it guarantees immediate program failure and prevents any further execution, making the code unreliable and unusable."}}
        # AI 서비스 REST API 호출 로직 구현
        # 프롬프트 입력도 별도 변수로 저장 필요
        print(f"        Calling AI for flaw detection on {filepath}")
        try:
            prompt = find_flaw_prompt.format(filepath=filepath, source_code=source_code)
            response = gemini.chat(prompt)
            flaw_rsp = json.loads(response)
            print(flaw_rsp)
            if 'issue_analysis' in flaw_rsp:
                return flaw_rsp
            else:
                print("        AI service returned no flaw description.")
                return None
        except Exception as e:
            print(f"        Error calling Gemini API for flaw detection: {e}")
            return None

    def get_last_analysis_record(self, cursor, file_id):
        cursor.execute("""
            SELECT patch_msgs, execute_type, execute_msgs
            FROM daily_db_project_task_file_analysis
            WHERE file_id = %s
            ORDER BY id DESC
            LIMIT 1
        """, (file_id,))
        return cursor.fetchone()

    def call_ai_for_patch(self, filepath, source_code, last_patch_msgs, last_execute_msgs):
        return '--- /projects/init1/file_a.py\n+++ /projects/init1/file_a.py\n@@ -3,5 +3,8 @@\n if __name__ == "__main__":\n     # div by zero error\n-    print(10 / 0)\n+    try:\n+        print(10 / 0)\n+    except ZeroDivisionError:\n+        print("Error: Attempted to divide by zero!")\n     print("End of file_a.py")\n', 'Yes it is'
        try:
            response = gemini.chat(get_patch_prompt.format(filepath=filepath, source_code=source_code, previous_patch=last_patch_msgs, patch_problem_description=last_execute_msgs))
            print(f"call ai for patch response: {response}")
            rsp = json.loads(response)
            if 'patch' in rsp and 'explanation' in rsp:
                return rsp['patch'], rsp['explanation']
            else:
                print("        AI service returned no patch content.")
                return "No patch needed.", None
        except Exception as e:
            print(f"        Error calling Gemini API for patch generation: {e}")
            return "No patch needed.", None

    def insert_analysis_record(self, conn, cursor, file_id, flaw_detail, patch_msgs, execute_type, execute_succeed, execute_msgs):
        cursor.execute("""
            INSERT INTO daily_db_project_task_file_analysis
            (file_id, flaw_detail, patch_msgs, execute_type, execute_succeed, execute_msgs)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (file_id, flaw_detail, patch_msgs, execute_type, execute_succeed, execute_msgs))
        conn.commit()
        return cursor.lastrowid

    def update_analysis_record(self, conn, cursor, analysis_id, execute_type, execute_succeed, execute_msgs):
        cursor.execute("""
            UPDATE daily_db_project_task_file_analysis
            SET execute_type = %s, execute_succeed = %s, execute_msgs = %s
            WHERE id = %s
        """, (execute_type, execute_succeed, execute_msgs, analysis_id))
        conn.commit()

    def apply_patch(self, project_root_dir, filepath, patch_content):
        # 실제 패치 적용 로직 구현
        # patch_content를 사용하여 project_root_dir/filepath에 패치를 적용
        print(f"        Applying patch to {project_root_dir}{filepath}...")
        
        full_filepath = os.path.join(project_root_dir, filepath) # 절대 경로 생성
        
        # 패치 내용을 임시 파일로 저장
        temp_patch_file = os.path.join(project_root_dir, "temp_patch.diff")
        try:
            with open(temp_patch_file, "w", encoding="utf-8") as f:
                f.write(patch_content)
            
            # 'patch' 명령어를 사용하여 패치 적용
            # -p1 옵션은 첫 번째 경로 구성 요소를 제거합니다. (diff 파일이 보통 a/path/to/file, b/path/to/file 형식이기 때문)
            # -N 옵션은 새로운 파일을 생성합니다.
            # --dry-run 옵션으로 먼저 테스트 실행
            dry_run_command = ['patch', '-p1', '-N', '--dry-run', '-i', temp_patch_file, '-d', project_root_dir]
            dry_run_result = subprocess.run(dry_run_command, capture_output=True, text=True, cwd=project_root_dir)
            print(dry_run_result)

            if dry_run_result.returncode != 0:
                return False, f"Patch dry-run failed: {dry_run_result.stderr}"

            # 실제 패치 적용
            apply_command = ['patch', '-p1', '-N', '-i', temp_patch_file, '-d', project_root_dir]
            apply_result = subprocess.run(apply_command, capture_output=True, text=True, cwd=project_root_dir)

            if apply_result.returncode == 0:
                return True, "Patch applied successfully."
            else:
                return False, f"Patch application failed: {apply_result.stderr}"
        except FileNotFoundError:
            return False, "Patch command not found. Please ensure 'patch' utility is installed and in PATH."
        except Exception as e:
            return False, f"Error during patch application: {e}"
        finally:
            if os.path.exists(temp_patch_file):
                os.remove(temp_patch_file)

    def build_project(self, project_root_dir):
        # 프로젝트 빌드 로직 구현
        print(f"        Building project in {project_root_dir}...")
        try:
            result = run_if.execute_interface_build(project_root_dir)
            return result["success"], result["stdout"] + result["stderr"]
        except Exception as e:
            return False, f"Error during project build: {e}"

    def run_project(self, project_root_dir):
        # 프로젝트 실행 로직 구현
        print(f"        Running project in {project_root_dir}...")
        try:
            result = run_if.execute_interface_run(project_root_dir)
            return result["success"], result["stdout"] + result["stderr"]
        except Exception as e:
            return False, f"Error during project run: {e}"

    def check_and_update_file_state(self, conn, cursor, file_id, user_id):
        print(file_id, user_id)
        # 7. 해당 파일의 analysis가 done이면, file record의 state는 Completed, 아니라면 analysis 갯수를 체크하고 user config retry 설정보다 갯수가 많거나 같으면 Failed 처리한다.
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM daily_db_project_task_file_analysis
            WHERE file_id = %s AND execute_type = 'done'
        """, (file_id,))
        done_count = cursor.fetchone()['cnt']

        if done_count > 0:
            cursor.execute("UPDATE daily_db_project_files SET result = 'Completed' WHERE id = %s", (file_id,))
            conn.commit()
            print(f"      File {file_id} state updated to 'Completed'.")
        else:
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM daily_db_project_task_file_analysis
                WHERE file_id = %s
            """, (file_id,))
            analysis_count = cursor.fetchone()['cnt']

            cursor.execute("""
                SELECT max_retry_attempts FROM daily_db_setting_config
                WHERE user_id = %s
            """, (user_id,))
            config = cursor.fetchone()
            max_retry_attempts = config['max_retry_attempts'] if config else 5 # 기본값 5

            if analysis_count >= max_retry_attempts:
                cursor.execute("UPDATE daily_db_project_files SET result = 'Failed' WHERE id = %s", (file_id,))
                conn.commit()
                print(f"      File {file_id} state updated to 'Failed' due to max retry attempts.")
            else:
                print(f"      File {file_id} still in progress. Analysis count: {analysis_count}/{max_retry_attempts}")
                # 이 경우는 아직 진행 중이므로 메시지를 추가하지 않습니다.

    def check_and_update_all_projects_state(self, conn, cursor):
        # 8. daily_db_project_files에서 project id의 가장 마지막 배치의 queued의 갯수가 0인 프로젝트들이 있다면, project의 state를 done으로 바꾼다.
        print("    Checking and updating states for all projects...")
        cursor.execute("""
            UPDATE daily_db_projects dp
            SET dp.state = 'done'
            WHERE (dp.state = 'init' OR dp.state = 'doing')
              AND NOT EXISTS (
                SELECT 1
                FROM daily_db_project_files dpf
                WHERE dpf.prj_id = dp.id
                  AND dpf.batch = dp.batch
                  AND dpf.result = 'Queued'
              );
        """)
        updated_rows = cursor.rowcount
        conn.commit()
        if updated_rows > 0:
            print(f"    Updated {updated_rows} project(s) state to 'done'.")
        else:
            print("    No projects needed state update.")

# 서비스 시작 예시 (app.py 등에서 호출)
# if __name__ == "__main__":
#     service = BackgroundService()
#     service.start()
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         service.stop()
#         service.join()
#         print("Background service stopped.")

find_flaw_prompt = """**[INSTRUCTION]**
You are a **Security Expert** or a **Senior Developer**. Analyze the source code provided below and identify the **most critical or severe security/logic issue**.

**[SOURCE CODE]**
The source code for analysis is provided below. Please clearly distinguish where the code begins and ends.

--- START_CODE: [Source Filename/Path \'{filepath}\'] ---
```
{source_code}
```
--- END_CODE ---

[REQUEST 1: ISSUE ANALYSIS] For the critical issue you find, please provide a detailed explanation covering the following three points:
Issue Summary: (A concise one-sentence description)
Vulnerability/Problem Type: (e.g., SQL Injection, Null Pointer Dereference, Race Condition, etc.)
Impact and Severity: (The worst-case scenario and severity level resulting from this flaw)

[Response Format]
Respond in the following JSON format:
{{
    "issue_analysis": {{
        "issue_summary": "...",
        "vulnerability_type": "...",
        "impact_and_severity": "..."
    }}
}}
"""
get_patch_prompt = """**[INSTRUCTION]**
You are a **Security Expert** or a **Senior Developer**. Analyze the source code provided below and identify the **most critical or severe security/logic issue**.

**[SOURCE CODE]**
The source code for analysis is provided below. Please clearly distinguish where the code begins and ends.

--- START_CODE: [Source Filename/Path \'{filepath}\'] ---
```
{source_code}
```
--- END_CODE ---

[REQUEST 1: PATCH] You gave us a patch like below, but we face some issues when applying it.
Please when you give another patch us, please consider previous patch error. If empty text is given, it means it is the first trial.

--- Previous Patch History ---
{previous_patch}
--- End of Previous Patch ---
--- Patch Problem Description ---
{patch_problem_description}
--- End of Patch Problem Description ---

[REQUEST 2: PATCH GENERATION] Please generate the patch content required to resolve the critical issue identified above. 
The output must be strictly in the Unified Format Patch (diff -u style), clearly showing the changes.
If no patch is needed, respond patch variable with "No patch needed."

[REQUEST 3: PATCH EXPLANATION] Please provide what kind of issue does this patch resolve. And explain why this patch is necessary.

[Response Format]
Respond in the following JSON format:
{{
    "explanation": "...",
    "patch": "...",
}}
"""
