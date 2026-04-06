from flask import Blueprint, jsonify, request

from pharmapath.core.auth import auth_required
from pharmapath.services.drug_service import DrugService


drugs_bp = Blueprint("drugs", __name__)


@drugs_bp.get("/search")
@auth_required
def search():
    query = request.args.get("q", "")
    limit = int(request.args.get("limit", 10))
    return jsonify(DrugService().search(query, limit))


@drugs_bp.get("/<drug_id>")
@auth_required
def get_drug(drug_id: str):
    drug = DrugService().get(drug_id)
    if drug is None:
        return jsonify({"error": "Drug not found"}), 404
    return jsonify(drug)


@drugs_bp.get("/<drug_id>/interactions")
@auth_required
def interactions(drug_id: str):
    return jsonify(DrugService().interactions_for(drug_id))

