from flask import Flask # type: ignore
from flask_mysqldb import MySQL # type: ignore

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Needed for sessions and flash
# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Sudhan@123'
app.config['MYSQL_DB'] = 'pro'
mysql = MySQL(app)
# Import routes *after* creating `app` and `mysql`
from controllers import routes

if __name__ == '__main__':
    app.run(debug=True)
