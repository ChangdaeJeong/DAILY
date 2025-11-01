from flask import Flask, render_template
from flask import Flask, render_template
import mysql_db

app = Flask(__name__)

@app.before_first_request
def initialize_db_pool():
    mysql_db.create_db_pool()


@app.route('/')
def loading():
    return render_template('loading.html')

@app.route('/index')
def index():
    conn = mysql_db.get_connection_from_pool()
    if conn:
        # Perform database operations here
        # For example: cursor = conn.cursor(); cursor.execute("SELECT 1"); result = cursor.fetchone(); print(result)
        mysql_db.close_db_pool_connection(conn) # Return connection to the pool
    return render_template('index.html')

@app.route('/request')
def request_page():
    return render_template('request.html')

@app.route('/report')
def report():
    return render_template('report.html')

if __name__ == '__main__':
    app.run(debug=True)
