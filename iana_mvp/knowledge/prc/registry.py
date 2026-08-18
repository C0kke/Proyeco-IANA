"""
Módulo de Registro e Indexación de Planes Reguladores Comunales (PRC) por Región y Comuna.
Permite buscar fichas de zonas, normativas locales generales y extraer fragmentos
específicos para el motor de reglas deterministas y el validador de IA (Gemini).
"""

from __future__ import annotations

import os
import json
import re
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Catálogo de comunas soportadas y sus carpetas de datos
PRC_CATALOG = {
    ("coquimbo", "coquimbo"): os.path.join(BASE_DIR, "coquimbo"),
    ("iv", "coquimbo"): os.path.join(BASE_DIR, "coquimbo"),
    ("4", "coquimbo"): os.path.join(BASE_DIR, "coquimbo"),
    ("región de coquimbo", "coquimbo"): os.path.join(BASE_DIR, "coquimbo"),
    ("region de coquimbo", "coquimbo"): os.path.join(BASE_DIR, "coquimbo"),
}

_CACHE_PRC_DATA: Dict[str, Dict[str, Any]] = {}


def _normalize_name(name: str) -> str:
    if not name:
        return ""
    name_clean = name.lower().strip()
    name_clean = re.sub(r'[áàäâ]', 'a', name_clean)
    name_clean = re.sub(r'[éèëê]', 'e', name_clean)
    name_clean = re.sub(r'[íìïî]', 'i', name_clean)
    name_clean = re.sub(r'[óòöô]', 'o', name_clean)
    name_clean = re.sub(r'[úùüû]', 'u', name_clean)
    return name_clean


def get_available_prc_communes() -> List[Dict[str, str]]:
    """Retorna la lista de comunas que cuentan con Plan Regulador cargado en IANA."""
    return [
        {
            "region": "Región de Coquimbo",
            "commune": "Coquimbo",
            "instrument": "Actualización Plan Regulador Comunal de Coquimbo",
            "zones_count": 38
        }
    ]


def get_prc_data(region: str, commune: str) -> Optional[Dict[str, Any]]:
    """Carga los datos estructurados del Plan Regulador Comunal para una región y comuna."""
    norm_reg = _normalize_name(region)
    norm_com = _normalize_name(commune)
    
    cache_key = f"{norm_reg}::{norm_com}"
    if cache_key in _CACHE_PRC_DATA:
        return _CACHE_PRC_DATA[cache_key]
        
    folder_path = None
    for (r_key, c_key), path in PRC_CATALOG.items():
        if _normalize_name(c_key) == norm_com:
            folder_path = path
            break
            
    if not folder_path or not os.path.exists(folder_path):
        return None
        
    json_path = os.path.join(folder_path, "ordenanza_coquimbo.json")
    if not os.path.exists(json_path):
        for fname in os.listdir(folder_path):
            if fname.endswith(".json"):
                json_path = os.path.join(folder_path, fname)
                break
                
    if not os.path.exists(json_path):
        return None
        
    with open(json_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
        _CACHE_PRC_DATA[cache_key] = data
        return data


def normalize_zone_code(zone_code: str) -> str:
    """Normaliza un código de zona eliminando guiones o espacios extras (ej: 'ZU-3' -> 'ZU3')."""
    if not zone_code:
        return ""
    code_clean = zone_code.upper().strip()
    code_clean = re.sub(r'^(ZU|ZP|ZE|ZAV|ZR)-(\d+)', r'\1\2', code_clean)
    return code_clean


def get_zone_sheet(region: str, commune: str, zone_code: str) -> Optional[Dict[str, Any]]:
    """Obtiene la ficha paramétrica y texto normativo de una zona específica."""
    prc_data = get_prc_data(region, commune)
    if not prc_data:
        return None
        
    zones = prc_data.get("zones", {})
    norm_code = normalize_zone_code(zone_code)
    
    if norm_code in zones:
        return zones[norm_code]
        
    for z_key, z_val in zones.items():
        if z_key == norm_code or norm_code.startswith(z_key) or z_key.startswith(norm_code):
            return z_val
            
    return None


def extract_prc_context_for_prompt(
    region: str, 
    commune: str, 
    zone_code: Optional[str] = None,
    max_chars: int = 4000
) -> str:
    """
    Genera un fragmento de texto optimizado para inyectar en el prompt de Gemini.
    Si se especifica una zona, extrae la ficha de esa zona. Si no, entrega un resumen de zonas disponibles.
    """
    prc_data = get_prc_data(region, commune)
    if not prc_data:
        return ""
        
    commune_name = prc_data.get("commune", commune)
    inst_name = prc_data.get("instrument_name", "Plan Regulador Comunal")
    
    if zone_code:
        zone_sheet = get_zone_sheet(region, commune, zone_code)
        if zone_sheet:
            header = f"=== PLAN REGULADOR COMUNAL DE {commune_name.upper()} ({inst_name}) ===\n"
            header += f"FICHA NORMATIVA ESPECÍFICA - ZONA {zone_sheet.get('code')}: {zone_sheet.get('title', '')}\n\n"
            
            params = []
            if zone_sheet.get("superficie_predial_minima"):
                params.append(f"- Superficie predial mínima: {zone_sheet['superficie_predial_minima']} m2")
            if zone_sheet.get("coeficiente_constructibilidad_max") is not None:
                params.append(f"- Coeficiente máximo de constructibilidad: {zone_sheet['coeficiente_constructibilidad_max']}")
            if zone_sheet.get("coeficiente_ocupacion_suelo_max") is not None:
                params.append(f"- Coeficiente máximo de ocupación de suelo: {zone_sheet['coeficiente_ocupacion_suelo_max']}")
            if zone_sheet.get("altura_maxima"):
                params.append(f"- Altura máxima de edificación: {zone_sheet['altura_maxima']}")
            if zone_sheet.get("densidad_bruta_maxima"):
                params.append(f"- Densidad bruta máxima: {zone_sheet['densidad_bruta_maxima']}")
            if zone_sheet.get("sistema_agrupamiento"):
                params.append(f"- Sistema de agrupamiento: {zone_sheet['sistema_agrupamiento']}")
            if zone_sheet.get("antejardin"):
                params.append(f"- Antejardín exigido: {zone_sheet['antejardin']}")
                
            if params:
                header += "PARÁMETROS PRINCIPALES DE LA ZONA:\n" + "\n".join(params) + "\n\n"
                
            header += "TEXTO OFICIAL DE LA ORDENANZA LOCAL PARA ESTA ZONA:\n"
            header += zone_sheet.get("raw_text", "")[:max_chars]
            return header
            
    zones_list = list(prc_data.get("zones", {}).keys())
    return (
        f"=== PLAN REGULADOR COMUNAL DE {commune_name.upper()} ({inst_name}) ===\n"
        f"Esta comuna cuenta con Plan Regulador Comunal con {len(zones_list)} zonas normadas.\n"
        f"Zonas principales: {', '.join(zones_list[:20])}...\n"
        "Identifica en el CIP o plano la zona específica del predio para verificar sus coeficientes y alturas máximas."
    )
