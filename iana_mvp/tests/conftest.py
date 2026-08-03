"""
Fichero de configuración global de Pytest y Fixtures compartidas.
Este archivo prepara datos temporales y mocks para que las pruebas corran
de forma aislada, rápida y sin depender de conexión a internet o servicios externos.
"""

import os
import tempfile
import pytest
import fitz  # PyMuPDF


@pytest.fixture
def temp_dir():
    """Crea un directorio temporal limpio para cada prueba y lo elimina al finalizar."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_pdf(temp_dir):
    """
    Crea un archivo PDF sintético en memoria/disco con contenido controlado
    para probar la extracción de texto sin requerir archivos reales.
    """
    pdf_path = os.path.join(temp_dir, "documento_prueba.pdf")
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((50, 100), "PROYECTO DE ARQUITECTURA RESIDENCIAL")
    page1.insert_text((50, 150), "Ancho libre de puerta principal: 90 cm según norma OGUC 4.1.7")
    page1.insert_text((50, 200), "Rampa de acceso minusválidos con pendiente de 8%")
    page2 = doc.new_page()
    page2.insert_text((50, 100), "Detalle de pasillos y accesibilidad universal")
    page2.insert_text((50, 150), "Puerta secundaria con ancho 0.90 m")
    
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture
def empty_pdf(temp_dir):
    """Crea un PDF sin texto (página en blanco) para probar casos al límite (edge cases)."""
    pdf_path = os.path.join(temp_dir, "pdf_vacio.pdf")
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture
def sample_rules():
    """Reglas OGUC sintéticas para probar el motor de reglas."""
    return [
        {
            "id": "RULE_001",
            "title": "Verificación de Accesibilidad Universal",
            "type": "keyword_any",
            "keywords": ["accesibilidad", "minusválidos", "rampa"],
            "severity": "alta",
            "norm_ref": "Art. 4.1.7 OGUC"
        },
        {
            "id": "RULE_002",
            "title": "Ancho Mínimo de Puerta de Acceso",
            "type": "door_width",
            "severity": "media",
            "norm_ref": "Art. 4.1.7 OGUC"
        },
        {
            "id": "RULE_003",
            "title": "Superficie de Estacionamientos",
            "type": "regex",
            "pattern": r"estacionamiento\s+de\s+\d+\s*m2",
            "severity": "baja",
            "norm_ref": "Art. 2.4.2 OGUC"
        }
    ]


@pytest.fixture
def sample_report_data():
    """Estructura de resultado de análisis representativa de la base de datos/JSON."""
    return {
        "job_id": "job_test_12345",
        "filename": "Plano_Arquitectura_v1.pdf",
        "project_name": "Edificio Residencial Don Pedro",
        "user_id": "user_abc_789",
        "status": "COMPLETED",
        "success_probability": 85.5,
        "observaciones": "Edificio de 5 pisos con destino residencial.",
        "summary_notes": "El proyecto cumple mayoritariamente con la normativa OGUC de accesibilidad.",
        "infracciones": [
            {
                "articulo": "Art. 4.1.7",
                "descripcion": "Ancho de pasillo registrado como 1.10m en plano, se requiere mínimo 1.20m.",
                "gravedad": "ALTA",
                "pagina": 1
            }
        ]
    }