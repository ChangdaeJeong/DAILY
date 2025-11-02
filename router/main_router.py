from flask import render_template
from . import main_bp
import mysql_db

@main_bp.route('/')
def index():
    conn = mysql_db.get_conn()
    if conn:
        mysql_db.close_conn(conn)
    return render_template('main/index.html')

@main_bp.route('/loading')
def loading():
    return render_template('main/loading.html')
