"""
Pruebas Unitarias para el Módulo Verificador por IA (ai_verifier.py).
Cubre el procesamiento multimodal de imágenes de planos y el fallback de seguridad.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.ai_verifier import evaluate_document_individually, DocumentSpecificAnalysis


def test_evaluate_document_individually_text_only(mocker):
    """
    CASO COMÚN: Evaluación de documento solo de texto (ej. ETT / Especificaciones Técnicas).
    Verifica que llame a la API con la lista de mensajes sin lanzar excepciones.
    """
    mock_response = DocumentSpecificAnalysis(
        document_summary="Resumen de especificaciones técnicas",
        is_valid_architectural_doc=True,
        infractions=[],
        extracted_metadata=[]
    )
    
    mock_create = mocker.patch("app.ai_verifier.client.chat.completions.create", return_value=mock_response)
    
    res = evaluate_document_individually(
        doc_text="Texto de prueba ETT",
        doc_type="ett",
        oguc_text="Texto OGUC"
    )
    
    assert res.document_summary == "Resumen de especificaciones técnicas"
    assert mock_create.called


def test_evaluate_document_individually_multimodal_pdf(sample_pdf, mocker):
    """
    CASO COMÚN: Evaluación multimodal de un plano PDF (doc_type="sections" o "site_plan").
    Verifica que convierta las páginas del PDF en objetos de imagen InstructorImage y las envíe.
    """
    mock_response = DocumentSpecificAnalysis(
        document_summary="Análisis de plano de arquitectura",
        is_valid_architectural_doc=True,
        infractions=[],
        extracted_metadata=[]
    )
    
    mock_create = mocker.patch("app.ai_verifier.client.chat.completions.create", return_value=mock_response)
    
    res = evaluate_document_individually(
        doc_text="Plano de arquitectura",
        doc_type="sections",
        oguc_text="Texto OGUC",
        pdf_path=sample_pdf
    )
    
    assert res.document_summary == "Análisis de plano de arquitectura"
    assert mock_create.called
    
    # Comprobar que los mensajes enviados al cliente contengan elementos de tipo InstructorImage
    call_args = mock_create.call_args[1]
    messages = call_args["messages"]
    content_list = messages[0]["content"]
    assert len(content_list) > 1  # prompt_text + al menos 1 página de imagen InstructorImage


def test_evaluate_document_individually_multimodal_fallback_on_error(sample_pdf, mocker):
    """
    EDGE CASE / ERROR: Si la llamada multimodal falla por cualquier motivo (ej. incompatibilidad de payload de imagen),
    el sistema debe capturar el error y reintentar de forma transparente solo con el prompt de texto sin romper la ejecución.
    """
    mock_response = DocumentSpecificAnalysis(
        document_summary="Resumen obtenido tras reintento sólo de texto",
        is_valid_architectural_doc=True,
        infractions=[],
        extracted_metadata=[]
    )
    
    # Simular que el primer intento (con imágenes) falla, y el segundo (sólo texto) tiene éxito
    mock_create = mocker.patch(
        "app.ai_verifier.client.chat.completions.create",
        side_effect=[ValueError("Unsupported content item type"), mock_response]
    )
    
    res = evaluate_document_individually(
        doc_text="Plano con error de imagen",
        doc_type="sections",
        oguc_text="Texto OGUC",
        pdf_path=sample_pdf
    )
    
    assert res.document_summary == "Resumen obtenido tras reintento sólo de texto"
    assert mock_create.call_count == 2
