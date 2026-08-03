"""
Pruebas de Integración y Endpoints para el Backend FastAPI (app/main.py).
Utiliza TestClient de FastAPI para simular peticiones HTTP sin necesidad de levantar el servidor web real.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ==============================================================================
# 1. PRUEBAS DE SALUD Y VERSIÓN DE LA API
# ==============================================================================

def test_api_version_endpoint():
    """
    CASO COMÚN: Verificar que el endpoint de salud/versión /api/version retorne HTTP 200
    y devuelva el número de versión correcto del backend.
    """
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert isinstance(data["version"], str)


# ==============================================================================
# 2. PRUEBAS DE RUTAS Y CORD / CABECERAS (edge cases)
# ==============================================================================

def test_non_existent_route_returns_404():
    """
    / ERROR: Petición a una ruta no registrada.
    Debe responder con un estado HTTP 404 Not Found estandarizado.
    """
    response = client.get("/api/endpoint_inexistente_123")
    assert response.status_code == 404