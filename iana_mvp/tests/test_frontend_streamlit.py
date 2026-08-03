"""
Pruebas de Interfaz de Usuario / Frontend (Streamlit AppTest).
Utiliza el framework oficial streamlit.testing.v1.AppTest para simular
el comportamiento de la interfaz de usuario en Streamlit sin necesidad de un navegador web.
"""

import pytest
from streamlit.testing.v1 import AppTest


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