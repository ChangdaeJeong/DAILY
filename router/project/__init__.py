import os
import sys
import shutil # shutil 모듈 추가
from flask import current_app, render_template, Blueprint, request, redirect, url_for, session, jsonify
import mysql_db

# run_if.py를 임포트하기 위해 app.py가 있는 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import run_if

project_bp = Blueprint('project', __name__)

@project_bp.route('/create', methods=['GET', 'POST'])
def create_project_page():
    if request.method == 'POST':
        project_name = request.form['project_name']
        project_path = request.form['project_path']
        interface_script = request.form['interface_script']

        user = session.get('user', {}).get('user', {})
        if not user:
            return jsonify(success=False, msg="로그인된 사용자 정보를 찾을 수 없습니다."), 401
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
            return jsonify(success=True, redirect_url=url_for('main.project.view_project', project_id=project_id))
        except Exception as e:
            return jsonify(success=False, msg=f"프로젝트 생성 중 오류 발생: {e}"), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                mysql_db.close_conn(conn)
    return render_template('project/create.html')

@project_bp.route('/delete/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    conn = None
    cursor = None
    user_data = session.get('user', {})
    logged_in_user_id = user_data.get('user', {}).get('id')

    if not logged_in_user_id:
        return jsonify(success=False, msg="로그인이 필요합니다."), 401

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
def update_if_script(project_id):
    conn = None
    cursor = None
    user_data = session.get('user', {})
    logged_in_user_id = user_data.get('user', {}).get('id')
    if_script_content = request.json.get('if_script')

    if not logged_in_user_id:
        return jsonify(success=False, msg="로그인이 필요합니다."), 401
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
def check_project_name():
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

@project_bp.route('/<int:project_id>')
def view_project(project_id):
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
            return redirect(url_for('main.project.init_project_page', project_id=project_id))
        return render_template('project/detail.html', project=project, files=files) # detail.html은 나중에 구현
    except Exception as e:
        print(f"Error fetching project details: {e}")
        return "Error loading project details", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)

@project_bp.route('/init/<int:project_id>', methods=['GET'])
def init_project_page(project_id):
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
            return redirect(url_for('main.project.view_project', project_id=project_id))
    except Exception as e:
        print(f"Error fetching project details: {e}")
        return "Error loading project details", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)

@project_bp.route('/init/step', methods=['POST'])
def initialize_project():
    conn = None
    cursor = None
    user_data = session.get('user', {})
    logged_in_user_id = user_data.get('user', {}).get('id')
    project_id = request.json.get('project_id') # project_id를 data로 받음
    step = request.json.get('step', 0) # step 데이터 추가 (기본값 0)

    if not logged_in_user_id:
        return jsonify(success=False, msg="로그인이 필요합니다."), 401
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
                return jsonify(success=False, msg=result['msg'])
        elif step == 3: # Project Build
            result = run_if.execute_interface_build(project_root_dir)
            if result['success']:
                return jsonify(success=True, msg="Project Build 완료.", next_step=4)
            else:
                return jsonify(success=False, msg=result['msg'])
        elif step == 4: # Project Run
            result = run_if.execute_interface_run(project_root_dir)
            if result['success']:
                return jsonify(success=True, msg="Project Run 완료.", next_step=5)
            else:
                return jsonify(success=False, msg=result['msg'])
        elif step == 5: # 프로젝트 하위 파일 검색
            full_path = os.path.join('workspace', project_root_dir)
            files_in_project = []
            try:
                for root, _, files in os.walk(full_path):
                    for file in files:
                        relative_path = os.path.relpath(os.path.join(root, file), full_path)
                        files_in_project.append(relative_path)
                return jsonify(success=True, msg="프로젝트 하위 파일 검색 완료.", files=files_in_project, next_step=6)
            except Exception as e:
                return jsonify(success=False, msg=f"프로젝트 하위 파일 검색 중 오류 발생: {e}")
        elif step == 6: # 선택된 파일 서버로 전송
            # selected_files = request.json.get('selected_files', []) # 현재 단계에서는 사용하지 않음
            try:
                # 모든 스텝 완료 후 프로젝트 상태를 'init'으로 변경
                cursor.execute("UPDATE daily_db_projects SET state = 'new' WHERE id = %s", (project_id,))
                conn.commit()
                return jsonify(success=True, msg="선택된 파일 전송 및 프로젝트 초기화 완료!")#, redirect_url=url_for('main.project.view_project', project_id=project_id))
            except Exception as e:
                return jsonify(success=False, msg=f"프로젝트 상태 업데이트 중 오류 발생: {e}")
        else:
            return jsonify(success=False, msg="유효하지 않은 초기화 단계입니다."), 400

    except Exception as e:
        print(f"프로젝트 초기화 중 오류 발생: {e}")
        return jsonify(success=False, msg=f"프로젝트 초기화 중 오류 발생: {e}"), 500

    except Exception as e:
        print(f"프로젝트 초기화 중 오류 발생: {e}")
        return jsonify(success=False, msg=f"프로젝트 초기화 중 오류 발생: {e}"), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            mysql_db.close_conn(conn)
