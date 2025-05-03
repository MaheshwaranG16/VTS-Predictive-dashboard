from flask import Flask
from flask_cors import CORS
from sqlalchemy.orm import scoped_session
from app.config import SessionLocal
from app import routes

app = Flask(__name__)
CORS(app) 
db_session = scoped_session(SessionLocal)

@app.teardown_appcontext
def remove_session(exception=None):
    db_session.remove()

app.register_blueprint(routes.routes)

if __name__ == "__main__":
    app.run(debug=True)