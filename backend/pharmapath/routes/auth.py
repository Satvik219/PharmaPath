from flask import Blueprint, jsonify, request

from pharmapath.services.auth_service import AuthService


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    try:
        result = AuthService().register(request.get_json(force=True))
        return jsonify(result), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@auth_bp.post("/login")
def login():
    try:
        return jsonify(AuthService().login(request.get_json(force=True)))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401


@auth_bp.post("/refresh")
def refresh():
    payload = request.get_json(force=True)
    return jsonify(AuthService().refresh(payload.get("refresh_token", "")))


@auth_bp.post("/logout")
def logout():
    return jsonify({"success": True})

