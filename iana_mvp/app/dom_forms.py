from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")


class DOMFormInfo(BaseModel):
    form_id: str = Field(description="Identificador interno del formulario (form_1 a form_5)")
    form_number: int = Field(description="Número de fase/formulario (1 a 5)")
    title: str = Field(description="Título corto del formulario")
    pdf_filename: str = Field(description="Nombre de archivo PDF en la carpeta knowledge")
    category: str = Field(description="Categoría general de obra")
    description: str = Field(description="Descripción de uso principal")
    applicable_permits: List[str] = Field(description="Lista de trámites o permisos que abarca este formulario")


DOM_FORMS_CATALOG: Dict[str, DOMFormInfo] = {
    "form_1": DOMFormInfo(
        form_id="form_1",
        form_number=1,
        title="Formulario N° 1 - Obras Menores",
        pdf_filename="MAPA-FORMULARIOS-OBRAS-MENORES.pdf",
        category="1 - Obras Menores",
        description="Aplica para permisos y declaraciones juradas de obras menores, ampliaciones hasta 100 m², modificaciones no estructurales y regularizaciones.",
        applicable_permits=[
            "Ampliación Hasta 100 m² (Art. 5.1.4 1A OGUC)",
            "Modificación sin alterar su Estructura (Art. 5.1.4 1B OGUC)",
            "Ampliación de Vivienda Social, Progresiva, Sanitaria o hasta 520 UF (Art. 166 LGUC y 5.1.4 2A OGUC)",
            "Regularización de Edificación Antigua (Anterior al 31.07.1959, Art. 5.1.4 2B OGUC)",
            "Proyecto de Radicación (Art. 6.2.9 OGUC)"
        ]
    ),
    "form_2": DOMFormInfo(
        form_id="form_2",
        form_number=2,
        title="Formulario N° 2 - Obras de Edificación",
        pdf_filename="MAPA-FORMULARIOS-OBRAS-DE-EDIFICACION.pdf",
        category="2 - Obras de Edificación",
        description="Aplica para permisos y declaraciones juradas de construcciones principales, obras nuevas, ampliaciones mayores a 100 m² y alteraciones estructurales.",
        applicable_permits=[
            "Obra Nueva (Construcción de edificios, viviendas o recintos nuevos)",
            "Ampliación Mayor a 100 m²",
            "Alteración Estructural",
            "Reparación Estructural",
            "Reconstrucción"
        ]
    ),
    "form_3": DOMFormInfo(
        form_id="form_3",
        form_number=3,
        title="Formulario N° 3 - Obras de Urbanización",
        pdf_filename="Mapa-Formularios-OBRAS-DE-URBANIZACION.pdf",
        category="3 - Obras de Urbanización",
        description="Aplica para proyectos de loteo, urbanización, cesión de espacios públicos y división predial afecta a utilidad pública.",
        applicable_permits=[
            "Loteo y Loteo con Construcción Simultánea (DFL N°2 / General)",
            "División Predial con Afectación a Utilidad Pública y sus Obras",
            "Urbanización de Predios Afectos a Utilidad Pública en Copropiedad Inmobiliaria",
            "Urbanización Voluntaria en Espacio Público Existente",
            "Urbanización y Cesión Voluntaria al Interior de Predio"
        ]
    ),
    "form_4": DOMFormInfo(
        form_id="form_4",
        form_number=4,
        title="Formulario N° 4 - Subdivisiones y Fusión Predial",
        pdf_filename="Mapa-Formularios-SUBVIDISIONES-Y-FUSION-PREDIAL.pdf",
        category="4 - Subdivisiones y Fusión Predial",
        description="Aplica para autorizaciones administrativas de división o unión de predios sin afectación a obras de urbanización.",
        applicable_permits=[
            "Subdivisión Predial",
            "Fusión Predial",
            "Subdivisión y Fusión Simultánea"
        ]
    ),
    "form_5": DOMFormInfo(
        form_id="form_5",
        form_number=5,
        title="Formulario N° 5 - Otras Obras",
        pdf_filename="MAPA-FORMULARIOS-OTRAS-OBRAS.pdf",
        category="5 - Otras Obras",
        description="Aplica para permisos y declaraciones juradas de demolición, obras auxiliares, piscinas privadas y edificaciones complementarias.",
        applicable_permits=[
            "Permiso / Declaración Jurada de Demolición",
            "Declaración Jurada de Obras Auxiliares",
            "Declaración Jurada de Piscinas Privadas (<=1.5m de deslinde)",
            "Edificaciones Complementarias en Áreas Verdes"
        ]
    )
}


def get_form_by_id(form_id: str) -> Optional[DOMFormInfo]:
    return DOM_FORMS_CATALOG.get(form_id)


def get_form_pdf_bytes(pdf_filename: str) -> Optional[bytes]:
    pdf_path = os.path.join(KNOWLEDGE_DIR, pdf_filename)
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            return f.read()
    return None


def determine_dom_form(
    project_metadata: Optional[Dict[str, Any]] = None,
    text_content: str = "",
    ai_recommendation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analiza los datos del proyecto y/o texto del plano para determinar el formulario DOM adecuado.
    Retorna un diccionario estructurado listo para ser consumido por la UI y el backend.
    """
    # 1. Si la IA sugirió explícitamente un form_id válido, priorizarlo
    if ai_recommendation_id and ai_recommendation_id in DOM_FORMS_CATALOG:
        form_info = DOM_FORMS_CATALOG[ai_recommendation_id]
        return {
            "form_id": form_info.form_id,
            "form_number": form_info.form_number,
            "title": form_info.title,
            "pdf_filename": form_info.pdf_filename,
            "category": form_info.category,
            "reason": f"Evaluado por IA como el formulario adecuado para ingresar este expediente a la DOM.",
            "applicable_permits": form_info.applicable_permits
        }

    project_metadata = project_metadata or {}
    proj_type = str(project_metadata.get("project_type", "")).lower()
    proj_name = str(project_metadata.get("name", "")).lower()
    text_lower = (text_content + " " + proj_name + " " + proj_type).lower()

    # Extraer superficie si existe en metadatos
    surface_val = None
    surface_meta = project_metadata.get("surface") or project_metadata.get("superficie")
    if surface_meta:
        m = re.search(r"(\d+(?:[\.,]\d+)?)", str(surface_meta))
        if m:
            try:
                surface_val = float(m.group(1).replace(",", "."))
            except ValueError:
                pass

    # 2. Evaluación por reglas de negocio deterministas
    
    # Criterio Form 5: Demolición, piscinas u obras auxiliares
    if "demolicion" in text_lower or "demolición" in text_lower or "piscina" in text_lower or "obras auxiliares" in text_lower:
        form_info = DOM_FORMS_CATALOG["form_5"]
        reason = "El expediente incluye faenas de demolición, piscinas o instalaciones auxiliares no clasificadas como edificación principal."
        return {
            "form_id": form_info.form_id,
            "form_number": form_info.form_number,
            "title": form_info.title,
            "pdf_filename": form_info.pdf_filename,
            "category": form_info.category,
            "reason": reason,
            "applicable_permits": form_info.applicable_permits
        }

    # Criterio Form 4: Subdivisión o Fusión Predial
    if "subdivision" in text_lower or "subdivisión" in text_lower or "fusion predial" in text_lower or "fusión predial" in text_lower:
        form_info = DOM_FORMS_CATALOG["form_4"]
        reason = "El proyecto corresponde a una alteración predial de subdivisión o fusión de terrenos."
        return {
            "form_id": form_info.form_id,
            "form_number": form_info.form_number,
            "title": form_info.title,
            "pdf_filename": form_info.pdf_filename,
            "category": form_info.category,
            "reason": reason,
            "applicable_permits": form_info.applicable_permits
        }

    # Criterio Form 3: Urbanización o Loteos
    if "loteo" in text_lower or "urbanizacion" in text_lower or "urbanización" in text_lower or "division predial con afectacion" in text_lower:
        form_info = DOM_FORMS_CATALOG["form_3"]
        reason = "El proyecto contempla aperturas de calles, loteos o cesiones de espacio público de urbanización."
        return {
            "form_id": form_info.form_id,
            "form_number": form_info.form_number,
            "title": form_info.title,
            "pdf_filename": form_info.pdf_filename,
            "category": form_info.category,
            "reason": reason,
            "applicable_permits": form_info.applicable_permits
        }

    # Criterio Form 1: Obras Menores / Ampliación <= 100m²
    if "obra menor" in text_lower or "obras menores" in text_lower or "modificacion interior" in text_lower or "regularizacion" in text_lower or "regularización" in text_lower:
        form_info = DOM_FORMS_CATALOG["form_1"]
        reason = "Corresponde a Obras Menores o regularización de edificación (Art. 5.1.4 OGUC)."
        return {
            "form_id": form_info.form_id,
            "form_number": form_info.form_number,
            "title": form_info.title,
            "pdf_filename": form_info.pdf_filename,
            "category": form_info.category,
            "reason": reason,
            "applicable_permits": form_info.applicable_permits
        }

    if "ampliacion" in text_lower or "ampliación" in text_lower:
        if surface_val and surface_val <= 100.0:
            form_info = DOM_FORMS_CATALOG["form_1"]
            reason = f"Proyecto de ampliación con superficie proyectada <= 100 m² ({surface_val} m²), correspondiente a Formulario 1 (Obras Menores, Art. 5.1.4 1A OGUC)."
            return {
                "form_id": form_info.form_id,
                "form_number": form_info.form_number,
                "title": form_info.title,
                "pdf_filename": form_info.pdf_filename,
                "category": form_info.category,
                "reason": reason,
                "applicable_permits": form_info.applicable_permits
            }
        elif surface_val and surface_val > 100.0:
            form_info = DOM_FORMS_CATALOG["form_2"]
            reason = f"Proyecto de ampliación mayor a 100 m² ({surface_val} m²), correspondiente a Formulario 2 (Obras de Edificación)."
            return {
                "form_id": form_info.form_id,
                "form_number": form_info.form_number,
                "title": form_info.title,
                "pdf_filename": form_info.pdf_filename,
                "category": form_info.category,
                "reason": reason,
                "applicable_permits": form_info.applicable_permits
            }

    # Por defecto / Obra Nueva -> Formulario 2 (Obras de Edificación)
    form_info = DOM_FORMS_CATALOG["form_2"]
    reason = "Formulario principal de ingreso para Obra Nueva, construcción residencial/comercial o proyectos de edificación general."
    return {
        "form_id": form_info.form_id,
        "form_number": form_info.form_number,
        "title": form_info.title,
        "pdf_filename": form_info.pdf_filename,
        "category": form_info.category,
        "reason": reason,
        "applicable_permits": form_info.applicable_permits
    }