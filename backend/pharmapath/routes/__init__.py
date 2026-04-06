from flask import Flask

from pharmapath.routes.auth import auth_bp
from pharmapath.routes.drugs import drugs_bp
from pharmapath.routes.interactions import interaction_bp
from pharmapath.routes.patients import patients_bp
from pharmapath.routes.reports import reports_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(drugs_bp, url_prefix="/api/drugs")
    app.register_blueprint(interaction_bp, url_prefix="/api/interactions")
    app.register_blueprint(patients_bp, url_prefix="/api/patients")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
