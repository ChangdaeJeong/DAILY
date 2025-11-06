import os
import shutil
import sys
import re # re 모듈 추가
from flask import current_app, render_template, Blueprint, request, redirect, url_for, session, jsonify
from lib.decorator import require_debug_mode
import lib.mysql_db as mysql_db

# run_if.py를 임포트하기 위해 app.py가 있는 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import run_if

project_bp = Blueprint('project', __name__)

def categorized_projects_data(logged_in_user_id, offsets=None):
    if offsets is None:
        offsets = {}

    conn = None
    cursor = None
    results = {
        'doing_projects': [],
        'init_projects': [],
        'done_projects': [],
        'delete_projects': [],
        'has_more_doing': False,
        'has_more_init': False,
        'has_more_done': False,
        'has_more_delete': False,
        'total_doing_projects': 0,
        'total_init_projects': 0,
        'total_done_projects': 0,
        'total_delete_projects': 0
    }
    
    project_states = {
        'doing': ['doing'],
        'init': ['init', 'new'],
        'done': ['done'],
        'delete': ['delete']
    }
    
    limit = 5 # 각 카테고리별로 가져올 프로젝트 수

    try:
        conn = mysql_db.get_conn()
        cursor = conn.cursor(dictionary=True)

        for category, states in project_states.items():
            offset = offsets.get(f'offset_{category}', 0)
            
            # 총 프로젝트 수 확인
            state_placeholders = ', '.join(['%s'] * len(states))
            count_query = f"SELECT COUNT(*) FROM daily_db_projects WHERE user_id = %s AND state IN ({state_placeholders})"
            cursor.execute(count_query, (logged_in_user_id, *states))
            total_category_projects = cursor.fetchone()['COUNT(*)']

            # 페이지네이션된 프로젝트 데이터 가져오기
            query = f"""
                SELECT
                    p.id,
                    p.name,
                    p.state,
                    p.batch,
                    COALESCE(100 * SUM(CASE WHEN dpf.result != 'Queued' THEN 1 ELSE 0 END) / NULLIF(COUNT(dpf.id), 0), 0) AS progress
                FROM
                    daily_db_projects p
                LEFT JOIN
                    daily_db_project_files dpf ON p.id = dpf.prj_id AND p.batch = dpf.batch
                WHERE
                    p.user_id = %s AND p.state IN ({state_placeholders})
                GROUP BY
                    p.id, p.name, p.state, p.batch
                ORDER BY
                    p.id DESC, p.batch DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (logged_in_user_id, *states, limit, offset))
            projects_data = cursor.fetchall()

            category_list = []
            for project_data in projects_data:
                project = dict(project_data)
                if project['state'] == 'doing':
                    project['progress'] = round(project['progress'], 2)
                else:
                    project['progress'] = None
                category_list.append(project)
            
            results[f'{category}_projects'] = category_list
            results[f'has_more_{category}'] = total_category_projects > offset + len(category_list)
            results[f'total_{category}_projects'] = total_category_projects

    except Exception as e:
        current_app.logger.error(f"Error fetching categorized projects: {e}", exc_info=True)
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)
        return results


@project_bp.route('/get_batch_files/<int:project_id>/<int:batch_num>', methods=['GET'])
def get_batch_files(project_id, batch_num):
    conn = None
    cursor = None
    user_data = session.get('user', {})
    logged_in_user_id = user_data.get('user', {}).get('id')

    try:
        conn = mysql_db.get_conn()
        cursor = conn.cursor(dictionary=True)

        # 프로젝트 소유자 확인
        cursor.execute("SELECT user_id FROM daily_db_projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()

        if not project:
            return jsonify(success=False, msg="프로젝트를 찾을 수 없습니다."), 404

        if project['user_id'] != logged_in_user_id:
            return jsonify(success=False, msg="접근 거부: 이 프로젝트의 소유자가 아닙니다."), 403

        # 해당 배치에 속한 파일 리스트와 분석 상태 가져오기
        cursor.execute("""
            SELECT
                dpf.id AS file_id,
                dpf.filepath,
                dpf.result,
                dpf.flaws,
                GROUP_CONCAT(CONCAT_WS('||', dptfa.flaw_detail, dptfa.patch_msgs, dptfa.execute_type, dptfa.execute_succeed, dptfa.execute_msgs) SEPARATOR '@@') AS analysis_details
            FROM
                daily_db_project_files dpf
            LEFT JOIN
                daily_db_project_task_file_analysis dptfa ON dpf.id = dptfa.file_id
            WHERE
                dpf.prj_id = %s AND dpf.batch = %s
            GROUP BY
                dpf.id, dpf.filepath, dpf.result, dpf.flaws
            ORDER BY
                dpf.filepath
        """, (project_id, batch_num))
        files_data = cursor.fetchall()

        # analysis_details 파싱
        for file_data in files_data:
            if file_data['analysis_details']:
                analysis_list = []
                for detail_str in file_data['analysis_details'].split('@@'):
                    parts = detail_str.split('||')
                    if len(parts) == 5:
                        analysis_list.append({
                            'flaw_detail': parts[0],
                            'patch_msgs': parts[1],
                            'execute_type': parts[2],
                            'execute_succeed': parts[3] == '1', # BOOLEAN으로 변환
                            'execute_msgs': parts[4]
                        })
                file_data['analysis_details'] = analysis_list
            else:
                file_data['analysis_details'] = []

        return jsonify(success=True, files=files_data)

    except Exception as e:
        current_app.logger.error(f"Error fetching batch files: {e}", exc_info=True)
        return jsonify(success=False, msg=f"배치 파일 목록을 가져오는 중 오류 발생: {e}"), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)
    
    return results

@project_bp.route('/get_categorized_projects')
def get_categorized_projects():
    user_uid = session.get('user_uid')
    logged_in_user_id = session.get('user', {}).get('user', {}).get('id')

    offsets = {
        'offset_doing': request.args.get('offset_doing', 0, type=int),
        'offset_init': request.args.get('offset_init', 0, type=int),
        'offset_done': request.args.get('offset_done', 0, type=int),
        'offset_delete': request.args.get('offset_delete', 0, type=int)
    }
    
    results = categorized_projects_data(logged_in_user_id, offsets)
    return jsonify(results)

@project_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        project_name = request.form['project_name']
        # project_path = request.form['project_path']
        project_path = project_name+'/'
        interface_script = request.form['interface_script']

        user = session.get('user', {}).get('user', {})
        user_id = user.get('id')# inject_user에서 user_data['user']에 id가 있음

        conn = None
        cursor = None
        try:
            conn = mysql_db.get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO daily_db_projects (name, user_id, root_dir, if_script, state) VALUES (%s, %s, %s, %s, %s)",
                (project_name, user_id, project_path, interface_script, 'new')
            )
            conn.commit()
            project_id = cursor.lastrowid
            return jsonify(success=True, redirect_url=url_for('main.project.project_detail_page', project_id=project_id))
        except Exception as e:
            return jsonify(success=False, msg=f"프로젝트 생성 중 오류 발생: {e}"), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                mysql_db.close_conn(conn)
    return render_template('project/create.html')

@project_bp.route('/delete/<int:project_id>', methods=['POST'])
def delete(project_id):
    conn = None
    cursor = None
    user_data = session.get('user', {})
    logged_in_user_id = user_data.get('user', {}).get('id')

    try:
        conn = mysql_db.get_conn()
        cursor = conn.cursor(dictionary=True)

        # 프로젝트 소유자 확인
        cursor.execute("SELECT user_id FROM daily_db_projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()

        if not project:
            return jsonify(success=False, msg="프로젝트를 찾을 수 없습니다."), 404

        if project['user_id'] != logged_in_user_id:
            return jsonify(success=False, msg="접근 거부: 이 프로젝트의 소유자가 아닙니다."), 403

        # 프로젝트 상태를 'delete'로 변경
        cursor.execute("UPDATE daily_db_projects SET state = 'delete' WHERE id = %s", (project_id,))
        conn.commit()

        return jsonify(success=True, msg="프로젝트가 성공적으로 삭제되었습니다.")

    except Exception as e:
        print(f"프로젝트 삭제 중 오류 발생: {e}")
        return jsonify(success=False, msg=f"프로젝트 삭제 중 오류 발생: {e}"), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)

@project_bp.route('/update/<int:project_id>', methods=['POST'])
def update(project_id):
    conn = None
    cursor = None
    user_data = session.get('user', {})
    logged_in_user_id = user_data.get('user', {}).get('id')
    if_script_content = request.json.get('if_script')

    if not if_script_content:
        return jsonify(success=False, msg="업데이트할 스크립트 내용이 없습니다."), 400

    try:
        conn = mysql_db.get_conn()
        cursor = conn.cursor(dictionary=True)

        # 프로젝트 소유자 확인
        cursor.execute("SELECT user_id FROM daily_db_projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()

        if not project:
            return jsonify(success=False, msg="프로젝트를 찾을 수 없습니다."), 404

        if project['user_id'] != logged_in_user_id:
            return jsonify(success=False, msg="접근 거부: 이 프로젝트의 소유자가 아닙니다."), 403

        # if_script 업데이트
        cursor.execute("UPDATE daily_db_projects SET if_script = %s WHERE id = %s", (if_script_content, project_id))
        conn.commit()

        return jsonify(success=True, msg="인터페이스 스크립트가 성공적으로 업데이트되었습니다.")

    except Exception as e:
        print(f"인터페이스 스크립트 업데이트 중 오류 발생: {e}")
        return jsonify(success=False, msg=f"인터페이스 스크립트 업데이트 중 오류 발생: {e}"), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)

@project_bp.route('/check_project_name', methods=['POST'])
def check_name():
    project_name = request.json.get('project_name')
    if not project_name:
        return jsonify(exists=False, msg="프로젝트 이름을 입력해주세요.")

    conn = None
    cursor = None
    try:
        conn = mysql_db.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daily_db_projects WHERE name = %s", (project_name,))
        count = cursor.fetchone()[0]
        if count > 0:
            return jsonify(exists=True, msg="이미 존재하는 프로젝트 이름입니다.")
        else:
            return jsonify(exists=False, msg="사용 가능한 프로젝트 이름입니다.")
    except Exception as e:
        return jsonify(exists=True, msg=f"이름 확인 중 오류 발생: {e}"), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)

@project_bp.route('/detail/<int:project_id>')
def detail_page(project_id):
    conn = None
    cursor = None
    project = None
    files = []
    user_data = session.get('user', {}) # app.py의 inject_user에서 user_data를 가져옴
    logged_in_user_id = user_data.get('user', {}).get('id')

    try:
        conn = mysql_db.get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM daily_db_projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()

        if not project:
            return "Project not found", 404
        
        # 프로젝트 소유자 확인
        if project['user_id'] != logged_in_user_id:
            return "Access Denied: You do not own this project.", 403

        if project['state'] == 'new':
            # state가 'new'이고, 로그인된 사용자가 프로젝트 소유자이면 init.html 렌더링
            return redirect(url_for('main.project.init_page', project_id=project_id))
        
        # 프로젝트 진행률 계산 (doing 상태일 경우에만)
        project_progress = 0
        if project['state'] == 'doing':
            cursor.execute("""
                SELECT
                    COALESCE(100 * SUM(CASE WHEN dpf.result != 'Queued' THEN 1 ELSE 0 END) / NULLIF(COUNT(dpf.id), 0), 0) AS progress
                FROM
                    daily_db_project_files dpf
                WHERE
                    dpf.prj_id = %s AND dpf.batch = %s
            """, (project_id, project['batch']))
            progress_result = cursor.fetchone()
            if progress_result and progress_result['progress'] is not None:
                project_progress = round(progress_result['progress'], 2)
        project['progress'] = project_progress

        # 배치별 파일 상태 요약 정보 가져오기
        cursor.execute("""
            SELECT
                dpf.batch,
                SUM(CASE WHEN dpf.result = 'Queued' THEN 1 ELSE 0 END) AS queued_count,
                SUM(CASE WHEN dpf.result = 'Completed' THEN 1 ELSE 0 END) AS completed_count,
                SUM(CASE WHEN dpf.result = 'Skipped' THEN 1 ELSE 0 END) AS skipped_count,
                SUM(CASE WHEN dpf.result = 'Failed' THEN 1 ELSE 0 END) AS failed_count,
                COUNT(dpf.id) AS total_files,
                COALESCE(100 * SUM(CASE WHEN dpf.result != 'Queued' THEN 1 ELSE 0 END) / NULLIF(COUNT(dpf.id), 0), 0) AS progress
            FROM
                daily_db_project_files dpf
            WHERE
                dpf.prj_id = %s
            GROUP BY
                dpf.batch
            ORDER BY
                dpf.batch DESC
        """, (project_id,))
        batch_file_status = cursor.fetchall()

        return render_template('project/detail.html', project=project, batch_file_status=batch_file_status)
    except Exception as e:
        current_app.logger.error(f"Error fetching project details: {e}", exc_info=True)
        return "Error loading project details", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)

@project_bp.route('/init/<int:project_id>', methods=['GET'])
def init_page(project_id):
    conn = None
    cursor = None
    user_data = session.get('user', {})
    logged_in_user_id = user_data.get('user', {}).get('id')

    try:
        conn = mysql_db.get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM daily_db_projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()

        if not project:
            return "Project not found", 404
        
        # 프로젝트 소유자 확인
        if project['user_id'] != logged_in_user_id:
            return "Access Denied: You do not own this project.", 403

        if project['state'] == 'new':
            return render_template('project/init.html', project=project)
        else:
            return redirect(url_for('main.project.detail_page', project_id=project_id))
    except Exception as e:
        print(f"Error fetching project details: {e}")
        return "Error loading project details", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)


@project_bp.route('/test/file_modal/<int:project_id>', methods=['GET'])
@require_debug_mode
def test_file_modal(project_id):
    conn = None
    cursor = None
    user_data = session.get('user', {})
    logged_in_user_id = user_data.get('user', {}).get('id')

    try:
        conn = mysql_db.get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM daily_db_projects WHERE id = %s", (project_id,))
        project = cursor.fetchone()

        if not project:
            return "Project not found", 404

        # 프로젝트 소유자 확인
        if project['user_id'] != logged_in_user_id:
            return "Access Denied: You do not own this project.", 403

        return render_template('project/test_file_modal.html', project=project)
    except Exception as e:
        print(f"Error fetching project details: {e}")
        return "Error loading project details", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)

def _get_file_extension(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower()

def _get_filtered_project_files(project_root_dir):
    full_path = os.path.join('workspace', project_root_dir)
    files_in_project = []
    
    excluded_dirs = ['node_modules', 'venv', '__pycache__', '.git', 'dist', 'build', 'static', 'templates', 'router']
    excluded_file_patterns = [r'\.log$', r'\.tmp$', r'\.swp$', r'\.bak$', r'\.gitignore$', r'\.DS_Store$', r'DailyProjectInterface\.py$'] # DailyProjectInterface.py 추가

    try:
        for root, dirs, files in os.walk(full_path):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]

            for file in files:
                relative_path = os.path.relpath(os.path.join(root, file), full_path)
                
                if any(re.search(pattern, relative_path) for pattern in excluded_file_patterns):
                    continue
                
                if _get_file_extension(file) == '':
                    continue

                files_in_project.append(relative_path)
        return files_in_project
    except Exception as e:
        current_app.logger.error(f"프로젝트 파일 목록 필터링 중 오류 발생: {e}", exc_info=True)
        raise e # 예외를 다시 발생시켜 상위 호출자가 처리하도록 함

@project_bp.route('/init/step', methods=['POST'])
def initialize():
    conn = None
    cursor = None
    user_data = session.get('user', {})
    logged_in_user_id = user_data.get('user', {}).get('id')
    project_id = request.json.get('project_id') # project_id를 data로 받음
    step = request.json.get('step', 0) # step 데이터 추가 (기본값 0)

    if not project_id:
        return jsonify(success=False, msg="프로젝트 ID가 필요합니다."), 400

    try:
        conn = mysql_db.get_conn()
        cursor = conn.cursor(dictionary=True)

        # 프로젝트 소유자 확인 및 root_dir, if_script 가져오기
        cursor.execute("SELECT user_id, root_dir, if_script FROM daily_db_projects WHERE id = %s", (project_id,))
        project_data = cursor.fetchone()

        if not project_data:
            return jsonify(success=False, msg="프로젝트를 찾을 수 없습니다."), 404

        if project_data['user_id'] != logged_in_user_id:
            return jsonify(success=False, msg="접근 거부: 이 프로젝트의 소유자가 아닙니다."), 403

        project_root_dir = project_data['root_dir']
        project_if_script = project_data['if_script']

        # step 값에 따라 초기화 로직 진행
        if step == 0: # Workspace 초기화
            full_path = os.path.join('workspace', project_root_dir)
            try:
                if os.path.exists(full_path):
                    shutil.rmtree(full_path)
                os.makedirs(full_path)
                return jsonify(success=True, msg=f"Workspace '{project_root_dir}' 초기화 완료.", next_step=1)
            except Exception as e:
                return jsonify(success=False, msg=f"Workspace 초기화 중 오류 발생: {e}")
        elif step == 1: # Interface 설치
            interface_file_path = os.path.join('workspace', project_root_dir, 'DailyProjectInterface.py')
            try:
                with open(interface_file_path, 'w', encoding='utf-8') as f:
                    f.write(project_if_script)
                return jsonify(success=True, msg="Interface 설치 완료.", next_step=2)
            except Exception as e:
                return jsonify(success=False, msg=f"Interface 설치 중 오류 발생: {e}")
        elif step == 2: # Project Init
            result = run_if.execute_interface_init(project_root_dir)
            if result['success']:
                return jsonify(success=True, msg="Project Init 완료.", next_step=3)
            else:
                return jsonify(success=False, msg=result['msg']+'\n 프로젝트 초기화 실패.', stdout=result['stdout'], stderr=result['stderr'])
        elif step == 3: # Project Build
            result = run_if.execute_interface_build(project_root_dir)
            if result['success']:
                return jsonify(success=True, msg="Project Build 완료.", next_step=4)
            else:
                return jsonify(success=False, msg=result['msg']+'\n 프로젝트 빌드 실패.', stdout=result['stdout'], stderr=result['stderr'])
        elif step == 4: # Project Run
            result = run_if.execute_interface_run(project_root_dir)
            if result['success']:
                return jsonify(success=True, msg="Project Run 완료.", next_step=5)
            else:
                return jsonify(success=False, msg=result['msg']+'\n 프로젝트 실행 실패.', stdout=result['stdout'], stderr=result['stderr'])
        elif step == 5: # 프로젝트 하위 파일 검색
            try:
                files_in_project = _get_filtered_project_files(project_root_dir)
                return jsonify(success=True, msg="프로젝트 하위 파일 검색 완료.", files=files_in_project, next_step=6)
            except Exception as e:
                return jsonify(success=False, msg=f"프로젝트 하위 파일 검색 중 오류 발생: {e}")
        elif step == 6: # 선택된 파일 서버로 전송 및 DB 저장
            selected_files = request.json.get('selected_files', [])
            
            # 1. 클라이언트단에서 전달된 파일 리스트를 받아 각 파일들이 존재하는지 체크
            # _get_filtered_project_files 함수를 사용하여 필터링된 전체 프로젝트 파일 목록을 가져옴
            try:
                all_project_files_filtered = set(_get_filtered_project_files(project_root_dir))
            except Exception as e:
                conn.rollback()
                current_app.logger.error(f"프로젝트 파일 목록 스캔 중 오류 발생: {e}", exc_info=True)
                return jsonify(success=False, msg=f"프로젝트 파일 목록 스캔 중 오류 발생: {e}"), 500

            # 클라이언트에서 전달된 selected_files를 서버에서 다시 필터링
            filtered_selected_files_for_db = []
            for file_path in selected_files:
                # _get_filtered_project_files에서 이미 필터링된 목록에 있는지 확인
                if file_path not in all_project_files_filtered:
                    conn.rollback()
                    return jsonify(success=False, msg=f"파일을 찾을 수 없습니다: {file_path} 또는 필터링 규칙에 의해 제외됨"), 400
                filtered_selected_files_for_db.append(file_path)

            try:
                # 2. transaction 시작 (이미 conn이 트랜잭션 모드이므로 별도 시작 구문 불필요)
                # 3. projects 테이블에서 사용자 id와 project id가 일치하는 레코드의 batch 정보를 +1해서 저장하고, 그 값을 가져온다.
                #    만약 업데이트가 발생하지 않은 경우 (없는 경우) 에러 반환, 롤백
                cursor.execute(
                    "UPDATE daily_db_projects SET batch = batch + 1 WHERE id = %s AND user_id = %s",
                    (project_id, logged_in_user_id)
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return jsonify(success=False, msg="프로젝트를 찾을 수 없거나 소유자가 일치하지 않습니다."), 404
                
                cursor.execute("SELECT batch FROM daily_db_projects WHERE id = %s", (project_id,))
                new_batch = cursor.fetchone()['batch']

                # 4. 가져온 batch 값을 이용하여 daily_db_project_files에 모두 추가한다. 실패하면 rollback
                if filtered_selected_files_for_db: # 필터링된 파일 목록 사용
                    file_insert_query = "INSERT INTO daily_db_project_files (prj_id, batch, filepath, result) VALUES (%s, %s, %s, %s)"
                    file_records = [(project_id, new_batch, file_path, 'Queued') for file_path in filtered_selected_files_for_db]
                    cursor.executemany(file_insert_query, file_records)

                # 5. 작업이 완료되면, projects 테이블에서 state를 init으로 변경한다. 실패하면 rollback
                cursor.execute("UPDATE daily_db_projects SET state = 'init' WHERE id = %s", (project_id,))
                
                # 6. transaction end 및 응답 반환
                conn.commit()
                return jsonify(success=True, msg="선택된 파일 전송 및 프로젝트 초기화 완료!", next_step=7) # next_step 7은 완료를 의미
            except Exception as e:
                conn.rollback()
                current_app.logger.error(f"프로젝트 초기화 중 오류 발생 (step 6): {e}", exc_info=True)
                return jsonify(success=False, msg=f"프로젝트 초기화 중 오류 발생: {e}"), 500
        else:
            return jsonify(success=False, msg="유효하지 않은 초기화 단계입니다."), 400

    except Exception as e:
        current_app.logger.error(f"프로젝트 초기화 중 오류 발생: {e}", exc_info=True)
        return jsonify(success=False, msg=f"프로젝트 초기화 중 오류 발생: {e}"), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)
