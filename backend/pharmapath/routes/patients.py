from flask import Blueprint, g, jsonify, request

from pharmapath.core.auth import auth_required
from pharmapath.services.patient_service import PatientService


patients_bp = Blueprint("patients", __name__)


@patients_bp.post("")
@auth_required
def create_patient():
    payload = request.get_json(force=True)
    return jsonify(PatientService().create(payload, g.current_user["tenant_id"])), 201


@patients_bp.get("/<patient_id>")
@auth_required
def get_patient(patient_id: str):
    patient = PatientService().get(patient_id)
    if patient is None:
        return jsonify({"error": "Patient not found"}), 404
    return jsonify(patient)


@patients_bp.put("/<patient_id>")
@auth_required
def update_patient(patient_id: str):
    payload = request.get_json(force=True)
    return jsonify(PatientService().update(patient_id, payload))


@patients_bp.get("/<patient_id>/history")
@auth_required
def patient_history(patient_id: str):
    return jsonify(PatientService().history(patient_id))


@patients_bp.delete("/<patient_id>")
@auth_required
def delete_patient(patient_id: str):
    return jsonify(PatientService().delete(patient_id))

