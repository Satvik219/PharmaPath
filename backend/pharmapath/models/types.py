from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PatientProfile:
    age: int | None = None
    weight_kg: float | None = None
    conditions: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    liver_function: str | None = None
    renal_function: str | None = None


@dataclass
class DrugRecord:
    drug_id: str
    name: str
    generic_name: str
    drug_class: str
    form: str
    half_life: str = ""
    metabolism: str = ""
    max_dose: str = ""
    contraindications: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)

