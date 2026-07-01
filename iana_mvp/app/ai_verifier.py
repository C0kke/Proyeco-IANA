from __future__ import annotations

import os
import re
from google import genai
import instructor
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

try:
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
        description="Texto, dimensión o cota exacta extraída del documento que demuestra el incumplimiento (ej. 'Puerta con ancho de 0.75m')"
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


def retrieve_relevant_oguc_content(plan_text: str, oguc_text: str, max_tokens_budget: int = 40000) -> str:
    """
    Divide la OGUC en artículos individuales y selecciona aquellos con la mayor cantidad
    de palabras coincidentes (overlap) con el plano, respetando un presupuesto máximo de tokens.
    """
    pattern = re.compile(r'(?m)^(\*{0,2}Artículo\s+\d+\.\d+\.\d+(?:\s+[Bb]is)?\.?\*{0,2})')
    matches = list(pattern.finditer(oguc_text))
    
    if not matches:
        print("ADVERTENCIA: No se pudieron extraer los artículos de la OGUC mediante expresiones regulares.")
        return oguc_text[:max_tokens_budget * 4]
        
    articles = []
    for i, match in enumerate(matches):
        art_title = match.group(1).replace("*", "").strip()
        start_idx = match.start()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(oguc_text)
        art_content = oguc_text[start_idx:end_idx].strip()
        articles.append((art_title, art_content))
        
    plan_words = set(re.findall(r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{4,}', plan_text.lower()))
    
    stopwords = {
        "para", "como", "este", "esta", "estos", "estas", "con", "del", "las", "los",
        "una", "uno", "unos", "unas", "por", "que", "debe", "deben", "deberá", "deberán",
        "donde", "cuando", "cuyo", "cada", "sino", "pero", "entre", "sobre", "desde",
        "hasta", "hacia", "sino", "quien", "cual", "cuales", "toda", "todo", "todas", "todos",
        "mismo", "misma", "mismos", "mismas", "otro", "otra", "otros", "otras", "algun", "alguna",
        "algunos", "algunas", "caso", "casos", "parte", "partes", "obra", "obras", "edificio",
        "edificios", "artículo", "artículos", "ordenanza", "general", "urbanismo", "construcciones"
    }
    query_words = plan_words - stopwords
    
    scored_articles = []
    for title, content in articles:
        content_lower = content.lower()
        score = sum(1 for word in query_words if word in content_lower)
        scored_articles.append((score, title, content))
        
    scored_articles.sort(key=lambda x: x[0], reverse=True)
    
    char_budget = max_tokens_budget * 4
    selected_content = []
    current_chars = 0
    selected_titles = []
    
    for score, title, content in scored_articles:
        if score == 0 and len(selected_content) >= 5:
            break
            
        content_len = len(content)
        if current_chars + content_len > char_budget:
            if len(selected_content) < 3:
                selected_content.append(content[:char_budget - current_chars])
                selected_titles.append(title)
            break
        selected_content.append(content)
        selected_titles.append(title)
        current_chars += content_len
        
    print(f"Búsqueda semántica local: Seleccionados {len(selected_content)} artículos de la OGUC. Títulos: {selected_titles}")
    return "\n\n---\n\n".join(selected_content)


def evaluate_project_with_ai(plan_text: str, oguc_text: str) -> ProjectEvaluation:
    """
    Envía el texto extraído del plano junto con los artículos relevantes de la OGUC
    a la API de Gemini usando Instructor para recibir una evaluación estructurada.
    """
    if not client:
        raise ValueError(
            "El cliente de Gemini/Instructor no se pudo inicializar. Asegúrate de configurar la variable de entorno GEMINI_API_KEY."
        )

    relevant_oguc = retrieve_relevant_oguc_content(plan_text, oguc_text, max_tokens_budget=40000)

    prompt = (
        "Actúa como un revisor municipal de edificación y analista experto en la Ordenanza General de Urbanismo y Construcción (OGUC) de Chile.\n"
        "Tu tarea es analizar el texto y cotas extraídas de un plano y compararlas con las exigencias del documento legal de la OGUC adjunto para reportar infracciones.\n\n"
        "--- LEY OFICIAL (ARTÍCULOS SELECCIONADOS DE LA OGUC CHILE) ---\n"
        f"{relevant_oguc}\n\n"
        "--- DATOS EXTRAÍDOS DEL PLANO ANALIZADO ---\n"
        f"{plan_text}\n\n"
        "Analiza el plano en base a la ley y genera la evaluación del proyecto en el formato de salida estructurado."
    )

    response: ProjectEvaluation = client.chat.completions.create(
        model="gemini-2.5-flash",
        response_model=ProjectEvaluation,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    return response