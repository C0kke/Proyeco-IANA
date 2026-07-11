from __future__ import annotations

import os
import re
import json
from google import genai
import instructor
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

try:
    genai_client = genai.Client(api_key=api_key) if api_key else genai.Client()
    client = instructor.from_genai(genai_client, mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS)
except Exception as e:
    client = None
    print(f"Error inicializando el cliente Gemini: {e}")

class MetadataItem(BaseModel):
    key: str = Field(description="Nombre del parámetro (ej: 'rol_terreno', 'superficie', 'altura_maxima', 'manzana', 'lote', 'comuna', 'region', 'destino_edificacion')")
    value: str = Field(description="Valor del parámetro (ej: '123-45', '450m2', '12 metros', 'Santiago', etc.)")

class Infraction(BaseModel):
    rule_id: str = Field(
        description="Identificador o número de artículo de la OGUC que se infringe o incumple (ej. 'Artículo 4.1.7')"
    )
    description: str = Field(
        description="Descripción detallada de la infracción o incumplimiento normativo detectado"
    )
    severity: str = Field(
        description="Severidad de la infracción: 'ALTA' (falla grave/normativa bloqueante), 'MEDIA' (falla moderada), o 'BAJA' (observación menor)"
    )
    evidence: str = Field(
        description="Texto, dimensión o cota exacta extraída del documento que demuestra el incumplimiento (ej. 'Puerta con ancho de 0.75m')"
    )
    justification: str = Field(
        description="Explicación de lo que exige la OGUC de Chile para este caso y por qué está en falta"
    )


class ProjectEvaluation(BaseModel):
    """Modelo para retrocompatibilidad"""
    project_name: str = Field(
        description="Nombre del proyecto, archivo o plano analizado"
    )
    success_probability: float = Field(
        description="Probabilidad de éxito o viabilidad normativa del proyecto expresada de 0.0 a 100.0"
    )
    infractions: List[Infraction] = Field(
        description="Lista de infracciones o incumplimientos normativos encontrados. Si no hay ninguna, debe ser []"
    )
    summary_notes: str = Field(
        description="Resumen de la evaluación, observaciones generales y recomendaciones clave de viabilidad"
    )


class DocumentSpecificAnalysis(BaseModel):
    """Análisis individual de un documento específico"""
    document_summary: str = Field(
        description="Resumen corto de los aspectos técnicos y constructivos clave expuestos en este documento (máximo 300 palabras)."
    )
    is_valid_architectural_doc: bool = Field(
        description="Indica si el documento subido guarda relación directa con un proyecto de construcción, edificación, arquitectura, especificaciones técnicas de obra, planos, o información catastral (CIP). Si el documento trata de informática, programación, cocina, literatura, leyes no constructivas, o cualquier otro tema no relacionado, debe ser False."
    )
    infractions: List[Infraction] = Field(
        description="Lista de infracciones o incumplimientos de la OGUC encontrados *únicamente* en este archivo. Si no hay, debe ser []"
    )
    extracted_metadata: List[MetadataItem] = Field(
        default_factory=list,
        description="Lista de parámetros catastrales y normativos clave extraídos."
    )


class ConsolidatedProjectEvaluation(BaseModel):
    """Evaluación consolidada acumulativa del proyecto"""
    consolidated_context: str = Field(
        description="Resumen acumulado actualizado del proyecto. Incorpora de forma fluida lo que ya sabíamos con lo aportado por el nuevo documento."
    )
    is_valid_project_documentation: bool = Field(
        description="Indica si toda la documentación acumulada hasta el momento pertenece a un proyecto de edificación real y coherente. Si algún documento no tiene relación (es de informática, etc.), o es incompatible con el tipo de proyecto declarado, debe ser False."
    )
    consolidated_infractions: List[Infraction] = Field(
        description="Lista completa y limpia de alertas e infracciones normativas vigentes para todo el proyecto. Si una alerta previa fue resuelta por la evidencia aportada por el nuevo documento, no la incluyas aquí (resuelves la alerta)."
    )
    success_probability: float = Field(
        description="Probabilidad global de viabilidad normativa del proyecto (0.0 a 100.0) basada en todos los documentos cargados hasta el momento."
    )
    extracted_metadata: List[MetadataItem] = Field(
        default_factory=list,
        description="Lista consolidada que unifica todos los parámetros catastrales y normativos acumulados del proyecto."
    )

def retrieve_relevant_oguc_content(plan_text: str, oguc_text: str, max_tokens_budget: int = 40000) -> str:
    """
    Divide la OGUC en artículos individuales y selecciona aquellos con la mayor cantidad
    de palabras coincidentes (overlap) con el texto provisto.
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

def evaluate_project_with_ai(plan_text: str, oguc_text: str, observaciones: str = "") -> ProjectEvaluation:
    if not client:
        raise ValueError("El cliente de Gemini/Instructor no está inicializado.")

    relevant_oguc = retrieve_relevant_oguc_content(plan_text, oguc_text, max_tokens_budget=40000)

    prompt = (
        "Actúa como un revisor municipal de edificación y analista experto en la OGUC de Chile.\n"
        "Tu tarea es analizar el texto y cotas extraídas de los documentos de un proyecto y compararlas con las exigencias de la OGUC para reportar infracciones.\n\n"
    )
    if observaciones:
        prompt += (
            "--- CONTEXTO ADICIONAL / OBSERVACIONES PROPORCIONADAS POR EL PROYECTISTA ---\n"
            f"{observaciones}\n\n"
        )
    prompt += (
        "--- LEY OFICIAL (ARTÍCULOS SELECCIONADOS DE LA OGUC CHILE) ---\n"
        f"{relevant_oguc}\n\n"
        "--- DATOS EXTRAÍDOS DEL PROYECTO ANALIZADO ---\n"
        f"{plan_text}\n\n"
        "Analiza el proyecto en base a la ley y genera la evaluación en el formato estructurado."
    )

    response: ProjectEvaluation = client.chat.completions.create(
        model="gemini-2.5-flash",
        response_model=ProjectEvaluation,
        messages=[{"role": "user", "content": prompt}],
    )
    return response


def evaluate_document_individually(
    doc_text: str, 
    doc_type: str, 
    oguc_text: str,
    observaciones: str = "",
    pdf_path: Optional[str] = None
) -> DocumentSpecificAnalysis:
    """
    Realiza un análisis individual de un documento específico de acuerdo a su tipo
    (CIP, ETT, site_plan, etc.). Extrae variables, parámetros y alertas locales de la OGUC.
    Soporta análisis visual de planos adjuntando imágenes de páginas de PDF al prompt de Gemini.
    """
    if not client:
        raise ValueError("El cliente de Gemini/Instructor no está inicializado.")

    relevant_oguc = retrieve_relevant_oguc_content(doc_text, oguc_text, max_tokens_budget=30000)

    prompt_text = (
        "Actúa como un revisor normativo experto en edificación de Chile.\n"
        f"Analiza este documento de tipo: '{doc_type}' contra los artículos relevantes de la OGUC.\n\n"
    )
    if observaciones:
        prompt_text += (
            "--- CONTEXTO/OBSERVACIONES DEL PROYECTISTA PARA ESTE DOCUMENTO ---\n"
            f"{observaciones}\n\n"
        )
    prompt_text += (
        "--- LEY OFICIAL (OGUC CHILE) ---\n"
        f"{relevant_oguc}\n\n"
        "--- CONTENIDO DE TEXTO EXTRAÍDO DEL ARCHIVO ---\n"
        f"{doc_text}\n\n"
        "Tu tarea consiste en:\n"
        "1. Generar un resumen técnico del contenido del archivo.\n"
        "2. Identificar infracciones a la OGUC presentes únicamente en este archivo.\n"
        "3. Extraer metadatos claves (ej: 'rol_terreno', 'comuna', 'region', 'superficie_terreno', "
        "'altura_maxima', 'manzana', 'lote', 'constructibilidad', 'ocupacion_suelo') en formato clave-valor.\n"
        "4. Determinar si el documento tiene relación directa con arquitectura, edificación, construcción, planos, ETT, CIP, etc. Si el documento trata de informática, software, cocina, literatura, u otro tema no constructivo, debes marcar is_valid_architectural_doc = False; de lo contrario, True.\n"
    )

    content_list = [prompt_text]

    if pdf_path and os.path.exists(pdf_path) and doc_type in ["site_plan", "sections", "elevations", "cuts"]:
        try:
            import fitz
            from PIL import Image
            import io
            doc = fitz.open(pdf_path)
            max_pages = min(len(doc), 3)
            for page_num in range(max_pages):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(dpi=120)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                content_list.append(img)
            
            # Avisar a la IA que examine las imágenes
            prompt_text += (
                "\n--- ENTRADA MULTIMODAL (IMÁGENES DEL PLANO ADJUNTAS) ---\n"
                "Hemos renderizado y adjuntado las páginas de este plano como imágenes de alta resolución. "
                "Debes analizarlas visualmente con extremo cuidado. Coteja las elevaciones, dibujos de cortes, "
                "líneas, alturas de edificación, distanciamientos y rasantes representados gráficamente, "
                "ya que la extracción de texto plana puede omitir detalles visuales críticos o cotas numéricas del dibujo."
            )
            content_list[0] = prompt_text
        except Exception as img_err:
            print(f"Advertencia al renderizar imágenes del PDF para la IA: {img_err}")

    response: DocumentSpecificAnalysis = client.chat.completions.create(
        model="gemini-2.5-flash",
        response_model=DocumentSpecificAnalysis,
        messages=[{"role": "user", "content": content_list}],
    )
    return response


def consolidate_project_context(
    project_metadata: Dict[str, Any],
    existing_context: str,
    existing_infractions: List[Dict[str, Any]],
    new_doc_analysis: DocumentSpecificAnalysis,
    oguc_text: str
) -> ConsolidatedProjectEvaluation:
    """
    Toma la información previa del proyecto, las alertas e infracciones vigentes,
    las combina con la ficha de análisis individual del nuevo documento cargado
    y realiza una llamada a Gemini para actualizar y consolidar el estado de viabilidad general.
    Esto permite resolver alertas normativas previas si el nuevo documento aporta la información necesaria.
    """
    if not client:
        raise ValueError("El cliente de Gemini/Instructor no está inicializado.")

    # Convertir las infracciones previas a string legible para el prompt
    existing_infractions_str = json.dumps(existing_infractions, ensure_ascii=False, indent=2)
    new_doc_infractions_str = json.dumps([inf.model_dump() for inf in new_doc_analysis.infractions], ensure_ascii=False, indent=2)

    prompt = (
        "Actúa como un Director de Obras Municipales (DOM) y supervisor de ciberseguridad/revisión normativo de Chile.\n"
        "Debes consolidar el estado actual de un proyecto de edificación tras la adición de un nuevo documento técnico.\n\n"
        "--- METADATOS DEL PROYECTO ---\n"
        f"Nombre del proyecto: {project_metadata.get('name')}\n"
        f"Tipo de proyecto: {project_metadata.get('project_type')}\n"
        f"Ubicación: Comuna de {project_metadata.get('commune')}, Región {project_metadata.get('region')}\n"
        f"Ficha catastral: Rol {project_metadata.get('terrain_rol')}, Manzana {project_metadata.get('block')}, Lote {project_metadata.get('lot')}\n\n"
    )
    
    meta = project_metadata.get("extracted_metadata", {}) or {}
    observations = meta.get("observations", "")
    if observations:
        prompt += (
            "--- CONTEXTO ADICIONAL / OBSERVACIONES DEL PROYECTISTA ---\n"
            f"{observations}\n\n"
        )
        
    new_doc_meta_dict = {item.key: item.value for item in new_doc_analysis.extracted_metadata}
    prompt += (
        "--- CONTEXTO ACUMULADO PREVIO ---\n"
        f"{existing_context}\n\n"
        "--- INFRACCIONES/ALERTAS PENDIENTES PREVIAS ---\n"
        f"{existing_infractions_str}\n\n"
        "--- NUEVO DOCUMENTO INCORPORADO ---\n"
        f"Resumen técnico del nuevo archivo: {new_doc_analysis.document_summary}\n"
        f"Infracciones reportadas por el nuevo archivo: {new_doc_infractions_str}\n"
        f"Metadatos extraídos de este archivo: {json.dumps(new_doc_meta_dict, ensure_ascii=False)}\n\n"
        "--- INSTRUCCIONES ---\n"
        "1. **Actualiza el Contexto Acumulado:** Redacta un texto fluido que integre los nuevos detalles (ej: si el nuevo documento es un plano de cortes y antes solo teníamos la ETT).\n"
        "2. **Resuelve Infracciones Previas:** Analiza si los nuevos datos o el nuevo plano justifican/sanan alguna alerta anterior. Si es así, elimínala de las infracciones consolidadas.\n"
        "3. **Agrega Nuevas Infracciones:** Si el nuevo documento contiene nuevas fallas normativas que no estaban documentadas, agrégalas a la lista.\n"
        "4. **Combina Metadatos:** Unifica los metadatos anteriores con los del nuevo archivo.\n"
        "5. **Estima la Viabilidad y Justifica:** Recalcula el porcentaje de éxito (0.0 a 100.0) de aprobación final municipal. Si is_valid_project_documentation es False, la viabilidad debe ser 0.0. "
        "Cualquier penalización que deje la viabilidad por debajo del 95% debe estar estrictamente justificada por infracciones en la lista. Si penalizas la viabilidad porque el proyecto aún está incompleto (ej. solo se ha subido el CIP pero faltan los planos de arquitectura o elevaciones indispensables), debes añadir obligatoriamente alertas correspondientes a la lista de infracciones (ej: rule_id='Expediente Incompleto', description='Falta cargar el plano de arquitectura para verificar coeficiente de constructibilidad y alturas', severity='MEDIA' o 'BAJA'). Si el expediente está completo y no hay infracciones detectadas, la viabilidad debe ser del 100%.\n"
        "6. **Valida la Documentación del Proyecto:** Si el nuevo documento tiene is_valid_architectural_doc = False o no tiene relación alguna con edificación/construcción de viviendas, debes marcar is_valid_project_documentation = False; de lo contrario, True.\n"
        "7. **También señala puntos buenos en tu análisis, reduciendo la información general del proyecto a una sola linea, dando pie a tener un análisis mayor. \n"
        "8. **Finalmente añade un pequeño punteo sobre qué normas importantes o que la DOM suele aprobar o rechazar más está contemplado en el contexto. \n"
    )

    response: ConsolidatedProjectEvaluation = client.chat.completions.create(
        model="gemini-2.5-flash",
        response_model=ConsolidatedProjectEvaluation,
        messages=[{"role": "user", "content": prompt}],
    )
    return response

def rebuild_project_context(project_id: str, jwt_token: str, oguc_text: str) -> Dict[str, Any]:
    import logging
    logger = logging.getLogger("iana.rebuild")
    
    from app.db import get_supabase_client, update_project_context_db
    
    client_db = get_supabase_client(jwt_token)
    try:
        res = client_db.table("documents").select("*, document_analyses(*)").eq("project_id", project_id).order("uploaded_at", desc=False).execute()
        docs = res.data or []
        
        proj_res = client_db.table("projects").select("*").eq("id", project_id).execute()
        if not proj_res.data:
            return {"success": False, "error": "El proyecto no existe."}
        project = proj_res.data[0]
        
        if not docs:
            reset_data = {
                "consolidated_context": "Proyecto inicializado sin documentos cargados.",
                "consolidated_infractions": [],
                "success_probability": 0.0,
                "extracted_metadata": {},
                "terrain_rol": None,
                "block": None,
                "lot": None
            }
            return update_project_context_db(project_id, reset_data, jwt_token)
            
        consolidated_context = "Proyecto inicializado."
        consolidated_infractions = []
        current_meta = {}
        
        last_success_probability = 100.0
        
        for doc in docs:
            analyses = doc.get("document_analyses", [])
            if not analyses:
                continue
                
            analysis_data = analyses[0]
            db_metadata = analysis_data.get("metadata") or {}
            
            meta_list = [
                MetadataItem(key=k, value=str(v))
                for k, v in db_metadata.items()
                if k not in ["is_valid", "observations"]
            ]
            
            doc_analysis = DocumentSpecificAnalysis(
                document_summary=analysis_data.get("extracted_text_summary", ""),
                is_valid_architectural_doc=db_metadata.get("is_valid", True),
                infractions=[Infraction(**inf) for inf in (analysis_data.get("infractions") or [])],
                extracted_metadata=meta_list
            )
            
            consolidated = consolidate_project_context(
                project_metadata=project,
                existing_context=consolidated_context,
                existing_infractions=consolidated_infractions,
                new_doc_analysis=doc_analysis,
                oguc_text=oguc_text
            )
            
            consolidated_context = consolidated.consolidated_context
            consolidated_infractions = [inf.model_dump() for inf in consolidated.consolidated_infractions]
            
            consolidated_meta_dict = {item.key: item.value for item in consolidated.extracted_metadata}
            current_meta = {**current_meta, **consolidated_meta_dict}
            current_meta["is_valid"] = consolidated.is_valid_project_documentation
            last_success_probability = consolidated.success_probability
            
            obs = db_metadata.get("observations", "")
            if obs:
                current_meta["observations"] = obs
                
        update_res = update_project_context_db(
            project_id=project_id,
            context_data={
                "consolidated_context": consolidated_context,
                "consolidated_infractions": consolidated_infractions,
                "success_probability": last_success_probability,
                "extracted_metadata": current_meta,
                "terrain_rol": current_meta.get("rol_terreno"),
                "block": current_meta.get("manzana"),
                "lot": current_meta.get("lote")
            },
            jwt_token=jwt_token
        )
        return update_res
    except Exception as e:
        logger.error(f"Error al reconstruir el contexto del proyecto: {e}")
        return {"success": False, "error": str(e)}