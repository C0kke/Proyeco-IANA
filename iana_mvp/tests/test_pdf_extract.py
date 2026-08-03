"""
Pruebas Unitarias para el Módulo de Extracción de Texto (pdf_extract.py).
Cubre normalización de texto y extracción de bloques desde PDF y Word (.docx),
incluyendo casos de uso comunes y manejo de errores (edge cases).
"""

import os
import pytest
import fitz
from app.pdf_extract import (
    normalize_text,
    extract_pdf_blocks,
    extract_text_blocks,
    TextBlock
)


# ==============================================================================
# 1. PRUEBAS DE NORMALIZACIÓN DE TEXTO (normalize_text)
# ==============================================================================

def test_normalize_text_common():
    """CASO COMÚN: Limpieza de espacios en blanco y conversión a minúsculas."""
    raw_input = "   PROYECTO    DE  ARQUITECTURA\n\tRESIDENCIAL   "
    expected = "proyecto de arquitectura residencial"
    assert normalize_text(raw_input) == expected


def test_normalize_text_empty():
    """(EDGE CASE): Cadena vacía o solo espacios."""
    assert normalize_text("") == ""
    assert normalize_text("   \n\t  ") == ""


def test_normalize_text_special_characters():
    """CASO COMÚN: Preservación de tildes y caracteres en español."""
    raw_input = "Accesibilidad Mínima del Art. 4.1.7"
    assert normalize_text(raw_input) == "accesibilidad mínima del art. 4.1.7"


# ==============================================================================
# 2. PRUEBAS DE EXTRACCIÓN DE BLOQUES DESDE PDF (extract_pdf_blocks)
# ==============================================================================

def test_extract_pdf_blocks_success(sample_pdf):
    """
    CASO COMÚN: Extracción correcta de bloques de texto y metadatos desde un PDF válido.
    Verifica que retorne objetos TextBlock con número de página, bbox y texto normalizado.
    """
    blocks = extract_pdf_blocks(sample_pdf)
    
    assert len(blocks) > 0
    assert isinstance(blocks[0], TextBlock)
    
    # Verificar que el texto de la página 1 contiene la palabra clave esperada
    first_block = blocks[0]
    assert first_block.page == 1
    assert "PROYECTO DE ARQUITECTURA" in first_block.text
    assert "proyecto de arquitectura" in first_block.text_norm
    assert len(first_block.bbox) == 4


def test_extract_pdf_blocks_empty_pdf(empty_pdf):
    """
    (EDGE CASE): PDF válido pero sin ningún texto en sus páginas.
    Debe retornar una lista vacía sin arrojar excepciones.
    """
    blocks = extract_pdf_blocks(empty_pdf)
    assert blocks == []


def test_extract_pdf_blocks_non_existent_file(temp_dir):
    """
    ERROR: Ruta de archivo no existente.
    PyMuPDF debe lanzar RuntimeError o FileNotFoundError al intentar abrirlo.
    """
    fake_path = os.path.join(temp_dir, "archivo_que_no_existe.pdf")
    with pytest.raises((RuntimeError, FileNotFoundError, fitz.FileDataError)):
        extract_pdf_blocks(fake_path)


# ==============================================================================
# 3. PRUEBAS DE ENRUTAMIENTO (extract_text_blocks)
# ==============================================================================

def test_extract_text_blocks_routing_pdf(sample_pdf):
    """CASO COMÚN: Probar que extract_text_blocks detecta la extensión .pdf y procesa correctamente."""
    blocks = extract_text_blocks(sample_pdf)
    assert len(blocks) >= 2
    assert any("ancho libre de puerta" in b.text_norm for b in blocks)