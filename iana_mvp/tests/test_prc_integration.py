"""
Pruebas unitarias para la integración del Plan Regulador Comunal (PRC)
y la Ordenanza Local por Comuna y Región.
"""

from knowledge.prc.registry import (
    get_available_prc_communes,
    get_prc_data,
    get_zone_sheet,
    normalize_zone_code,
    extract_prc_context_for_prompt
)
from app.rules_engine import evaluate_prc_numeric_rules


def test_get_available_prc_communes():
    communes = get_available_prc_communes()
    assert len(communes) >= 1
    coquimbo = next((c for c in communes if c["commune"] == "Coquimbo"), None)
    assert coquimbo is not None
    assert coquimbo["zones_count"] >= 30


def test_get_prc_data_coquimbo():
    data = get_prc_data("Región de Coquimbo", "Coquimbo")
    assert data is not None
    assert data["commune"] == "Coquimbo"
    assert "zones" in data
    assert "ZU3" in data["zones"]
    assert "ZU4" in data["zones"]
    assert "ZU5" in data["zones"]


def test_normalize_zone_code():
    assert normalize_zone_code("ZU-3") == "ZU3"
    assert normalize_zone_code("zu3") == "ZU3"
    assert normalize_zone_code("ZU-5A") == "ZU5A"
    assert normalize_zone_code("ZU3-A") == "ZU3-A"
    assert normalize_zone_code("ZP-1") == "ZP1"


def test_get_zone_sheet_coquimbo():
    # ZU3: Constructibilidad 4.0, Altura 30m
    zu3 = get_zone_sheet("Región de Coquimbo", "Coquimbo", "ZU-3")
    assert zu3 is not None
    assert zu3["code"] == "ZU3"
    assert zu3["coeficiente_constructibilidad_max"] == 4.0
    assert "30" in str(zu3["altura_maxima"])

    # ZU4: Constructibilidad 3.0, Ocupación 0.7, Altura 18m
    zu4 = get_zone_sheet("Región de Coquimbo", "Coquimbo", "ZU4")
    assert zu4 is not None
    assert zu4["coeficiente_constructibilidad_max"] == 3.0
    assert zu4["coeficiente_ocupacion_suelo_max"] == 0.7


def test_extract_prc_context_for_prompt():
    # Context with specific zone
    ctx = extract_prc_context_for_prompt("Región de Coquimbo", "Coquimbo", "ZU-3")
    assert "PLAN REGULADOR COMUNAL DE COQUIMBO" in ctx
    assert "ZONA ZU3" in ctx
    assert "Coeficiente máximo de constructibilidad: 4.0" in ctx

    # Context without specific zone (general list)
    ctx_gen = extract_prc_context_for_prompt("Región de Coquimbo", "Coquimbo", None)
    assert "PLAN REGULADOR COMUNAL DE COQUIMBO" in ctx_gen
    assert "Zonas principales" in ctx_gen


def test_evaluate_prc_numeric_rules_pass():
    # In ZU4: max constructibility = 3.0, max ocupacion = 0.7, max altura = 18m
    meta = {
        "superficie_terreno": "500",
        "superficie_construida": "1000", # coef = 2.0 <= 3.0 (PASS)
        "superficie_primer_piso": "300", # ocup = 0.6 <= 0.7 (PASS)
        "altura_maxima": "12", # 12m <= 18m (PASS)
        "zona_prc": "ZU-4"
    }
    findings = evaluate_prc_numeric_rules(meta, "Región de Coquimbo", "Coquimbo")
    assert len(findings) == 3
    for f in findings:
        assert f["status"] == "PASS"


def test_evaluate_prc_numeric_rules_fail():
    # In ZU4: max constructibility = 3.0, max ocupacion = 0.7, max altura = 18m
    meta = {
        "superficie_terreno": "500",
        "superficie_construida": "2000", # coef = 4.0 > 3.0 (FAIL)
        "superficie_primer_piso": "400", # ocup = 0.8 > 0.7 (FAIL)
        "altura_maxima": "25", # 25m > 18m (FAIL)
        "zona_prc": "ZU-4"
    }
    findings = evaluate_prc_numeric_rules(meta, "Región de Coquimbo", "Coquimbo")
    assert len(findings) == 3
    for f in findings:
        assert f["status"] == "FAIL"
        assert f["severity"] == "high"


def test_evaluate_prc_numeric_rules_missing_zone():
    meta = {
        "superficie_terreno": "500",
        "superficie_construida": "1000"
    }
    findings = evaluate_prc_numeric_rules(meta, "Región de Coquimbo", "Coquimbo")
    assert len(findings) == 1
    assert findings[0]["id"] == "PRC_ZONE_MISSING"
    assert findings[0]["status"] == "WARNING"
