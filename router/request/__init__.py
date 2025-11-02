from flask import render_template, Blueprint
import mysql_db

request_bp = Blueprint('request', __name__)

@request_bp.route('/')
def request_page():
    return render_template('request.html')
