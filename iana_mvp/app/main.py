from __future__ import annotations

import json
import os
import uuid

from fastapi import FastAPI, File, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from .pdf_extract import extract_text_blocks
from .report import render_html_report
from .ai_verifier import evaluate_project_with_ai

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS = os.path.join(DATA_DIR, "uploads")
RESULTS = os.path.join(DATA_DIR, "results")

os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)

app = FastAPI(title="IANA v0.1 MVP - OGUC Validador")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

OGUC_CONTENT = ""

@app.on_event("startup")
def load_oguc():
    global OGUC_CONTENT
    oguc_path = os.path.join(BASE_DIR, "knowledge", "OGUC_2026.md")
    if os.path.exists(oguc_path):
        print(f"Cargando OGUC en memoria desde: {oguc_path}...")
        with open(oguc_path, "r", encoding="utf-8") as handle:
            OGUC_CONTENT = handle.read()
        print(f"OGUC cargada con éxito. Tamaño: {len(OGUC_CONTENT)} caracteres.")
    else:
        alt_path = os.path.join(os.path.dirname(BASE_DIR), "knowledge", "OGUC_2026.md")
        if os.path.exists(alt_path):
            print(f"Cargando OGUC en memoria desde ruta alternativa: {alt_path}...")
            with open(alt_path, "r", encoding="utf-8") as handle:
                OGUC_CONTENT = handle.read()
            print(f"OGUC cargada con éxito. Tamaño: {len(OGUC_CONTENT)} caracteres.")
        else:
            print("ADVERTENCIA: No se encontró el archivo OGUC_2026.md. Asegúrate de que existe en la carpeta 'knowledge'.")


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)) -> JSONResponse:
    job_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx"]:
        return JSONResponse(
            {"error": "Formato de archivo no soportado. El sistema requiere un documento PDF (.pdf) o Word (.docx)."},
            status_code=400
        )

    file_path = os.path.join(UPLOADS, f"{job_id}{ext}")
    
    content = await file.read()
    print(f"Archivo recibido para procesamiento: '{file.filename}' ({len(content)} bytes)")

    if len(content) == 0:
        return JSONResponse(
            {"error": "El archivo subido está vacío (0 bytes). Por favor, selecciona un archivo válido en tu cliente HTTP."},
            status_code=400
        )

    with open(file_path, "wb") as handle:
        handle.write(content)

    blocks = extract_text_blocks(file_path)
    plan_text = "\n".join([b.text for b in blocks])

    try:
        evaluation = evaluate_project_with_ai(plan_text, OGUC_CONTENT)
        eval_dict = evaluation.model_dump()
    except Exception as e:
        print(f"Error evaluando el plano por IA: {e}")
        eval_dict = {
            "project_name": file.filename,
            "success_probability": 0.0,
            "infractions": [
                {
                    "rule_id": "ERROR_SISTEMA",
                    "description": f"No se pudo completar el análisis normativo por IA debido a un error: {str(e)}",
                    "severity": "ALTA",
                    "evidence": "N/A",
                    "justification": "Fallo de comunicación con la API de Gemini o Instructor."
                }
            ],
            "summary_notes": "Error crítico al procesar la verificación por Inteligencia Artificial."
        }

    result = {
        "job_id": job_id,
        "filename": file.filename,
        "project_name": eval_dict.get("project_name", file.filename),
        "success_probability": eval_dict.get("success_probability", 0.0),
        "infractions": eval_dict.get("infractions", []),
        "summary_notes": eval_dict.get("summary_notes", ""),
    }
    
    out_json = os.path.join(RESULTS, f"{job_id}.json")
    with open(out_json, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)

    out_html = os.path.join(RESULTS, f"{job_id}.html")
    with open(out_html, "w", encoding="utf-8") as handle:
        handle.write(render_html_report(file.filename, result))

    try:
        from .report import render_pdf_report
        out_pdf = os.path.join(RESULTS, f"{job_id}.pdf")
        pdf_bytes = render_pdf_report(file.filename, result)
        with open(out_pdf, "wb") as handle:
            handle.write(pdf_bytes)
    except Exception as e:
        print(f"Error generando PDF durante la subida: {e}")

    return JSONResponse({"job_id": job_id})


@app.get("/api/status/{job_id}")
def status(job_id: str) -> JSONResponse:
    ok = os.path.exists(os.path.join(RESULTS, f"{job_id}.json"))
    return JSONResponse({"job_id": job_id, "status": "DONE" if ok else "NOT_FOUND"})


@app.get("/api/result/{job_id}")
def result(job_id: str) -> JSONResponse:
    path = os.path.join(RESULTS, f"{job_id}.json")
    if not os.path.exists(path):
        return JSONResponse({"error": "not_found"}, status_code=404)
    with open(path, "r", encoding="utf-8") as handle:
        return JSONResponse(json.load(handle))


@app.get("/api/report/{job_id}", response_class=HTMLResponse)
def report(job_id: str) -> HTMLResponse:
    path = os.path.join(RESULTS, f"{job_id}.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>Not found</h1>", status_code=404)
    with open(path, "r", encoding="utf-8") as handle:
        return HTMLResponse(handle.read())


@app.get("/api/jobs")
def list_jobs(page: int = 1, page_size: int = 10) -> JSONResponse:
    from datetime import datetime

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 10
        
    if not os.path.exists(RESULTS):
        return JSONResponse({
            "total_jobs": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "jobs": []
        })

    files = [
        f for f in os.listdir(RESULTS)
        if f.endswith(".json")
    ]
    
    file_info = []
    for f in files:
        path = os.path.join(RESULTS, f)
        mtime = os.path.getmtime(path)
        file_info.append((path, mtime))
        
    file_info.sort(key=lambda x: x[1], reverse=True)
    
    total_jobs = len(file_info)
    total_pages = (total_jobs + page_size - 1) // page_size if total_jobs > 0 else 0
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_slice = file_info[start_idx:end_idx]
    
    jobs = []
    for path, mtime in page_slice:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                
            dt = datetime.fromtimestamp(mtime)
            jobs.append({
                "job_id": data.get("job_id"),
                "filename": data.get("filename"),
                "project_name": data.get("project_name"),
                "success_probability": data.get("success_probability"),
                "created_at": dt.isoformat(),
                "summary_notes_short": data.get("summary_notes", "")[:200] + "..." if len(data.get("summary_notes", "")) > 200 else data.get("summary_notes", ""),
                "infractions_count": len(data.get("infractions", []))
            })
        except Exception as e:
            print(f"Error leyendo archivo de resultado {path}: {e}")
            
    return JSONResponse({
        "total_jobs": total_jobs,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "jobs": jobs
    })


@app.get("/api/report/{job_id}/pdf")
def report_pdf(job_id: str) -> Response:
    path = os.path.join(RESULTS, f"{job_id}.pdf")
    if not os.path.exists(path):
        path_json = os.path.join(RESULTS, f"{job_id}.json")
        if not os.path.exists(path_json):
            return Response("Not found", status_code=404, media_type="text/plain")
        try:
            with open(path_json, "r", encoding="utf-8") as handle:
                result_data = json.load(handle)
            from .report import render_pdf_report
            pdf_bytes = render_pdf_report(result_data["filename"], result_data)
            with open(path, "wb") as handle:
                handle.write(pdf_bytes)
        except Exception as e:
            return Response(f"Error generando PDF: {str(e)}", status_code=500, media_type="text/plain")
    else:
        with open(path, "rb") as handle:
            pdf_bytes = handle.read()
            
    headers = {
        "Content-Disposition": f"attachment; filename=reporte_{job_id}.pdf"
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)