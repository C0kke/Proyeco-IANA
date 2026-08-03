"""
Pruebas de Interfaz de Usuario / Frontend (Streamlit AppTest & Dashboard components).
Utiliza el framework oficial streamlit.testing.v1.AppTest y unit tests directos
para verificar la carga correcta del frontend y sus módulos sin NameError.
"""

import pytest
from streamlit.testing.v1 import AppTest
from components.project_dashboard import determine_dom_form, DOM_FORMS_CATALOG, get_form_pdf_bytes, display_results


# ==============================================================================
# 1. PRUEBAS DE INICIALIZACIÓN DE LA APLICACIÓN STREAMLIT
# ==============================================================================

def test_streamlit_app_initialization():
    """
    CASO COMÚN: Verificar que la aplicación de Streamlit se inicie correctamente,
    configure la página y cargue las claves por defecto en session_state.
    """
    at = AppTest.from_file("streamlit_app.py", default_timeout=10)
    at.run(timeout=10)
    
    # Verificar que el session_state se haya inicializado con los valores por defecto
    assert at.session_state["user"] is None
    assert at.session_state["active_tab"] == "Validar Nuevo Documento"
    assert at.session_state["file_uploader_key"] == "file_uploader_v1"
    
    # Al no haber usuario autenticado, debe mostrar el componente de autenticación (Auth)
    assert not at.exception


# ==============================================================================
# 2. PRUEBAS DE IMPORTACIÓN Y DISPONIBILIDAD DE DOM FORMS EN DASHBOARD
# ==============================================================================

def test_project_dashboard_dom_form_imports():
    """
    CASO COMÚN: Verificar que los componentes de DOM Forms estén disponibles a nivel global
    en el módulo project_dashboard sin lanzar NameError durante la validación de un archivo.
    """
    assert callable(determine_dom_form)
    assert isinstance(DOM_FORMS_CATALOG, dict)
    assert callable(get_form_pdf_bytes)
    
    res = determine_dom_form({"name": "Test Project"}, "Obra nueva de vivienda")
    assert "form_id" in res
    assert "pdf_filename" in res