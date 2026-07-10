import streamlit as st
import os
import json
import urllib.parse
from app.db import create_project, update_project_context_db, list_user_projects

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@st.cache_data
def load_regions_and_communes():
    json_path = os.path.join(BASE_DIR, "knowledge", "regiones.json")
    try:
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error cargando regiones y comunas: {e}")
    return {"regions": []}

def get_commune_coordinates(region_name: str, commune_name: str) -> tuple[float, float]:
    json_path = os.path.join(BASE_DIR, "knowledge", "regiones.json")
    data = None
    try:
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for r in data.get("regions", []):
                if r.get("name") == region_name:
                    for c in r.get("communes", []):
                        if c.get("name") == commune_name:
                            if "lat" in c and "lng" in c:
                                return float(c["lat"]), float(c["lng"])
    except Exception as e:
        print(f"Error al leer regiones.json para coordenadas: {e}")

    try:
        import httpx
        from app.version import __version__
        query = f"{commune_name}, {region_name}, Chile"
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1"
        headers = {"User-Agent": f"IANA-App/{__version__}"}
        with httpx.Client(timeout=2.0) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 200:
                res_data = response.json()
                if res_data:
                    lat = float(res_data[0]["lat"])
                    lng = float(res_data[0]["lon"])
                    return lat, lng
    except Exception as g_err:
        print(f"Fallo al geocodificar comuna {commune_name}: {g_err}")

    if data:
        for r in data.get("regions", []):
            if r.get("name") == region_name:
                if r.get("communes"):
                    first_c = r["communes"][0]
                    if "lat" in first_c and "lng" in first_c:
                        return float(first_c["lat"]), float(first_c["lng"])

    return -33.4489, -70.6693


@st.dialog("Crear Nuevo Proyecto", width="large")
def render_create_project_modal():
    st.markdown("Ingresa los datos normativos y de ubicación geográfica del terreno para aplicar el marco regulatorio correspondiente.")
    
    p_name = st.text_input("Nombre del Proyecto *", placeholder="Ej: Condominio Las Flores")
    p_type = st.selectbox(
        "Tipo de Proyecto *",
        options=["private_housing", "large_scale_real_estate", "public_spaces_green_areas", "other"],
        format_func=lambda x: {
            "private_housing": "Vivienda Privada (Unifamiliar/Condominios)",
            "large_scale_real_estate": "Inmobiliario de Gran Envergadura (Comercial, Industrial)",
            "public_spaces_green_areas": "Espacios Públicos y Áreas Verdes",
            "other": "Otro"
        }[x]
    )
    
    regions_data = load_regions_and_communes()
    region_names = [r["name"] for r in regions_data.get("regions", [])]
    
    col1, col2 = st.columns(2)
    with col1:
        p_region = st.selectbox("Región *", options=region_names if region_names else ["Metropolitana de Santiago"])
    with col2:
        commune_options = []
        if regions_data.get("regions"):
            for r in regions_data["regions"]:
                if r["name"] == p_region:
                    commune_options = [c["name"] for c in r.get("communes", [])]
                    break
        if not commune_options:
            commune_options = ["Providencia", "Santiago", "Las Condes"]
        p_commune = st.selectbox("Comuna *", options=commune_options)
        
    state_key_lat = f"lat_{p_region}_{p_commune}"
    state_key_lng = f"lng_{p_region}_{p_commune}"
    
    if state_key_lat not in st.session_state:
        lat_val, lng_val = get_commune_coordinates(p_region, p_commune)
        st.session_state[state_key_lat] = lat_val
        st.session_state[state_key_lng] = lng_val
        
    st.markdown("**Ubicación Geográfica (Coordenadas Estimadas)**")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        p_lat = st.number_input(
            "Latitud", 
            format="%.8f", 
            value=st.session_state[state_key_lat],
            key=f"input_{state_key_lat}"
        )
    with col_c2:
        p_lng = st.number_input(
            "Longitud", 
            format="%.8f", 
            value=st.session_state[state_key_lng],
            key=f"input_{state_key_lng}"
        )
        
    st.session_state[state_key_lat] = p_lat
    st.session_state[state_key_lng] = p_lng
        
    st.markdown("**Identificación del Terreno (Catastral - Opcional)**")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        p_rol = st.text_input("Rol de Avalúo (Terreno)", placeholder="Ej: 1245-22")
    with col_t2:
        p_block = st.text_input("Manzana", placeholder="Ej: 14")
    with col_t3:
        p_lot = st.text_input("Lote", placeholder="Ej: A-3")
        
    st.divider()
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn2:
        submitted = st.button("Guardar Proyecto", type="primary", use_container_width=True)
    with col_btn1:
        cancelled = st.button("Cancelar", use_container_width=True)
        
    if cancelled:
        st.rerun()
        
    if submitted:
        if not p_name.strip():
            st.error("El Nombre del Proyecto es obligatorio.")
        elif not p_region or not p_commune:
            st.error("La Región y Comuna son obligatorias.")
        else:
            p_data = {
                "name": p_name.strip(),
                "project_type": p_type,
                "region": p_region,
                "commune": p_commune,
                "latitude": p_lat,
                "longitude": p_lng,
                "terrain_rol": p_rol if p_rol.strip() else None,
                "block": p_block if p_block.strip() else None,
                "lot": p_lot if p_lot.strip() else None,
                "user_id": st.session_state["user"].id
            }
            with st.spinner("Creando proyecto..."):
                res = create_project(p_data, st.session_state["jwt_token"])
                if res["success"]:
                    st.success(f"Proyecto '{p_name.strip()}' creado con éxito.")
                    st.session_state["projects"] = list_user_projects(st.session_state["jwt_token"])
                    st.session_state["active_project"] = res["project"]
                    st.rerun()
                else:
                    st.error(f"Error al guardar: {res['error']}")


@st.dialog("Editar Detalles del Proyecto", width="large")
def render_edit_project_modal():
    p = st.session_state["active_project"]
    if not p:
        st.warning("No hay un proyecto activo seleccionado.")
        return
        
    regiones_data = load_regions_and_communes()
    regions = [r["name"] for r in regiones_data.get("regions", [])]
    
    p_name = st.text_input("Nombre del Proyecto *", value=p.get("name", ""))
    
    region_idx = regions.index(p["region"]) if p.get("region") in regions else 0
    p_region = st.selectbox("Región *", options=regions, index=region_idx, key="edit_region")
    
    communes = []
    region_sel = next((r for r in regiones_data.get("regions", []) if r["name"] == p_region), None)
    if region_sel:
        communes = [c["name"] for c in region_sel.get("communes", [])]
        
    commune_idx = communes.index(p["commune"]) if p.get("commune") in communes else 0
    p_commune = st.selectbox("Comuna *", options=communes, index=commune_idx, key="edit_commune")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        p_lat = st.number_input("Latitud", format="%.8f", value=float(p.get("latitude") or 0.0), key="edit_lat")
    with col_c2:
        p_lng = st.number_input("Longitud", format="%.8f", value=float(p.get("longitude") or 0.0), key="edit_lng")
        
    st.markdown("**Identificación del Terreno (Catastral - Opcional)**")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        p_rol = st.text_input("Rol de Avalúo (Terreno)", value=p.get("terrain_rol") or "", placeholder="Ej: 1245-22")
    with col_t2:
        p_block = st.text_input("Manzana", value=p.get("block") or "", placeholder="Ej: 14")
    with col_t3:
        p_lot = st.text_input("Lote", value=p.get("lot") or "", placeholder="Ej: A-3")
        
    st.divider()
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn2:
        submitted = st.button("Guardar Cambios", type="primary", use_container_width=True)
    with col_btn1:
        cancelled = st.button("Cancelar", use_container_width=True, key="btn_cancel_edit")
        
    if cancelled:
        st.rerun()
        
    if submitted:
        if not p_name.strip():
            st.error("El Nombre del Proyecto es obligatorio.")
        elif not p_region or not p_commune:
            st.error("La Región y Comuna son obligatorias.")
        else:
            lat_val = p_lat
            lng_val = p_lng
            if (p_commune != p["commune"] or p_region != p["region"]) and (p_lat == p["latitude"] and p_lng == p["longitude"]):
                calc_lat, calc_lng = get_commune_coordinates(p_region, p_commune)
                lat_val = calc_lat
                lng_val = calc_lng
                
            update_data = {
                "name": p_name.strip(),
                "region": p_region,
                "commune": p_commune,
                "latitude": lat_val,
                "longitude": lng_val,
                "terrain_rol": p_rol if p_rol.strip() else None,
                "block": p_block if p_block.strip() else None,
                "lot": p_lot if p_lot.strip() else None
            }
            
            with st.spinner("Guardando cambios..."):
                res = update_project_context_db(p["id"], update_data, st.session_state["jwt_token"])
                if res["success"]:
                    st.success("Proyecto actualizado con éxito.")
                    st.session_state["projects"] = list_user_projects(st.session_state["jwt_token"])
                    for updated_p in st.session_state["projects"]:
                        if updated_p["id"] == p["id"]:
                            st.session_state["active_project"] = updated_p
                            break
                    st.rerun()
                else:
                    st.error(f"Error al guardar: {res['error']}")


@st.dialog("Eliminar Documento")
def confirm_delete_document(doc_id: str, doc_name: str, project_id: str, oguc_content: str):
    st.write(f"¿Estás seguro de que deseas eliminar el documento **{doc_name}** de este proyecto?")
    st.write("Esta acción recalculará toda la viabilidad y reconstruirá el contexto del proyecto")
    st.write("")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("Sí, Eliminar", type="primary", use_container_width=True):
            with st.spinner("Eliminando documento y reconstruyendo contexto..."):
                from app.db import delete_project_document
                from app.ai_verifier import rebuild_project_context
                
                del_res = delete_project_document(doc_id, st.session_state["jwt_token"])
                if del_res["success"]:
                    rebuild_res = rebuild_project_context(project_id, st.session_state["jwt_token"], oguc_content)
                    if rebuild_res["success"]:
                        st.success("Documento eliminado con éxito y contexto reconstruido.")
                        st.session_state["projects"] = list_user_projects(st.session_state["jwt_token"])
                        for updated_p in st.session_state["projects"]:
                            if updated_p["id"] == project_id:
                                st.session_state["active_project"] = updated_p
                                break
                        st.session_state["viewing_pdf_id"] = None
                        st.session_state["docs_cache"] = None
                        st.session_state["history_cache"] = None
                        st.rerun()
                    else:
                        st.error(f"Error al reconstruir contexto: {rebuild_res['error']}")
                else:
                    st.error(f"Error al eliminar: {del_res['error']}")
    with col_c2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()