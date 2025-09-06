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

import os

if __name__ == "__main__":
<<<<<<< HEAD
    port = int(os.environ.get("PORT", 8000))  # Render sets PORT automatically
    app.run(host="0.0.0.0", port=port)
  # Run the app on port 5000
=======
    port = int(os.environ.get("PORT", 5000))  # Render gives you PORT env var
    app.run(host="0.0.0.0", port=port)        # Must bind to 0.0.0.0

>>>>>>> 71b9f65755a9d4e9afdc722dc0cd930e55047139
