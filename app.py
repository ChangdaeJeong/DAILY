from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def loading():
    return render_template('loading.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/request')
def request_page():
    return render_template('request.html')

@app.route('/report')
def report():
    return render_template('report.html')

if __name__ == '__main__':
    app.run(debug=True)
