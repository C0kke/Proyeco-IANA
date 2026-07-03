import os
import logging
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("iana.db")

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY or not SUPABASE_SECRET_KEY:
    logger.warning("Faltan variables de entorno de Supabase en el archivo .env. La integración podría fallar.")

def get_supabase_client(jwt_token: Optional[str] = None) -> Client:
    if jwt_token:
        client = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
        client.postgrest.auth(jwt_token)
        client.storage.headers.update({"Authorization": f"Bearer {jwt_token}"})
        return client
    else:
        return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def sign_in_user(email: str, password: str) -> Dict[str, Any]:
    admin_client = get_supabase_client()
    try:
        response = admin_client.auth.sign_in_with_password({"email": email, "password": password})
        if response.session:
            return {
                "success": True,
                "user": response.user,
                "jwt_token": response.session.access_token,
                "session": response.session
            }
        return {"success": False, "error": "No se pudo iniciar sesión."}
    except Exception as e:
        logger.error(f"Error al iniciar sesión: {e}")
        return {"success": False, "error": str(e)}

def sign_up_user(email: str, password: str, name: str, phone: str, rut: str, role: str) -> Dict[str, Any]:
    admin_client = get_supabase_client()
    try:
        response = admin_client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "name": name,
                    "phone": phone,
                    "rut": rut,
                    "role": role
                }
            }
        })
        if response.user:
            return {"success": True, "user": response.user}
        return {"success": False, "error": "No se pudo crear el usuario."}
    except Exception as e:
        logger.error(f"Error al registrar usuario: {e}")
        return {"success": False, "error": str(e)}

def verify_jwt_session(jwt_token: str) -> Dict[str, Any]:
    admin_client = get_supabase_client()
    try:
        response = admin_client.auth.get_user(jwt_token)
        if response.user:
            return {"success": True, "user": response.user}
        return {"success": False, "error": "Token JWT inválido o expirado."}
    except Exception as e:
        logger.error(f"Error verificando JWT: {e}")
        return {"success": False, "error": str(e)}

def create_project(project_data: Dict[str, Any], jwt_token: str) -> Dict[str, Any]:
    client = get_supabase_client(jwt_token)
    try:
        res = client.table("projects").insert(project_data).execute()
        if res.data:
            return {"success": True, "project": res.data[0]}
        return {"success": False, "error": "No se recibió respuesta al insertar el proyecto."}
    except Exception as e:
        logger.error(f"Error al crear proyecto: {e}")
        return {"success": False, "error": str(e)}

def list_user_projects(jwt_token: str) -> List[Dict[str, Any]]:
    client = get_supabase_client(jwt_token)
    try:
        res = client.table("projects").select("*").order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error al listar proyectos: {e}")
        return []

def upload_project_document(
    user_id: str,
    project_id: str,
    file_name: str,
    file_bytes: bytes,
    document_type: str,
    jwt_token: str
) -> Dict[str, Any]:
    bucket_name = "project-documents"
    bucket_path = f"{user_id}/{project_id}/{document_type}/{file_name}"
    user_client = get_supabase_client(jwt_token)
    
    try:
        user_client.storage.from_(bucket_name).upload(
            path=bucket_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf", "x-upsert": "true"}
        )
        doc_record = {
            "project_id": project_id,
            "file_name": file_name,
            "document_type": document_type,
            "bucket_path": bucket_path
        }
        db_res = user_client.table("documents").insert(doc_record).execute()
        
        logger.info(f"Documento '{file_name}' guardado exitosamente en Supabase (Bucket + DB).")
        return {
            "success": True,
            "storage_location": "supabase",
            "bucket_path": bucket_path,
            "document": db_res.data[0] if db_res.data else doc_record
        }
        
    except Exception as e:
        logger.critical(
            f"ALERTA DESARROLLO - FALLO EN STORAGE SUPABASE: "
            f"No se pudo guardar el archivo '{file_name}' en el bucket '{bucket_name}' para el proyecto '{project_id}'. "
            f"Detalle del error: {str(e)}"
        )
        try:
            local_fallback_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                "data", 
                "uploads", 
                "fallback"
            )
            os.makedirs(local_fallback_dir, exist_ok=True)
            local_file_path = os.path.join(local_fallback_dir, f"{project_id}_{file_name}")
            
            with open(local_file_path, "wb") as handle:
                handle.write(file_bytes)
                
            local_rel_path = f"local://fallback/{project_id}_{file_name}"
            logger.warning(f"Fallback activado: Archivo guardado localmente en: {local_file_path}")
            
            fallback_record = {
                "project_id": project_id,
                "file_name": file_name,
                "document_type": document_type,
                "bucket_path": local_rel_path
            }
            
            try:
                admin_client = get_supabase_client(None)
                db_res = admin_client.table("documents").insert(fallback_record).execute()
                doc_data = db_res.data[0] if db_res.data else fallback_record
            except Exception as db_err:
                logger.error(f"No se pudo guardar el metadato del fallback en la DB: {db_err}")
                doc_data = fallback_record
                doc_data["is_db_offline"] = True
                
            return {
                "success": True,
                "storage_location": "local_fallback",
                "bucket_path": local_rel_path,
                "local_path": local_file_path,
                "document": doc_data
            }
            
        except Exception as local_err:
            logger.error(f"Fallo crítico doble: el almacenamiento local de fallback también falló: {local_err}")
            return {
                "success": False,
                "error": f"Fallo en Supabase Storage y fallback local no disponible. Error: {local_err}"
            }

def save_document_analysis(analysis_data: Dict[str, Any], jwt_token: str) -> Dict[str, Any]:
    client = get_supabase_client(jwt_token)
    try:
        res = client.table("document_analyses").insert(analysis_data).execute()
        if res.data:
            return {"success": True, "analysis": res.data[0]}
        return {"success": False, "error": "No se recibió respuesta al guardar el análisis."}
    except Exception as e:
        logger.error(f"Error al guardar análisis del documento: {e}")
        return {"success": False, "error": str(e)}

def update_project_context_db(project_id: str, context_data: Dict[str, Any], jwt_token: str) -> Dict[str, Any]:
    client = get_supabase_client(jwt_token)
    try:
        res = client.table("projects").update(context_data).eq("id", project_id).execute()
        if res.data:
            return {"success": True, "project": res.data[0]}
        return {"success": False, "error": "No se recibió respuesta al actualizar el proyecto."}
    except Exception as e:
        logger.error(f"Error al actualizar contexto del proyecto: {e}")
        return {"success": False, "error": str(e)}