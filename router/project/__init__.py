from flask import render_template, Blueprint
import mysql_db

project_bp = Blueprint('project', __name__)

@project_bp.route('/create')
def create_project_page():
    return render_template('project/create.html')
