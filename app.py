from flask import Flask, render_template
from router import main_bp, request_bp, report_bp
import mysql_db

app = Flask(__name__)

@app.before_first_request
def initialize_db_pool():
    mysql_db.create_db_pool()

app.register_blueprint(main_bp)
app.register_blueprint(request_bp, url_prefix='/request')
app.register_blueprint(report_bp, url_prefix='/report')

if __name__ == '__main__':
    app.run(debug=True)
