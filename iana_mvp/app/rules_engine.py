from __future__ import annotations

import re
from typing import Any, Dict, List

import yaml


def load_rules(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return payload.get("rules", [])


def top_evidence(matches: List[Dict[str, Any]], k: int = 3) -> List[Dict[str, Any]]:
    return matches[:k]


def run_rules(blocks, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    for rule in rules:
        rtype = rule["type"]
        matches: List[Dict[str, Any]] = []

        if rtype == "keyword_any":
            kws = [k.lower() for k in rule.get("keywords", [])]
            for b in blocks:
                matched = False
                for kw in kws:
                    pattern = re.compile(rf"(?:^|[^a-zñáéíóúü]){re.escape(kw)}", re.IGNORECASE)
                    if pattern.search(b.text_norm):
                        matched = True
                        break
                if matched:
                    matches.append({"page": b.page, "bbox": b.bbox, "snippet": b.text[:200]})

        elif rtype == "regex":
            pattern = re.compile(rule["pattern"], re.IGNORECASE)
            for b in blocks:
                if pattern.search(b.text):
                    matches.append({"page": b.page, "bbox": b.bbox, "snippet": b.text[:200]})

        elif rtype == "door_width":
            width_re = re.compile(r"(0\.?(8|9|90)|90\s*cm|900\s*mm|0\.90\s*m)", re.IGNORECASE)
            for b in blocks:
                if "puerta" in b.text_norm and width_re.search(b.text):
                    matches.append({"page": b.page, "bbox": b.bbox, "snippet": b.text[:200]})

        num_matches = len(matches)
        unique_pages = len(set(m["page"] for m in matches)) if num_matches > 0 else 0

        if rtype == "keyword_any":
            if num_matches == 0:
                status = "FAIL"
                confidence = 0.50
                notes = "No se encontró evidencia de las palabras clave en el documento."
            elif num_matches == 1:
                status = "WARNING"
                confidence = 0.70
                notes = f"Se encontró una única mención en la página {matches[0]['page']}. Verificar si corresponde al contexto esperado."
            else:
                status = "PASS"
                confidence = min(0.80 + (unique_pages * 0.04) + (num_matches * 0.01), 0.98)
                notes = f"Se encontraron {num_matches} coincidencias distribuidas en {unique_pages} páginas."

        elif rtype == "regex":
            if num_matches == 0:
                status = "UNVERIFIABLE"
                confidence = 0.45
                notes = "No se pudo verificar el patrón en el texto extraído."
            elif num_matches == 1:
                status = "WARNING"
                confidence = 0.75
                notes = f"Se encontró un único patrón coinciciente en la página {matches[0]['page']}. Validar precisión."
            else:
                status = "PASS"
                confidence = min(0.80 + (unique_pages * 0.03) + (num_matches * 0.01), 0.95)
                notes = f"Se encontraron {num_matches} patrones en {unique_pages} páginas."

        elif rtype == "door_width":
            if num_matches == 0:
                status = "UNVERIFIABLE"
                confidence = 0.40
                notes = "No se encontraron menciones de ancho de puerta dentro de los bloques de texto analizados."
            elif num_matches == 1:
                status = "WARNING"
                confidence = 0.70
                notes = f"Se detectó un solo ancho de puerta en la página {matches[0]['page']}. Validar si aplica a todos los accesos principales."
            else:
                status = "PASS"
                confidence = min(0.75 + (unique_pages * 0.04) + (num_matches * 0.01), 0.92)
                notes = f"Se detectaron {num_matches} referencias de puertas normativas en {unique_pages} páginas."
        else:
            status = "UNVERIFIABLE"
            confidence = 0.30
            notes = "Tipo de regla no soportado."

        findings.append(
            {
                "id": rule["id"],
                "title": rule["title"],
                "norm_ref": rule.get("norm_ref", ""),
                "severity": rule.get("severity", "low"),
                "status": status,
                "confidence": round(float(confidence), 2),
                "evidence": top_evidence(matches, 3),
                "notes": notes,
            }
        )

    return findings


def _parse_float(val: Any) -> Optional[float]:
    """Helper para convertir strings con números, comas y unidades a float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().replace(",", ".")
    m = re.search(r"[-+]?\d*\.?\d+", val_str)
    if m:
        try:
            return float(m.group(0))
        except ValueError:
            return None
    return None


def evaluate_prc_numeric_rules(
    project_metadata: Dict[str, Any],
    region: str,
    commune: str,
    zone_code: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Evalúa determinísticamente los parámetros numéricos del proyecto contra la ficha
    del Plan Regulador Comunal (PRC) correspondiente a la comuna y zona.
    """
    findings: List[Dict[str, Any]] = []
    
    from knowledge.prc.registry import get_zone_sheet, get_prc_data
    
    # 1. Resolver código de zona
    if not zone_code:
        zone_code = project_metadata.get("zona_prc") or project_metadata.get("zona") or project_metadata.get("zona_regulador")
        
    if not zone_code:
        return [
            {
                "id": "PRC_ZONE_MISSING",
                "title": "Zona del Plan Regulador Comunal no identificada",
                "norm_ref": f"PRC {commune.title()}",
                "severity": "medium",
                "status": "WARNING",
                "confidence": 0.90,
                "evidence": [],
                "notes": f"La comuna de {commune.title()} posee Plan Regulador Comunal. Sube el Certificado de Informaciones Previas (CIP) para identificar la zona exacta y verificar coeficientes.",
            }
        ]
        
    zone_sheet = get_zone_sheet(region, commune, zone_code)
    if not zone_sheet:
        return [
            {
                "id": "PRC_ZONE_NOT_FOUND",
                "title": f"Zona '{zone_code}' no encontrada en el PRC de {commune.title()}",
                "norm_ref": f"PRC {commune.title()}",
                "severity": "low",
                "status": "UNVERIFIABLE",
                "confidence": 0.70,
                "evidence": [],
                "notes": f"No se encontró la ficha técnica para la zona '{zone_code}'. Revisa la denominación en la Ordenanza Local.",
            }
        ]
        
    norm_ref = f"PRC {commune.title()} - Zona {zone_sheet['code']} ({zone_sheet.get('title', '')})"
    
    # Extraer métricas del proyecto
    sup_terreno = _parse_float(project_metadata.get("superficie_terreno") or project_metadata.get("superficie_predial"))
    sup_construida = _parse_float(project_metadata.get("superficie_construida") or project_metadata.get("superficie_total"))
    sup_primer_piso = _parse_float(project_metadata.get("superficie_primer_piso") or project_metadata.get("ocupacion_suelo_m2"))
    altura_proy = _parse_float(project_metadata.get("altura_maxima") or project_metadata.get("altura_edificacion") or project_metadata.get("altura"))
    
    # 1. Constructibilidad
    max_const = zone_sheet.get("coeficiente_constructibilidad_max")
    if max_const is not None and sup_terreno and sup_construida and sup_terreno > 0:
        coef_calculado = round(sup_construida / sup_terreno, 3)
        if coef_calculado > max_const:
            findings.append({
                "id": "PRC_CONSTRUCTIBILIDAD_EXCEEDED",
                "title": "Coeficiente de Constructibilidad Supera el Límite del PRC",
                "norm_ref": norm_ref,
                "severity": "high",
                "status": "FAIL",
                "confidence": 0.95,
                "evidence": [{"param": "constructibilidad", "calculado": coef_calculado, "maximo_prc": max_const}],
                "notes": f"El coeficiente calculado ({coef_calculado}) supera el máximo permitido de {max_const} para la zona {zone_sheet['code']}.",
            })
        else:
            findings.append({
                "id": "PRC_CONSTRUCTIBILIDAD_OK",
                "title": "Coeficiente de Constructibilidad Conforme al PRC",
                "norm_ref": norm_ref,
                "severity": "low",
                "status": "PASS",
                "confidence": 0.95,
                "evidence": [{"param": "constructibilidad", "calculado": coef_calculado, "maximo_prc": max_const}],
                "notes": f"Constructibilidad proyectada ({coef_calculado}) cumple con el límite máximo ({max_const}).",
            })
            
    # 2. Ocupación de Suelo
    max_ocup = zone_sheet.get("coeficiente_ocupacion_suelo_max")
    if max_ocup is not None and sup_terreno and sup_primer_piso and sup_terreno > 0:
        ocup_calculada = round(sup_primer_piso / sup_terreno, 3)
        if ocup_calculada > max_ocup:
            findings.append({
                "id": "PRC_OCUPACION_EXCEEDED",
                "title": "Coeficiente de Ocupación de Suelo Supera el Límite del PRC",
                "norm_ref": norm_ref,
                "severity": "high",
                "status": "FAIL",
                "confidence": 0.95,
                "evidence": [{"param": "ocupacion_suelo", "calculado": ocup_calculada, "maximo_prc": max_ocup}],
                "notes": f"La ocupación de suelo calculada ({ocup_calculada}) supera el máximo permitido de {max_ocup} en la zona {zone_sheet['code']}.",
            })
        else:
            findings.append({
                "id": "PRC_OCUPACION_OK",
                "title": "Coeficiente de Ocupación de Suelo Conforme al PRC",
                "norm_ref": norm_ref,
                "severity": "low",
                "status": "PASS",
                "confidence": 0.95,
                "evidence": [{"param": "ocupacion_suelo", "calculado": ocup_calculada, "maximo_prc": max_ocup}],
                "notes": f"Ocupación de suelo proyectada ({ocup_calculada}) cumple con el límite máximo ({max_ocup}).",
            })
            
    # 3. Altura Máxima
    max_alt_str = zone_sheet.get("altura_maxima")
    max_alt = _parse_float(max_alt_str)
    if max_alt is not None and altura_proy is not None:
        if altura_proy > max_alt:
            findings.append({
                "id": "PRC_ALTURA_EXCEEDED",
                "title": "Altura de Edificación Supera la Altura Máxima del PRC",
                "norm_ref": norm_ref,
                "severity": "high",
                "status": "FAIL",
                "confidence": 0.95,
                "evidence": [{"param": "altura_m", "proyectada": altura_proy, "maximo_prc": max_alt}],
                "notes": f"La altura proyectada ({altura_proy} m) supera la altura máxima permitida de {max_alt} m ({max_alt_str}) en la zona {zone_sheet['code']}.",
            })
        else:
            findings.append({
                "id": "PRC_ALTURA_OK",
                "title": "Altura de Edificación Conforme al PRC",
                "norm_ref": norm_ref,
                "severity": "low",
                "status": "PASS",
                "confidence": 0.95,
                "evidence": [{"param": "altura_m", "proyectada": altura_proy, "maximo_prc": max_alt}],
                "notes": f"Altura proyectada ({altura_proy} m) cumple con la altura máxima ({max_alt} m).",
            })
            
    return findings