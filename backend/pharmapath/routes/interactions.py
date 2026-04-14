from flask import Blueprint, g, jsonify, request

from pharmapath.core.auth import auth_required
from pharmapath.services.chat_service import ChatService
from pharmapath.services.interaction_service import InteractionService


interaction_bp = Blueprint("interactions", __name__)


@interaction_bp.post("/check")
@auth_required
def check_interactions():
    payload = request.get_json(force=True)
    return jsonify(InteractionService().check_interactions(payload, g.current_user.get("sub", "anonymous")))


@interaction_bp.post("/simulate")
@auth_required
def simulate():
    payload = request.get_json(force=True)
    return jsonify(InteractionService().simulate(payload, g.current_user.get("sub", "anonymous")))


@interaction_bp.post("/chat")
@auth_required
def chat():
    payload = request.get_json(force=True)
    return jsonify(ChatService().chat(payload, g.current_user.get("sub", "anonymous")))


@interaction_bp.post("/alternatives")
@auth_required
def alternatives():
    payload = request.get_json(force=True)
    return jsonify(InteractionService().alternatives(payload))


@interaction_bp.get("/graph")
@auth_required
def graph():
    drugs = [item for item in request.args.get("drugs", "").split(",") if item]
    return jsonify(InteractionService().graph(drugs))


@interaction_bp.get("/severity-levels")
@auth_required
def severity_levels():
    return jsonify(InteractionService().severity_levels())
