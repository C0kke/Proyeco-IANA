"""
Pruebas Unitarias para Utilidades del Dashboard de Proyectos (project_dashboard.py).
Prueba funciones helper de deduplicación de nombres de archivo y sanitización de datos.
"""

import pytest
from components.project_dashboard import is_duplicate_or_copy_name


# ==============================================================================
# 1. PRUEBAS DE DEDUPLICACIÓN DE NOMBRES (is_duplicate_or_copy_name)
# ==============================================================================

@pytest.mark.parametrize("name1, name2, expected", [
    # CASOS COMUNES
    ("Plano_Estructuras.pdf", "Plano_Estructuras.pdf", True),
    ("Plano_Estructuras.pdf", "plano_estructuras.pdf", True),  # Mayúsculas / minúsculas
    ("Plano_Estructuras (1).pdf", "Plano_Estructuras.pdf", True),  # Sufijo Windows (1)
    ("Plano_Estructuras - copia.pdf", "Plano_Estructuras.pdf", True),  # Sufijo Windows - copia
    ("Plano_Estructuras_1.pdf", "Plano_Estructuras.pdf", True),  # Sufijo _1
    
    # CASOS DISTINTOS (Debe retornar False)
    ("Plano_Estructuras.pdf", "Plano_Arquitectura.pdf", False),
    ("Plano_v1.pdf", "Plano_v2.pdf", False),
    
    # EDGE CASES (Nombres con puntos múltiples o extensiones mezcladas)
    ("informe.final.doc.pdf", "informe.final.doc (1).pdf", True),
])
def test_is_duplicate_or_copy_name(name1, name2, expected):
    """
    Verifica que la función identifique correctamente duplicados ignorando mayúsculas,
    extensiones y sufijos comunes de duplicados creados por el sistema operativo.
    """
    assert is_duplicate_or_copy_name(name1, name2) == expected