from __future__ import annotations

import os
from google import genai
import instructor
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

# Inicializar el cliente de instructor con google-genai
api_key = os.getenv("GEMINI_API_KEY")

try:
    # Si la API Key no está en .env, intentamos leer la del sistema por defecto
    genai_client = genai.Client(api_key=api_key) if api_key else genai.Client()
    client = instructor.from_genai(genai_client)
except Exception as e:
    client = None
    print(f"Error inicializando el cliente Gemini: {e}")


class Infraction(BaseModel):
    rule_id: str = Field(
        description="Identificador o número de artículo de la OGUC que se infringe (ej. 'Artículo 4.1.7')"
    )
    description: str = Field(
        description="Descripción detallada de la infracción o incumplimiento normativo detectado en el plano"
    )
    severity: str = Field(
        description="Severidad de la infracción: 'ALTA' (falla grave/normativa bloqueante), 'MEDIA' (falla moderada), o 'BAJA' (observación menor)"
    )
    evidence: str = Field(
        description="Texto, dimensión o cota exacta extraída del plano que demuestra el incumplimiento (ej. 'Puerta con ancho de 0.75m')"
    )
    justification: str = Field(
        description="Explicación de lo que exige la OGUC de Chile para este caso y por qué el plano está en falta"
    )


class ProjectEvaluation(BaseModel):
    project_name: str = Field(
        description="Nombre del proyecto, archivo o plano analizado"
    )
    success_probability: float = Field(
        description="Probabilidad de éxito o viabilidad normativa del proyecto expresada de 0.0 a 100.0 (porcentaje de cumplimiento)"
    )
    infractions: List[Infraction] = Field(
        description="Lista de infracciones o incumplimientos normativos encontrados. Si no hay ninguna, debe ser una lista vacía []"
    )
    summary_notes: str = Field(
        description="Resumen de la evaluación, observaciones generales y recomendaciones clave de viabilidad para el arquitecto"
    )


def evaluate_project_with_ai(plan_text: str, oguc_text: str) -> ProjectEvaluation:
    """
    Envía el texto extraído del plano junto con el texto de la OGUC
    a la API de Gemini usando Instructor para recibir una evaluación estructurada.
    """
    if not client:
        raise ValueError(
            "El cliente de Gemini/Instructor no se pudo inicializar. Asegúrate de configurar la variable de entorno GEMINI_API_KEY."
        )

    # Construimos un único prompt robusto que junta el contexto de la ley y el plano
    prompt = (
        "Actúa como un revisor municipal de edificación y analista experto en la Ordenanza General de Urbanismo y Construcción (OGUC) de Chile.\n"
        "Tu tarea es analizar el texto y cotas extraídas de un plano y compararlas con las exigencias del documento legal de la OGUC adjunto para reportar infracciones.\n\n"
        "--- LEY OFICIAL (OGUC CHILE) ---\n"
        f"{oguc_text}\n\n"
        "--- DATOS EXTRAÍDOS DEL PLANO ANALIZADO ---\n"
        f"{plan_text}\n\n"
        "Analiza el plano en base a la ley y genera la evaluación del proyecto en el formato de salida estructurado."
    )

    # Ejecutamos la llamada a través de instructor
    response: ProjectEvaluation = client.chat.completions.create(
        model="gemini-2.5-flash",
        response_model=ProjectEvaluation,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    return response
