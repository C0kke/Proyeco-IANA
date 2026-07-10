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
        access_token = jwt_token.split(":::")[0] if ":::" in jwt_token else jwt_token
        client = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
        client.postgrest.auth(access_token)
        
        if hasattr(client, "storage") and client.storage:
            if hasattr(client.storage, "session") and hasattr(client.storage.session, "headers"):
                client.storage.session.headers.update({"Authorization": f"Bearer {access_token}"})
            if hasattr(client.storage, "_headers"):
                client.storage._headers.update({"Authorization": f"Bearer {access_token}"})
                
        return client
    else:
        return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def sign_in_user(email: str, password: str) -> Dict[str, Any]:
    admin_client = get_supabase_client()
    try:
        response = admin_client.auth.sign_in_with_password({"email": email, "password": password})
        if response.session:
            combined_token = f"{response.session.access_token}:::{response.session.refresh_token}"
            return {
                "success": True,
                "user": response.user,
                "jwt_token": combined_token,
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
        access_token = jwt_token
        refresh_token = None
        if ":::" in jwt_token:
            parts = jwt_token.split(":::")
            access_token = parts[0]
            if len(parts) > 1:
                refresh_token = parts[1]
                
        try:
            response = admin_client.auth.get_user(access_token)
            if response.user:
                return {
                    "success": True, 
                    "user": response.user,
                    "jwt_token": jwt_token
                }
        except Exception:
            if refresh_token:
                logger.info("Access token expirado. Intentando refrescar sesión...")
                refresh_res = admin_client.auth.refresh_session(refresh_token)
                if refresh_res.session:
                    new_combined = f"{refresh_res.session.access_token}:::{refresh_res.session.refresh_token}"
                    return {
                        "success": True,
                        "user": refresh_res.user,
                        "jwt_token": new_combined,
                        "refreshed": True
                    }
                    
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
    
    safe_filename = os.path.basename(file_name)
    if not safe_filename or safe_filename in [".", ".."]:
        import uuid
        safe_filename = f"documento_{uuid.uuid4().hex[:8]}.pdf"
        
    bucket_path = f"{user_id}/{project_id}/{document_type}/{safe_filename}"
    user_client = get_supabase_client(jwt_token)
    
    try:
        user_client.storage.from_(bucket_name).upload(
            path=bucket_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf", "x-upsert": "true"}
        )
        doc_record = {
            "project_id": project_id,
            "file_name": safe_filename,
            "document_type": document_type,
            "bucket_path": bucket_path
        }
        db_res = user_client.table("documents").insert(doc_record).execute()
        
        logger.info(f"Documento '{safe_filename}' guardado exitosamente en Supabase (Bucket + DB).")
        return {
            "success": True,
            "storage_location": "supabase",
            "bucket_path": bucket_path,
            "document": db_res.data[0] if db_res.data else doc_record
        }
        
    except Exception as e:
        logger.critical(
            f"ALERTA DESARROLLO - FALLO EN STORAGE SUPABASE: "
            f"No se pudo guardar el archivo '{safe_filename}' en el bucket '{bucket_name}' para el proyecto '{project_id}'. "
            f"Detalle del error: {str(e)}"
        )
        
        try:
            proj_check = user_client.table("projects").select("id").eq("id", project_id).execute()
            if not proj_check.data:
                logger.error(f"Intento de acceso no autorizado detectado en fallback para el proyecto {project_id}")
                return {"success": False, "error": "Acceso denegado al proyecto o proyecto no encontrado."}
        except Exception as check_err:
            logger.error(f"Error comprobando propiedad del proyecto en fallback: {check_err}")
            return {"success": False, "error": "No se pudo verificar el acceso al proyecto."}

        try:
            local_fallback_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                "data", 
                "uploads", 
                "fallback"
            )
            os.makedirs(local_fallback_dir, exist_ok=True)
            local_file_path = os.path.join(local_fallback_dir, f"{project_id}_{safe_filename}")
            
            with open(local_file_path, "wb") as handle:
                handle.write(file_bytes)
                
            local_rel_path = f"local://fallback/{project_id}_{safe_filename}"
            logger.warning(f"Fallback activado: Archivo guardado localmente en: {local_file_path}")
            
            fallback_record = {
                "project_id": project_id,
                "file_name": safe_filename,
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

def list_project_documents(project_id: str, jwt_token: str) -> List[Dict[str, Any]]:
    client = get_supabase_client(jwt_token)
    try:
        res = client.table("documents").select("*").eq("project_id", project_id).execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Error al listar documentos del proyecto: {e}")
        return []

def delete_project_document(doc_id: str, jwt_token: str) -> Dict[str, Any]:
    client = get_supabase_client(jwt_token)
    try:
        doc_res = client.table("documents").select("*").eq("id", doc_id).execute()
        if not doc_res.data:
            return {"success": False, "error": "El documento no existe."}
            
        doc = doc_res.data[0]
        bucket_path = doc.get("bucket_path", "")
        
        if bucket_path:
            if bucket_path.startswith("local://fallback/"):
                filename = os.path.basename(bucket_path.replace("local://fallback/", ""))
                local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads", "fallback", filename)
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except Exception as fs_err:
                        logger.error(f"Error borrando archivo local de fallback: {fs_err}")
            else:
                try:
                    client.storage.from_("project-documents").remove([bucket_path])
                except Exception as storage_err:
                    logger.error(f"Error al borrar archivo del storage de Supabase: {storage_err}")
                    
        client.table("documents").delete().eq("id", doc_id).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error al eliminar documento: {e}")
        return {"success": False, "error": str(e)}

def delete_project(project_id: str, jwt_token: str) -> Dict[str, Any]:
    client = get_supabase_client(jwt_token)
    try:
        docs_res = client.table("documents").select("bucket_path").eq("project_id", project_id).execute()
        docs = docs_res.data or []
        
        for doc in docs:
            bucket_path = doc.get("bucket_path", "")
            if bucket_path:
                if bucket_path.startswith("local://fallback/"):
                    filename = os.path.basename(bucket_path.replace("local://fallback/", ""))
                    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads", "fallback", filename)
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                        except Exception as fs_err:
                            logger.error(f"Error borrando archivo local de fallback en delete_project: {fs_err}")
                else:
                    try:
                        client.storage.from_("project-documents").remove([bucket_path])
                    except Exception as storage_err:
                        logger.error(f"Error al borrar del storage remoto en delete_project: {storage_err}")
                        
        client.table("projects").delete().eq("id", project_id).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error al eliminar proyecto: {e}")
        return {"success": False, "error": str(e)}

def get_document_file_bytes(doc: dict, jwt_token: str) -> bytes | None:
    bucket_path = doc.get("bucket_path", "")
    if not bucket_path:
        return None
        
    if bucket_path.startswith("local://fallback/"):
        filename = os.path.basename(bucket_path.replace("local://fallback/", ""))
        local_path = os.path.join(DATA_DIR, "uploads", "fallback", filename)
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    return f.read()
            except OSError as err:
                logger.error(f"Error al leer archivo local de fallback: {err}")
    else:
        try:
            client = get_supabase_client(jwt_token)
            res = client.storage.from_("project-documents").download(bucket_path)
            return res
        except Exception as e:
            logger.error(f"Error al descargar archivo desde Supabase Storage: {e}")
            
    return None