from __future__ import annotations

from functools import wraps

from flask import current_app, g, jsonify, request

from pharmapath.core.security import decode_token


def auth_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Missing bearer token"}), 401

        token = header.replace("Bearer ", "", 1)
        payload = decode_token(token, current_app.config["SECRET_KEY"])
        if payload is None:
            return jsonify({"error": "Invalid or expired token"}), 401

        g.current_user = payload
        return view_func(*args, **kwargs)

    return wrapped

