from flask import Flask
from flask_cors import CORS

from pharmapath.config import Config
from pharmapath.db.schema import initialize_database
from pharmapath.routes import register_blueprints


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    initialize_database(app.config["DATABASE_PATH"])
    register_blueprints(app)

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "pharmapath-api"}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

