import os
import base64
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "public")

def get_public_asset_path(filename: str) -> str:
    """Retorna la ruta absoluta del archivo especificado en la carpeta /public."""
    primary_path = os.path.join(PUBLIC_DIR, filename)
    if os.path.exists(primary_path):
        return primary_path
    
    cwd_path = os.path.join(os.getcwd(), "public", filename)
    if os.path.exists(cwd_path):
        return cwd_path
        
    alt_path = os.path.join(BASE_DIR, "public", filename)
    if os.path.exists(alt_path):
        return alt_path
        
    return ""

def get_asset_base64(filename: str) -> Optional[str]:
    """Retorna el contenido en formato Data URI base64 para incrustar en HTML/CSS."""
    path = get_public_asset_path(filename)
    if path and os.path.exists(path):
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        mime_type = "image/png" if ext == "png" else f"image/{ext}"
        if ext == "ico":
            mime_type = "image/x-icon"
        try:
            with open(path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
                return f"data:{mime_type};base64,{b64_data}"
        except Exception as e:
            print(f"Error cargando asset {filename}: {e}")
    return None