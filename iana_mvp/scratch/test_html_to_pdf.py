import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.report import render_pdf_report

mock_result = {
    "filename": "PLANO_EDIFICIO_A.pdf",
    "project_name": "MEJORAMIENTO PLAZA SALVADOR ALLENDE",
    "success_probability": 60.0,
    "summary_notes": "El proyecto presenta un cumplimiento moderado. Se observan faltas críticas en accesibilidad de escaleras y anchos de pasillos.",
    "infractions": [
        {
            "rule_id": "Artículo 4.1.7",
            "description": "Falta de especificación de rampas de acceso para personas con movilidad reducida.",
            "severity": "ALTA",
            "evidence": "Rampa con pendiente de 12%",
            "justification": "La OGUC exige que las rampas tengan una pendiente máxima de 8%."
        },
        {
            "rule_id": "Artículo 4.1.4",
            "description": "Ventilación insuficiente en baños.",
            "severity": "MEDIA",
            "evidence": "Baño central sin ventana ni ducto",
            "justification": "Los baños deben ventilarse de forma natural o mediante ductos de al menos 0.16 m2."
        }
    ]
}

try:
    pdf_bytes = render_pdf_report(mock_result["filename"], mock_result)
    with open("scratch/test_report.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("PDF generated successfully as scratch/test_report.pdf")
except Exception as e:
    print("Error:", e)