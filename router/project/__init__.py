from flask import render_template, Blueprint, request, redirect, url_for, session, jsonify
import mysql_db

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
    # 프로젝트 상세 페이지 렌더링 로직 (나중에 구현)
    return f"Project ID: {project_id}"
