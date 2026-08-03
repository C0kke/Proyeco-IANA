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