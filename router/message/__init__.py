from flask import Blueprint, request, jsonify, session
from lib.message import get_messages

message_bp = Blueprint('message', __name__, url_prefix='/message')

@message_bp.route('/get_recent_activities', methods=['GET'])
def get_recent_activities():
    logged_in_user_id = session.get('user', {}).get('user', {}).get('id')

    # TODO: project_id를 어떻게 가져올지 결정해야 함.
    # 현재는 모든 프로젝트의 메시지를 가져오도록 구현.
    # 만약 특정 프로젝트의 메시지만 필요하다면, project_id를 쿼리 파라미터로 받거나 세션에서 가져와야 함.
    project_id = request.args.get('project_id', type=int)
    limit = request.args.get('limit', default=7, type=int)
    offset = request.args.get('offset', default=0, type=int)

    messages = get_messages(user_id=logged_in_user_id, project_id=project_id, limit=limit, offset=offset)

    # created_at datetime 객체를 문자열로 변환
    for msg in messages:
        if 'created_at' in msg and msg['created_at']:
            msg['created_at'] = msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify(messages)
