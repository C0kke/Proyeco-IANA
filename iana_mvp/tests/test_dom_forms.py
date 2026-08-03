"""
Pruebas Unitarias para el Módulo de Clasificación de Formularios DOM (dom_forms.py).
Prueba la lógica de catálogo, reglas de negocio deterministas y sugerencia por IA.
"""

import pytest
from app.dom_forms import (
    determine_dom_form,
    get_form_by_id,
    get_form_pdf_bytes,
    DOM_FORMS_CATALOG
)


# ==============================================================================
# 1. PRUEBAS DE CATÁLOGO DE FORMULARIOS DOM (DOM_FORMS_CATALOG)
# ==============================================================================

def test_dom_forms_catalog_contains_all_5_phases():
    """CASO COMÚN: Verificar que el catálogo contenga exactamente los 5 formularios (Fases 1 a 5)."""
    assert len(DOM_FORMS_CATALOG) == 5
    for form_id in ["form_1", "form_2", "form_3", "form_4", "form_5"]:
        assert form_id in DOM_FORMS_CATALOG
        form = DOM_FORMS_CATALOG[form_id]
        assert form.pdf_filename.endswith(".pdf")
        assert len(form.applicable_permits) > 0


def test_get_form_pdf_bytes_existing():
    """CASO COMÚN: Comprobar la lectura de bytes de un PDF de formulario existente en knowledge."""
    pdf_bytes = get_form_pdf_bytes("MAPA-FORMULARIOS-OBRAS-MENORES.pdf")
    assert pdf_bytes is not None
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


def test_get_form_pdf_bytes_non_existent():
    """EDGE CASE: Intentar leer un PDF que no existe en la carpeta knowledge."""
    pdf_bytes = get_form_pdf_bytes("FORMULARIO_INEXISTENTE_99.pdf")
    assert pdf_bytes is None


# ==============================================================================
# 2. PRUEBAS DE REGLAS DE DETERMINACIÓN DE FORMULARIO (determine_dom_form)
# ==============================================================================

def test_determine_dom_form_ai_override():
    """CASO COMÚN: La recomendación de la IA tiene prioridad si es válida."""
    res = determine_dom_form(
        project_metadata={"name": "Casa"},
        text_content="Obra nueva de casa",
        ai_recommendation_id="form_1"
    )
    assert res["form_id"] == "form_1"
    assert res["pdf_filename"] == "MAPA-FORMULARIOS-OBRAS-MENORES.pdf"


def test_determine_dom_form_demolition():
    """CASO COMÚN: Proyectos con demolición deben asignar el Formulario 5 (Otras Obras)."""
    res = determine_dom_form(
        project_metadata={"name": "Demolición de galpón"},
        text_content="Se requiere permiso para la demolición total de estructura existente"
    )
    assert res["form_id"] == "form_5"
    assert "demolición" in res["reason"].lower() or "demolicion" in res["reason"].lower()


def test_determine_dom_form_subdivision():
    """CASO COMÚN: Proyectos de subdivisión/fusión asignan Formulario 4."""
    res = determine_dom_form(
        project_metadata={"name": "Subdivisión predial lote A"},
        text_content="Solicitud de subdivisión predial sin obras de urbanización"
    )
    assert res["form_id"] == "form_4"


def test_determine_dom_form_urbanization():
    """CASO COMÚN: Loteos u obras de urbanización asignan Formulario 3."""
    res = determine_dom_form(
        project_metadata={"name": "Loteo DFL 2 con construcción simultánea"},
        text_content="Apertura de calles y loteo con obras de urbanización"
    )
    assert res["form_id"] == "form_3"


def test_determine_dom_form_minor_works_small_surface():
    """CASO COMÚN: Ampliación <= 100m² asigna Formulario 1 (Obras Menores)."""
    res = determine_dom_form(
        project_metadata={"name": "Ampliación vivienda", "superficie": "45m2"},
        text_content="Ampliación en segundo piso de vivienda de 45 m2"
    )
    assert res["form_id"] == "form_1"
    assert "Formulario 1" in res["reason"]


def test_determine_dom_form_major_construction_large_surface():
    """CASO COMÚN: Ampliación > 100m² asigna Formulario 2 (Obras de Edificación)."""
    res = determine_dom_form(
        project_metadata={"name": "Ampliación de mall", "superficie": "250m2"},
        text_content="Ampliación mayor a 100 m2 para nuevo local comercial"
    )
    assert res["form_id"] == "form_2"


def test_determine_dom_form_default_obra_nueva():
    """CASO COMÚN: Proyecto de obra nueva general asigna Formulario 2 por defecto."""
    res = determine_dom_form(
        project_metadata={"name": "Edificio Residencial Don Pedro", "project_type": "private_housing"},
        text_content="Construcción de edificio residencial unifamiliar"
    )
    assert res["form_id"] == "form_2"
    assert res["pdf_filename"] == "MAPA-FORMULARIOS-OBRAS-DE-EDIFICACION.pdf"