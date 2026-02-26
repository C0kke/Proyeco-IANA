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
                if any(kw in b.text_norm for kw in kws):
                    matches.append({"page": b.page, "bbox": b.bbox, "snippet": b.text[:200]})
            status = "PASS" if matches else "FAIL"
            confidence = 0.9 if matches else 0.6

        elif rtype == "regex":
            pattern = re.compile(rule["pattern"], re.IGNORECASE)
            for b in blocks:
                if pattern.search(b.text):
                    matches.append({"page": b.page, "bbox": b.bbox, "snippet": b.text[:200]})
            status = "PASS" if matches else "UNVERIFIABLE"
            confidence = 0.85 if matches else 0.5

        elif rtype == "door_width":
            width_re = re.compile(r"(0\.?(8|9|90)|90\s*cm|900\s*mm|0\.90\s*m)", re.IGNORECASE)
            for b in blocks:
                if "puerta" in b.text_norm and width_re.search(b.text):
                    matches.append({"page": b.page, "bbox": b.bbox, "snippet": b.text[:200]})
            status = "PASS" if matches else "UNVERIFIABLE"
            confidence = 0.8 if matches else 0.45

        else:
            status = "UNVERIFIABLE"
            confidence = 0.3

        findings.append(
            {
                "id": rule["id"],
                "title": rule["title"],
                "norm_ref": rule.get("norm_ref", ""),
                "severity": rule.get("severity", "low"),
                "status": status,
                "confidence": float(confidence),
                "evidence": top_evidence(matches, 3),
                "notes": "" if matches else "No se encontró evidencia en el texto extraído.",
            }
        )

    return findings
