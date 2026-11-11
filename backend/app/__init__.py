import os

from flask import Flask
from flask_cors import CORS

from .routes import api
from .services.pdf_service import DOCUMENT_STORE
from .services.persistence_service import PersistenceError, init_database, load_documents


def create_app() -> Flask:
    app = Flask(__name__)

    cors_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    try:
        init_database()
        DOCUMENT_STORE.update(load_documents())
    except PersistenceError as exc:
        app.config["PERSISTENCE_STARTUP_ERROR"] = str(exc)

    app.register_blueprint(api, url_prefix="/api")

    return app
