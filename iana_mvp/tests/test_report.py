"""
Pruebas Unitarias para el Módulo de Reportes (report.py).
Prueba la lógica de clasificación de estado de aprobación (get_status_label)
y el renderizado de informes HTML y PDF.
"""

import pytest
from app.report import get_status_label, render_html_report, render_pdf_report


# ==============================================================================
# 1. PRUEBAS DE CLASIFICACIÓN DE ESTADO (get_status_label)
# ==============================================================================

def test_get_status_label_invalid():
    """CASO COMÚN: Documento marcado como is_valid = False debe rechazarse directamente."""
    result = {"is_valid": False, "success_probability": 90.0, "infractions": []}
    assert get_status_label(result) == "Rechazado (No Válido)"


def test_get_status_label_high_severity():
    """CASO COMÚN: Al menos una infracción de severidad ALTA rechaza el proyecto."""
    result = {
        "is_valid": True,
        "success_probability": 95.0,
        "infractions": [{"severity": "ALTA", "description": "Falta de vías de evacuación"}]
    }
    assert get_status_label(result) == "Rechazado"


def test_get_status_label_reformular():
    """CASO COMÚN: Viabilidad entre 50% y 79% retorna 'Reformular'."""
    result = {
        "is_valid": True,
        "success_probability": 65.0,
        "infractions": [{"severity": "MEDIA", "description": "Detalle menor"}]
    }
    assert get_status_label(result) == "Reformular"


def test_get_status_label_approved():
    """CASO COMÚN: Proyecto sin infracciones y viabilidad alta es 'Aprobado'."""
    result = {
        "is_valid": True,
        "success_probability": 98.0,
        "infractions": []
    }
    assert get_status_label(result) == "Aprobado"


# ==============================================================================
# 2. PRUEBAS DE RENDERIZADO HTML (render_html_report)
# ==============================================================================

def test_render_html_report_success(sample_report_data):
    """
    CASO COMÚN: Renderizado exitoso de reporte HTML con todos sus campos requeridos.
    Verifica que el título del proyecto y archivo aparezcan en el HTML generado.
    """
    html = render_html_report("Plano_v1.pdf", sample_report_data)
    assert isinstance(html, str)
    assert "<!doctype html>" in html
    assert "Plano_Arquitectura_v1.pdf" in html
    assert "Edificio Residencial Don Pedro" in html


def test_render_html_report_missing_optional_fields():
    """
    (EDGE CASE): Reporte donde campos opcionales son None o vacíos.
    No debe lanzar excepciones por Jinja2 y debe manejar valores nulos adecuadamente.
    """
    minimal_data = {
        "filename": "plano_simple.pdf",
        "project_name": "Proyecto Ejemplo",
        "success_probability": 100.0,
        "observaciones": None,
        "summary_notes": "Sin observaciones adicionales.",
        "infractions": []
    }
    html = render_html_report("plano_simple.pdf", minimal_data)
    assert isinstance(html, str)
    assert "¡Proyecto Aprobable!" in html


# ==============================================================================
# 3. PRUEBAS DE RENDERIZADO PDF (render_pdf_report)
# ==============================================================================

def test_render_pdf_report_bytes(sample_report_data):
    """
    CASO COMÚN: Generación de PDF binario válido.
    Verifica que el resultado retorne bytes y comience con el encabezado %PDF.
    """
    pdf_bytes = render_pdf_report("Plano_v1.pdf", sample_report_data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


# ==============================================================================
# 4. PRUEBAS DE ESTILOS CORPORATIVOS Y AUDITORÍA POSITIVA EN HTML
# ==============================================================================

def test_render_html_report_includes_positive_rules(sample_report_data):
    """
    Verifica que el reporte HTML incluya las verificaciones positivas ('✔ CUMPLE')
    y la sección de trazabilidad y auditoría técnica.
    """
    html = render_html_report("Plano_v1.pdf", sample_report_data)
    assert "Auditoría Técnica y Trazabilidad Normativa" in html
    assert "✔ CUMPLE" in html
    assert "Art. 4.1.7 OGUC" in html
    assert "Ciencia de Datos" in html


def test_render_html_report_corporate_styling_tokens(sample_report_data):
    """
    Verifica que el reporte HTML contenga los estilos corporativos acordes a index.css:
    fuentes Orbitron y Raleway, métricas y badges de trazabilidad.
    """
    html = render_html_report("Plano_v1.pdf", sample_report_data)
    assert "Orbitron" in html
    assert "Raleway" in html
    assert "--brand-negro-profundo" in html
    assert "--brand-dorado" in html
    assert "Inspecciones Totales" in html
    assert "Conformes (CUMPLE)" in html


def test_render_html_report_custom_inspected_rules():
    """
    Verifica el renderizado de un conjunto explícito de inspected_rules con conformidades y alertas.
    """
    custom_data = {
        "filename": "casa_alerce.pdf",
        "project_name": "Casa Alerce Calbuco",
        "success_probability": 65.0,
        "observaciones": "Observación de prueba",
        "summary_notes": "Resumen ejecutivo del proyecto.",
        "infractions": [
            {
                "rule_id": "Art. 55 LGUC",
                "description": "Predio en área rural",
                "severity": "ALTA",
                "evidence": "CIP rural",
                "justification": "Exige autorización SEREMI."
            }
        ],
        "inspected_rules": [
            {
                "rule_id": "Art. 55 LGUC",
                "category": "Zonificación",
                "element_inspected": "Predio rural sin informe",
                "evidence_found": "CIP rural",
                "document_source": "Expediente del proyecto",
                "status": "NO CUMPLE",
                "detection_method": "Modelo IANA",
                "technical_rationale": "Debe contar con autorización."
            },
            {
                "rule_id": "Art. 4.1.7 OGUC",
                "category": "Accesibilidad",
                "element_inspected": "Ancho de puerta principal",
                "evidence_found": "0.90 m en lámina A1",
                "document_source": "Plano A1",
                "status": "CUMPLE",
                "detection_method": "Ciencia de Datos (Regex / NLP)",
                "technical_rationale": "Conforme a norma de accesibilidad."
            }
        ]
    }
    html = render_html_report("casa_alerce.pdf", custom_data)
    assert "Casa Alerce Calbuco" in html
    assert "✖ NO CUMPLE" in html
    assert "✔ CUMPLE" in html
    assert "Ancho de puerta principal" in html
    assert "Predio rural sin informe" in html
    assert "65.0%" in html