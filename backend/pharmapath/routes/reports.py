from flask import Blueprint, jsonify, request

from pharmapath.core.auth import auth_required
from pharmapath.services.report_service import ReportService


reports_bp = Blueprint("reports", __name__)


@reports_bp.post("/generate")
@auth_required
def generate_report():
    payload = request.get_json(force=True)
    return jsonify(ReportService().generate(payload)), 201


@reports_bp.get("/<report_id>")
@auth_required
def get_report(report_id: str):
    report = ReportService().get(report_id)
    if report is None:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report)


@reports_bp.get("")
@auth_required
def list_reports():
    patient_id = request.args.get("patient_id")
    return jsonify(ReportService().list(patient_id))

