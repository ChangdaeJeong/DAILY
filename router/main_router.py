from flask import render_template, redirect, url_for, request, session, jsonify, g
from . import main_bp
from flask import current_app
import mysql_db
from .auth import auth_bp
from .project import project_bp
from .report import report_bp
from lib.decorator import non_static_request # lib.decorator에서 non_static_request import

# 다른 Blueprint들을 main_bp에 등록
main_bp.register_blueprint(auth_bp, url_prefix='/auth')
main_bp.register_blueprint(project_bp, url_prefix='/project')
main_bp.register_blueprint(report_bp, url_prefix='/report')

@main_bp.before_app_request
@non_static_request
def check_login_status():
    # 'main.auth.'로 시작하는 엔드포인트는 auth_bp의 라우트입니다.
    if request.endpoint and request.endpoint.startswith('main.auth.'):
        return

    # 로그인되지 않은 상태에서 GET 요청 시 로그인 페이지로 리다이렉트
    if not session.get('user_uid') and request.method == 'GET':
        return redirect(url_for('main.auth.login'))
    
    # 로그인되지 않은 상태에서 POST 요청 시 JSON 에러 반환
    if not session.get('user_uid') and request.method == 'POST':
        return jsonify(success=False, msg='로그인되지 않았습니다.'), 401

@main_bp.before_app_request
@non_static_request
def inject_sidebar_data():
    g.sidebar_projects_data = {}
    if(session.get('user_uid')):
        logged_in_user_id = session.get('user', {}).get('user', {}).get('id')
        g.sidebar_projects_data = categorized_projects_data(logged_in_user_id)
        print("URL: ", request.url)

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

@main_bp.route('/')
def index():
    return render_template('main/index.html', sidebar_projects_data=g.sidebar_projects_data)

@main_bp.route('/loading')
def loading():
    return render_template('main/loading.html')

@main_bp.route('/get_categorized_projects')
def get_categorized_projects():
    user_uid = session.get('user_uid')
    logged_in_user_id = session.get('user', {}).get('user', {}).get('id')
    
    if not user_uid or not logged_in_user_id:
        return jsonify(doing_projects=[], init_projects=[], done_projects=[], delete_projects=[],
                       has_more_doing=False, has_more_init=False, has_more_done=False, has_more_delete=False,
                       total_doing_projects=0, total_init_projects=0, total_done_projects=0, total_delete_projects=0)

    offsets = {
        'offset_doing': request.args.get('offset_doing', 0, type=int),
        'offset_init': request.args.get('offset_init', 0, type=int),
        'offset_done': request.args.get('offset_done', 0, type=int),
        'offset_delete': request.args.get('offset_delete', 0, type=int)
    }
    
    results = _get_categorized_projects_data(logged_in_user_id, offsets)
    return jsonify(results)
