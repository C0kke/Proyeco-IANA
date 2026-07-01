import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.report import render_html_report

def save_html_report(job_id: str) -> bool:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_dir = os.path.join(base_dir, "data", "results")
    
    json_path = os.path.join(results_dir, f"{job_id}.json")
    html_path = os.path.join(results_dir, f"{job_id}.html")
    
    if not os.path.exists(json_path):
        print(f"Error: No se encontró el archivo de resultados JSON para el job_id: {job_id}")
        return False
        
    with open(json_path, "r", encoding="utf-8") as f:
        result_data = json.load(f)
        
    filename = result_data.get("filename", "desconocido.pdf")
    html_content = render_html_report(filename, result_data)
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Reporte HTML regenerado y guardado con éxito en: {html_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scratch/download_html.py <job_id>")
        sys.exit(1)
        
    job_id_arg = sys.argv[1]
    save_html_report(job_id_arg)