from flask import Flask
from router import main_bp
from flask_bcrypt import Bcrypt
import lib.inject as inject
import lib.mysql_db as mysql_db

app = Flask(__name__)
app.secret_key = 'D.A.I.L.Y_Secret_Key_v1.0'

app.before_first_request(mysql_db.create_db_pool)
app.before_first_request(lambda: setattr(app, 'bcrypt', Bcrypt(app)))
app.before_request(inject.check_login_status)

app.context_processor(inject.user)
app.context_processor(inject.sidebar_data)

app.register_blueprint(main_bp)
if __name__ == '__main__':
    app.run(debug=True)
