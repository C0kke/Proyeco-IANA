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
                    # Coincidir con la palabra clave solo al inicio de una palabra (evita falsos positivos como "scale" en "fiscales")
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

        # Calcular métricas dinámicas
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
                notes = f"Se encontró un único patrón coincidente en la página {matches[0]['page']}. Validar precisión."
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
