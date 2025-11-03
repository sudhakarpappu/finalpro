from flask import Flask # type: ignore

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Needed for sessions and flash

# Import routes *after* creating `app` and `mysql`
from controllers.routes import ulogin
# ... other imports
app.register_blueprint(ulogin, url_prefix='/ulogin')
from controllers import routes
import os
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

