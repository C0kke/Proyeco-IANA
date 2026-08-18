"""
Pruebas Unitarias para el Motor de Reglas OGUC (rules_engine.py).
Verifica la evaluación lógica de normas respecto al contenido extraído de los planos/documentos.
"""

from app.pdf_extract import TextBlock, normalize_text
from app.rules_engine import run_rules, top_evidence, load_rules


def create_block(page: int, text: str) -> TextBlock:
    return TextBlock(
        page=page,
        bbox=[0, 0, 100, 100],
        text=text,
        text_norm=normalize_text(text)
    )


# ==============================================================================
# 1. PRUEBAS DE EVIDENCIA Y TOP EVIDENCE (top_evidence)
# ==============================================================================

def test_top_evidence_limit():
    """CASO COMÚN: Verificar que top_evidence limita el arreglo al máximo 'k' solicitado."""
    items = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]
    result = top_evidence(items, k=3)
    assert len(result) == 3
    assert result == [{"id": 1}, {"id": 2}, {"id": 3}]


# ==============================================================================
# 2. PRUEBAS DE REGLA KEYWORD_ANY (Palabras Clave)
# ==============================================================================

def test_run_rules_keyword_any_pass(sample_rules):
    """
    CASO COMÚN (PASS): Regla por palabras clave con múltiples coincidencias en distintas páginas.
    Debe retornar estado 'PASS' y confianza alta (>0.8).
    """
    blocks = [
        create_block(1, "Plano de accesibilidad del edificio"),
        create_block(2, "Rampa para uso de minusválidos")
    ]
    # Filtrar solo la regla de keyword_any
    rules = [r for r in sample_rules if r["type"] == "keyword_any"]
    
    findings = run_rules(blocks, rules)
    assert len(findings) == 1
    finding = findings[0]
    assert finding["status"] == "PASS"
    assert finding["confidence"] >= 0.80
    assert len(finding["evidence"]) == 2


def test_run_rules_keyword_any_warning(sample_rules):
    """
    CASO COMÚN (WARNING): Regla por palabras clave con 1 sola mención.
    Debe advertir al usuario para validar el contexto.
    """
    blocks = [
        create_block(1, "Texto general de arquitectura sin palabras clave"),
        create_block(2, "Mención única de accesibilidad aquí")
    ]
    rules = [r for r in sample_rules if r["type"] == "keyword_any"]
    
    findings = run_rules(blocks, rules)
    finding = findings[0]
    assert finding["status"] == "WARNING"
    assert finding["confidence"] == 0.70


def test_run_rules_keyword_any_fail(sample_rules):
    """
    CASO COMÚN (FAIL): Ninguna palabra clave fue encontrada en el documento.
    Debe retornar 'FAIL'.
    """
    blocks = [create_block(1, "Este texto habla de estructura pero nada normativo")]
    rules = [r for r in sample_rules if r["type"] == "keyword_any"]
    
    findings = run_rules(blocks, rules)
    finding = findings[0]
    assert finding["status"] == "FAIL"
    assert finding["confidence"] == 0.50


# ==============================================================================
# 3. PRUEBAS DE REGLA DOOR_WIDTH (Ancho de Puerta)
# ==============================================================================

def test_run_rules_door_width_pass(sample_rules):
    """
    CASO COMÚN (PASS): Varias coincidencias normativas de puertas (e.g., '90 cm', '0.90 m').
    """
    blocks = [
        create_block(1, "Puerta principal de acceso: 90 cm"),
        create_block(2, "Puerta secundaria ancho 0.90 m")
    ]
    rules = [r for r in sample_rules if r["type"] == "door_width"]
    
    findings = run_rules(blocks, rules)
    finding = findings[0]
    assert finding["status"] == "PASS"


def test_run_rules_door_width_unverifiable(sample_rules):
    """
    (EDGE CASE): No se menciona la palabra 'puerta' con el formato numérico.
    Debe retornar 'UNVERIFIABLE'.
    """
    blocks = [create_block(1, "Ventana de ancho 90 cm")]
    rules = [r for r in sample_rules if r["type"] == "door_width"]
    
    findings = run_rules(blocks, rules)
    finding = findings[0]
    assert finding["status"] == "UNVERIFIABLE"


# ==============================================================================
# 4. PRUEBAS DE TIPOS DE REGLA NO SOPORTADOS O VACÍOS
# ==============================================================================

def test_run_rules_unknown_rule_type():
    """
    (EDGE CASE): Regla con tipo desconocido/inválido.
    Debe manejarlo ordenadamente con estado 'UNVERIFIABLE' sin romper el proceso.
    """
    unknown_rule = [
        {
            "id": "RULE_999",
            "title": "Regla experimental futura",
            "type": "future_ai_check",
            "severity": "baja"
        }
    ]
    blocks = [create_block(1, "Cualquier texto")]
    findings = run_rules(blocks, unknown_rule)
    assert findings[0]["status"] == "UNVERIFIABLE"
    assert findings[0]["confidence"] == 0.30


def test_run_rules_empty_blocks(sample_rules):
    """
    (EDGE CASE): Lista de bloques de texto completamente vacía.
    """
    findings = run_rules([], sample_rules)
    assert len(findings) == len(sample_rules)
    for f in findings:
        assert f["status"] in ["FAIL", "UNVERIFIABLE"]