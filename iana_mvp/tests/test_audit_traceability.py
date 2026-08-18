"""
Pruebas unitarias para el modelo de Auditoría y Trazabilidad Normativa (RuleCheck).
"""

from app.ai_verifier import RuleCheck, ConsolidatedProjectEvaluation, DocumentSpecificAnalysis


def test_rule_check_model_creation():
    rc = RuleCheck(
        rule_id="Art. 4.1.7 OGUC",
        category="Accesibilidad y Puertas",
        element_inspected="Puerta principal de acceso",
        evidence_found="Cota 0.90 m en lámina A-01",
        document_source="Plano de arquitectura",
        status="CUMPLE",
        detection_method="Ciencia de Datos (Regex / NLP)",
        technical_rationale="El vano cumple con el ancho mínimo libre exigido."
    )
    assert rc.rule_id == "Art. 4.1.7 OGUC"
    assert rc.status == "CUMPLE"
    assert rc.detection_method == "Ciencia de Datos (Regex / NLP)"
    
    dumped = rc.model_dump()
    assert dumped["status"] == "CUMPLE"
    assert dumped["detection_method"] == "Ciencia de Datos (Regex / NLP)"


def test_consolidated_evaluation_with_inspected_rules():
    rc1 = RuleCheck(
        rule_id="Art. 4.1.7 OGUC",
        category="Accesibilidad y Puertas",
        element_inspected="Puerta principal de acceso",
        evidence_found="Cota 0.90 m",
        document_source="Plano de arquitectura",
        status="CUMPLE",
        detection_method="Ciencia de Datos (Regex / NLP)",
        technical_rationale="Conforme."
    )
    rc2 = RuleCheck(
        rule_id="PRC Coquimbo - ZU-4",
        category="Zonificación y Alturas",
        element_inspected="Altura máxima",
        evidence_found="12 m proyectados vs 18 m máx",
        document_source="Cálculo Paramétrico PRC",
        status="CUMPLE",
        detection_method="Motor Determinista PRC",
        technical_rationale="Altura conforme a la zona ZU-4."
    )
    eval_cons = ConsolidatedProjectEvaluation(
        consolidated_context="Proyecto habitacional.",
        is_valid_project_documentation=True,
        consolidated_infractions=[],
        success_probability=100.0,
        extracted_metadata=[],
        inspected_rules=[rc1, rc2]
    )
    assert len(eval_cons.inspected_rules) == 2
    assert eval_cons.inspected_rules[0].status == "CUMPLE"
    assert eval_cons.inspected_rules[1].detection_method == "Motor Determinista PRC"
