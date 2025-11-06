from lib.mysql_db import get_conn, close_conn
from mysql.connector import Error

def add_message(project_id, title, message):
    conn = None
    cursor = None
    try:
        conn = get_conn()
        if conn:
            cursor = conn.cursor()
            sql = "INSERT INTO daily_db_messages (project_id, title, message) VALUES (%s, %s, %s)"
            cursor.execute(sql, (project_id, title, message))
            conn.commit()
            print(f"Message added successfully: Project ID={project_id}, Title='{title}', Message='{message}'")
            return True
        else:
            print("Failed to get database connection.")
            return False
    except Error as e:
        print(f"Error adding message to database: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            close_conn(conn)

def get_messages(user_id, project_id=None, limit=7, offset=0):
    conn = None
    cursor = None
    messages = []
    try:
        conn = get_conn()
        if conn:
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT m.id, m.project_id, m.title, m.message, m.created_at
                FROM daily_db_messages m
                JOIN daily_db_projects p ON m.project_id = p.id
                WHERE p.user_id = %s
            """
            params = [user_id]
            if project_id:
                sql += " AND m.project_id = %s"
                params.append(project_id)
            sql += " ORDER BY m.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(sql, tuple(params))
            messages = cursor.fetchall()
            return messages
        else:
            print("Failed to get database connection.")
            return []
    except Error as e:
        print(f"Error fetching messages from database: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            close_conn(conn)
