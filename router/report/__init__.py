from flask import render_template, Blueprint
import mysql_db

report_bp = Blueprint('report', __name__)

@report_bp.route('/')
def report_page():
    return render_template('report.html')
