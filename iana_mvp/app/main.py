from __future__ import annotations

import json
import os
import uuid

from fastapi import FastAPI, File, UploadFile, Response, Depends, Header, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .pdf_extract import extract_text_blocks
from .report import render_html_report
from .ai_verifier import (
    evaluate_project_with_ai,
    evaluate_document_individually,
    consolidate_project_context
)
from .db import (
    sign_in_user,
    sign_up_user,
    verify_jwt_session,
    create_project,
    list_user_projects,
    upload_project_document,
    save_document_analysis,
    update_project_context_db,
    get_supabase_client
)

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

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    phone: str = ""
    rut: str
    role: str = "architect"

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Acceso denegado. Se requiere un token de sesión válido (Bearer Token)."
        )
    token = authorization.split(" ")[1]
    res = verify_jwt_session(token)
    if not res["success"]:
        raise HTTPException(status_code=401, detail=res["error"])
    return {
        "user": res["user"],
        "token": token
    }

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

@app.post("/api/auth/login")
def login(req: LoginRequest):
    res = sign_in_user(req.email, req.password)
    if not res["success"]:
        return JSONResponse({"error": res["error"]}, status_code=400)
    return {
        "jwt_token": res["jwt_token"],
        "user": {
            "id": res["user"].id,
            "email": res["user"].email,
            "user_metadata": res["user"].user_metadata
        }
    }

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    res = sign_up_user(
        email=req.email,
        password=req.password,
        name=req.name,
        phone=req.phone,
        rut=req.rut,
        role=req.role
    )
    if not res["success"]:
        return JSONResponse({"error": res["error"]}, status_code=400)
    return {"message": "Usuario registrado con éxito.", "user_id": res["user"].id}

@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    project_id: str = Form(None),
    document_type: str = Form("other"),
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
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

    upload_res = None
    if project_id:
        try:
            upload_res = upload_project_document(
                user_id=current_user["user"].id,
                project_id=project_id,
                file_name=file.filename,
                file_bytes=content,
                document_type=document_type,
                jwt_token=current_user["token"]
            )
            print(f"Subida de documento a Supabase completada: {upload_res}")
        except Exception as e:
            print(f"Error subiendo a Supabase Storage (se mantiene copia local): {e}")

    blocks = extract_text_blocks(file_path)
    plan_text = "\n".join([b.text for b in blocks])

    eval_dict = None
    if project_id:
        try:
            print(f"Iniciando análisis individual de documento '{file.filename}' (Tipo: {document_type})...")
            doc_analysis = evaluate_document_individually(plan_text, document_type, OGUC_CONTENT)
            
            if upload_res and upload_res.get("success") and "document" in upload_res:
                doc_id = upload_res["document"].get("id")
                if doc_id:
                    try:
                        save_document_analysis({
                            "document_id": doc_id,
                            "extracted_text_summary": doc_analysis.document_summary,
                            "infractions": [inf.model_dump() for inf in doc_analysis.infractions],
                            "metadata": doc_analysis.extracted_metadata
                        }, current_user["token"])
                        print(f"Análisis individual de documento guardado en DB.")
                    except Exception as db_err:
                        print(f"Error guardando análisis del documento en la DB: {db_err}")

            print(f"Consolidando contexto incremental para el proyecto {project_id}...")
            client = get_supabase_client(current_user["token"])
            proj_res = client.table("projects").select("*").eq("id", project_id).execute()
            if proj_res.data:
                project = proj_res.data[0]
                existing_context = project.get("consolidated_context", "") or "Proyecto inicializado sin documentos."
                existing_infractions = project.get("consolidated_infractions", []) or []
                
                consolidated = consolidate_project_context(
                    project_metadata=project,
                    existing_context=existing_context,
                    existing_infractions=existing_infractions,
                    new_doc_analysis=doc_analysis,
                    oguc_text=OGUC_CONTENT
                )
                
                update_project_context_db(
                    project_id=project_id,
                    context_data={
                        "consolidated_context": consolidated.consolidated_context,
                        "consolidated_infractions": [inf.model_dump() for inf in consolidated.consolidated_infractions],
                        "success_probability": consolidated.success_probability,
                        "extracted_metadata": consolidated.extracted_metadata,
                        "terrain_rol": consolidated.extracted_metadata.get("rol_terreno", project.get("terrain_rol")),
                        "block": consolidated.extracted_metadata.get("manzana", project.get("block")),
                        "lot": consolidated.extracted_metadata.get("lote", project.get("lot"))
                    },
                    jwt_token=current_user["token"]
                )
                
                eval_dict = {
                    "project_name": project.get("name"),
                    "success_probability": consolidated.success_probability,
                    "infractions": [inf.model_dump() for inf in consolidated.consolidated_infractions],
                    "summary_notes": consolidated.consolidated_context
                }
                print(f"Contexto del proyecto consolidado con éxito. Viabilidad: {consolidated.success_probability}%")
        except Exception as e:
            print(f"Error en flujo incremental con IA (fallando a análisis único): {e}")
            eval_dict = None

    if not eval_dict:
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
def status(job_id: str, current_user: dict = Depends(get_current_user)) -> JSONResponse:
    ok = os.path.exists(os.path.join(RESULTS, f"{job_id}.json"))
    return JSONResponse({"job_id": job_id, "status": "DONE" if ok else "NOT_FOUND"})


@app.get("/api/result/{job_id}")
def result(job_id: str, current_user: dict = Depends(get_current_user)) -> JSONResponse:
    path = os.path.join(RESULTS, f"{job_id}.json")
    if not os.path.exists(path):
        return JSONResponse({"error": "not_found"}, status_code=404)
    with open(path, "r", encoding="utf-8") as handle:
        return JSONResponse(json.load(handle))


@app.get("/api/report/{job_id}", response_class=HTMLResponse)
def report(job_id: str, current_user: dict = Depends(get_current_user)) -> HTMLResponse:
    path = os.path.join(RESULTS, f"{job_id}.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>Not found</h1>", status_code=404)
    with open(path, "r", encoding="utf-8") as handle:
        return HTMLResponse(handle.read())


@app.get("/api/jobs")
def list_jobs(page: int = 1, page_size: int = 10, current_user: dict = Depends(get_current_user)) -> JSONResponse:
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
def report_pdf(job_id: str, current_user: dict = Depends(get_current_user)) -> Response:
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

class ProjectCreateRequest(BaseModel):
    name: str
    project_type: str = "real_estate"
    region: str
    commune: str
    latitude: float = None
    longitude: float = None
    terrain_rol: str = ""
    block: str = ""
    lot: str = ""

@app.post("/api/projects")
def api_create_project(req: ProjectCreateRequest, current_user: dict = Depends(get_current_user)):
    p_data = {
        "user_id": current_user["user"].id,
        "name": req.name,
        "project_type": req.project_type,
        "region": req.region,
        "commune": req.commune,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "terrain_rol": req.terrain_rol,
        "block": req.block,
        "lot": req.lot
    }
    res = create_project(p_data, current_user["token"])
    if not res["success"]:
        return JSONResponse({"error": res["error"]}, status_code=400)
    return res["project"]

@app.get("/api/projects")
def api_list_projects(current_user: dict = Depends(get_current_user)):
    projects = list_user_projects(current_user["token"])
    return projects