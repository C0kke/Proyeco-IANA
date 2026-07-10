import streamlit as st
import os
import uuid
import json
import base64
import re
from datetime import datetime

from app.db import (
    list_project_documents,
    upload_project_document,
    save_document_analysis,
    update_project_context_db,
    list_user_projects,
    get_document_file_bytes
)
from app.ai_verifier import (
    evaluate_document_individually,
    consolidate_project_context
)
from app.report import render_html_report, render_pdf_report
from components.dialogs import render_edit_project_modal, confirm_delete_document, render_delete_project_modal

def is_duplicate_or_copy_name(name1: str, name2: str) -> bool:
    """
    Compara dos nombres de archivo ignorando mayúsculas/minúsculas, extensiones
    y sufijos de copia comunes como (1), - copia, _1, etc.
    """
    base1 = os.path.splitext(name1)[0].lower().strip()
    base2 = os.path.splitext(name2)[0].lower().strip()
    
    suffix_pattern = re.compile(r'(\s*[\(\-_]\d+\)?|\s*-\s*copia)$', re.IGNORECASE)
    
    clean1 = suffix_pattern.sub('', base1).strip()
    clean2 = suffix_pattern.sub('', base2).strip()
    
    return clean1 == clean2

def get_jobs_history(project_id: str, results_dir: str):
    if not os.path.exists(results_dir):
        return []
    try:
        files = [f for f in os.listdir(results_dir) if f.endswith(".json")]
    except OSError as err:
        print(f"Error al listar archivos de resultados locales: {err}")
        return []
        
    history = []
    for f in files:
        path = os.path.join(results_dir, f)
        try:
            mtime = os.path.getmtime(path)
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if data.get("user_id") == st.session_state["user"].id:
                has_match = False
                if "project_id" in data:
                    has_match = (data["project_id"] == project_id)
                else:
                    has_match = (data.get("project_name") == st.session_state["active_project"]["name"])
                
                if has_match:
                    history.append({
                        "job_id": data.get("job_id"),
                        "filename": data.get("filename"),
                        "project_name": data.get("project_name", data.get("filename")),
                        "success_probability": data.get("success_probability", 0.0),
                        "is_valid": data.get("is_valid", True),
                        "mtime": mtime
                    })
        except (OSError, ValueError) as err:
            print(f"Error leyendo archivo de historial local {path}: {err}")
            
    history.sort(key=lambda x: x["mtime"], reverse=True)
    return history

def display_results(result_data):
    st.success(f"Análisis normativo completado: **{result_data['project_name']}**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Viabilidad Normativa",
            value=f"{result_data['success_probability']:.1f}%",
        )
    with col2:
        st.metric(
            label="Infracciones Detectadas",
            value=len(result_data.get("infractions", []))
        )
        
    is_valid = result_data.get("is_valid", True)
    infractions = result_data.get("infractions", [])
    has_high_severity = any(inf.get("severity") == "ALTA" for inf in infractions)
    
    if not is_valid:
        status_value = "Rechazado (No Válido)"
    elif has_high_severity:
        status_value = "Rechazado"
    elif infractions:
        status_value = "Aprobado con obs."
    else:
        status_value = "Aprobado"
        
    with col3:
        st.metric(
            label="Estado",
            value=status_value,
        )
        
    st.subheader("Resumen Ejecutivo (Consolidado por IA)", anchor=False)
    st.info(result_data.get("summary_notes", "Sin notas del análisis."))

    st.subheader("Detalle de Infracciones de la OGUC", anchor=False)
    
    if infractions:
        for idx, inf in enumerate(infractions):
            severity = inf.get("severity", "ALTA")
            color = "red" if severity == "ALTA" else "orange" if severity == "MEDIA" else "blue"
            
            with st.expander(f"[{severity}] {inf.get('rule_id')} - {inf.get('description')[:80]}..."):
                st.markdown(f"**Artículo OGUC:** `{inf.get('rule_id')}`")
                st.markdown(f"**Severidad:** :{color}[{severity}]")
                st.markdown(f"**Evidencia en documento:** `{inf.get('evidence')}`")
                st.markdown(f"**Justificación legal:** {inf.get('justification')}")
                st.markdown(f"**Descripción completa:** {inf.get('description')}")
    else:
        st.success("No se detectaron infracciones a la OGUC de Chile en este documento.")

    st.subheader("Descargar Reportes", anchor=False)
    
    html_content = render_html_report(result_data["filename"], result_data)
    try:
        pdf_content = render_pdf_report(result_data["filename"], result_data)
    except Exception as e:
        pdf_content = None
        st.error(f"Error al generar el PDF: {e}")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            label="Descargar Reporte HTML",
            data=html_content,
            file_name=f"reporte_iana_{result_data['job_id']}.html",
            mime="text/html",
            use_container_width=True
        )
    with col_d2:
        if pdf_content:
            st.download_button(
                label="Descargar Reporte PDF",
                data=pdf_content,
                file_name=f"reporte_iana_{result_data['job_id']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.button("Reporte PDF no disponible", disabled=True, use_container_width=True)

def render_project_dashboard(oguc_content: str, uploads_dir: str, results_dir: str):
    p = st.session_state["active_project"]
    if not p:
        st.warning("No hay un proyecto activo seleccionado.")
        return
        
    if st.session_state["docs_cache"] is None:
        st.session_state["docs_cache"] = list_project_documents(p["id"], st.session_state["jwt_token"])
    if st.session_state["history_cache"] is None:
        st.session_state["history_cache"] = get_jobs_history(p["id"], results_dir)
        
    type_mapping = {
        "private_housing": "Vivienda Privada (Unifamiliar/Condominios)",
        "large_scale_real_estate": "Inmobiliario de Gran Envergadura (Comercial, Industrial)",
        "public_spaces_green_areas": "Espacios Públicos y Áreas Verdes",
        "other": "Otro"
    }
    
    col_p1, col_p2 = st.columns([4, 1])
    with col_p1:
        st.markdown(
            f"""
            <div class="project-card">
                <div class="project-header">Proyecto: {p['name']}</div>
                <div class="project-meta">
                    Ubicación: <b>{p['commune']}, {p['region']}</b> (Lat: {p['latitude'] or 'N/A'}, Lng: {p['longitude'] or 'N/A'}) <br>
                    Tipo de Proyecto: <b>{type_mapping.get(p['project_type'], p['project_type'])}</b> | 
                    ROL Terreno: <b>{p['terrain_rol'] or 'N/A'}</b> | Manzana: <b>{p['block'] or 'N/A'}</b> | Lote: <b>{p['lot'] or 'N/A'}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_p2:
        st.write("")
        st.write("")
        if st.button("Editar Proyecto", use_container_width=True):
            render_edit_project_modal()
        if st.button("Eliminar Proyecto", use_container_width=True, key="delete_project_dashboard_btn"):
            render_delete_project_modal(p["id"], p["name"])
            
    docs = st.session_state["docs_cache"] or []
    uploaded_types = {d["document_type"] for d in docs}
    
    missing_docs = []
    if "site_plan" not in uploaded_types:
        missing_docs.append("Plano de emplazamiento")
    if "sections" not in uploaded_types:
        missing_docs.append("Plano de arquitectura")
    if "elevations" not in uploaded_types:
        missing_docs.append("Elevaciones / cortes")
    if "ett" not in uploaded_types:
        missing_docs.append("Techumbre")
        
    if missing_docs:
        missing_str = ", ".join(missing_docs)
        st.warning(
            f"Falta subir los siguientes documentos para este proyecto: {missing_str}."
        )
        
    st.write("")
    
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "Validar Nuevo Documento"
    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = "file_uploader_init"
        
    tab_options = ["Validar Nuevo Documento", "Documentos Asociados", "Historial de Aprobación"]
    
    st.radio(
        "Navegación",
        options=tab_options,
        key="active_tab",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if st.session_state["active_tab"] == "Validar Nuevo Documento":
        st.subheader("Subir Documentación del Proyecto", anchor=False)
        st.markdown("Sube planos, especificaciones técnicas o elevaciones para verificar su cumplimiento normativo.")
        
        docs_list = st.session_state["docs_cache"] or []
        if docs_list:
            st.markdown("**Documentos integrados en la memoria y contexto del proyecto:**")
            badges_html = '<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">'
            for d in docs_list:
                dtype = d.get("document_type")
                fname = d.get("file_name", "")
                if fname.startswith("[Techumbre] "):
                    fname = fname[len("[Techumbre] "):]
                    dtype_label = "Techumbre"
                elif fname.startswith("[Otro] "):
                    fname = fname[len("[Otro] "):]
                    dtype_label = "Otro"
                else:
                    labels = {
                        "cip": "CIP",
                        "ett": "ETT",
                        "site_plan": "Emplazamiento",
                        "sections": "Arquitectura",
                        "elevations": "Elevaciones/Cortes",
                        "other": "Otro"
                    }
                    dtype_label = labels.get(dtype, dtype)
                
                badges_html += f'<span style="background-color: #f1f5f9; color: #334155; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: 500; display: inline-flex; align-items: center; gap: 4px;">📄 {fname} <small style="color: #64748b; font-weight: 400;">({dtype_label})</small></span>'
            badges_html += '</div>'
            st.markdown(badges_html, unsafe_allow_html=True)
        else:
            st.markdown("<p style='color: #64748b; font-size: 12px; font-style: italic; margin-bottom: 15px;'>No hay documentos en la memoria de este proyecto. El primer archivo que subas inicializará el contexto.</p>", unsafe_allow_html=True)

        st.info(
            "**Flujo de Trabajo:** Al presionar 'Iniciar Validación', el archivo se "
            "guardará en la base de datos del proyecto y la IA lo analizará. "
            "Luego, **IANA evaluará incrementalmente todo el conjunto del proyecto**, "
            "incluyendo este y los documentos previamente cargados."
        )
        
        doc_type = st.selectbox(
            "Tipo de Documento a Subir",
            options=["cip", "ett", "site_plan", "sections", "elevations", "techumbre", "other"],
            format_func=lambda x: {
                "cip": "Certificado de Informaciones Previas (CIP)",
                "ett": "Especificaciones Técnicas (ETT)",
                "site_plan": "Plano de emplazamiento",
                "sections": "Plano de arquitectura",
                "elevations": "Elevaciones / cortes",
                "techumbre": "Techumbre",
                "other": "Otro documento"
            }[x]
        )
        
        uploaded_file = st.file_uploader(
            "Selecciona el archivo PDF o Word (.docx) del proyecto:",
            type=["pdf", "docx"],
            key=st.session_state["file_uploader_key"],
            help="El archivo debe tener texto seleccionable o ser un archivo de Word (.docx)."
        )
        
        active_job_id = st.query_params.get("job_id")
        
        p_obs = st.text_area(
            "Observaciones / Contexto Adicional para este Documento",
            value="",
            placeholder="Entrega contexto sobre este documento en particular para guiar a la IA...",
            help="Estas observaciones se enviarán a la IA para guiar la revisión."
        )
        
        if uploaded_file is not None:
            st.info(f"Archivo listo: **{uploaded_file.name}** ({uploaded_file.size / 1024:.2f} KB)")
            
            duplicate_doc = None
            for d in docs_list:
                clean_db_name = d.get("file_name", "")
                if clean_db_name.startswith("[Techumbre] "):
                    clean_db_name = clean_db_name[len("[Techumbre] "):]
                elif clean_db_name.startswith("[Otro] "):
                    clean_db_name = clean_db_name[len("[Otro] "):]
                
                if is_duplicate_or_copy_name(uploaded_file.name, clean_db_name):
                    duplicate_doc = clean_db_name
                    break
            
            confirm_upload = True
            if duplicate_doc:
                st.warning(f"El archivo **'{uploaded_file.name}'** parece ser un duplicado o una copia de **'{duplicate_doc}'** que ya fue subido a este proyecto.")
                confirm_upload = st.checkbox("Entiendo que es una copia y deseo subirlo de todas formas", value=False)
                
            button_disabled = not confirm_upload
            if st.button("Iniciar Validación Normativa con IA", type="primary", use_container_width=True, disabled=button_disabled):
                job_id = str(uuid.uuid4())
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                pdf_path = os.path.join(uploads_dir, f"{job_id}{ext}")
                
                try:
                    with st.spinner("Procesando y almacenando archivo en Storage..."):
                        file_bytes = uploaded_file.getvalue()
                        
                        db_doc_type = doc_type
                        display_filename = uploaded_file.name
                        if doc_type == "techumbre":
                            db_doc_type = "other"
                            display_filename = f"[Techumbre] {uploaded_file.name}"
                        elif doc_type == "other":
                            display_filename = f"[Otro] {uploaded_file.name}"
                        
                        db_res = upload_project_document(
                            user_id=st.session_state["user"].id,
                            project_id=p["id"],
                            file_name=display_filename,
                            file_bytes=file_bytes,
                            document_type=db_doc_type,
                            jwt_token=st.session_state["jwt_token"]
                        )
                        
                        with open(pdf_path, "wb") as handle:
                            handle.write(file_bytes)
                            
                        if db_res.get("storage_location") == "local_fallback":
                            st.warning("No se pudo conectar con el storage remoto. El archivo se guardó localmente en modo fallback de emergencia y el análisis continuará normalmente.")
                        else:
                            st.success("Archivo guardado y respaldado en Supabase Storage con políticas RLS de seguridad.")

                    with st.spinner("Extrayendo texto del archivo..."):
                        from app.pdf_extract import extract_text_blocks
                        blocks = extract_text_blocks(pdf_path)
                        plan_text = "\n".join([b.text for b in blocks])
                        
                    if not plan_text.strip():
                        raise ValueError("El archivo no contiene texto legible (sin capa de texto OCR o archivo vacío).")
                        
                    with st.spinner("Realizando análisis individual de este documento (Gemini AI)..."):
                        doc_analysis = evaluate_document_individually(
                            doc_text=plan_text,
                            doc_type=doc_type,
                            oguc_text=oguc_content,
                            observaciones=p_obs.strip()
                        )
                        
                        if db_res.get("success") and "document" in db_res:
                            doc_id = db_res["document"].get("id")
                            if doc_id:
                                try:
                                    save_document_analysis({
                                        "document_id": doc_id,
                                        "extracted_text_summary": doc_analysis.document_summary,
                                        "infractions": [inf.model_dump() for inf in doc_analysis.infractions],
                                        "metadata": {
                                            **doc_analysis.extracted_metadata,
                                            "observations": p_obs.strip(),
                                            "is_valid": doc_analysis.is_valid_architectural_doc
                                        }
                                    }, st.session_state["jwt_token"])
                                except Exception as db_err:
                                    st.warning(f"No se pudo guardar el análisis individual en la base de datos: {db_err}")

                    with st.spinner("Consolidando contexto histórico e integrando alertas..."):
                        existing_context = p.get("consolidated_context", "") or "Proyecto inicializado."
                        existing_infractions = p.get("consolidated_infractions", []) or []
                        
                        consolidated = consolidate_project_context(
                            project_metadata=p,
                            existing_context=existing_context,
                            existing_infractions=existing_infractions,
                            new_doc_analysis=doc_analysis,
                            oguc_text=oguc_content
                        )
                        
                        update_res = update_project_context_db(
                            project_id=p["id"],
                            context_data={
                                "consolidated_context": consolidated.consolidated_context,
                                "consolidated_infractions": [inf.model_dump() for inf in consolidated.consolidated_infractions],
                                "success_probability": consolidated.success_probability,
                                "extracted_metadata": {
                                    **consolidated.extracted_metadata,
                                    "is_valid": consolidated.is_valid_project_documentation
                                },
                                "terrain_rol": consolidated.extracted_metadata.get("rol_terreno", p.get("terrain_rol")),
                                "block": consolidated.extracted_metadata.get("manzana", p.get("block")),
                                "lot": consolidated.extracted_metadata.get("lote", p.get("lote"))
                            },
                            jwt_token=st.session_state["jwt_token"]
                        )
                        
                        if update_res["success"]:
                            st.session_state["projects"] = list_user_projects(st.session_state["jwt_token"])
                            for updated_p in st.session_state["projects"]:
                                if updated_p["id"] == p["id"]:
                                    st.session_state["active_project"] = updated_p
                                    break
                        else:
                            raise ValueError(f"Error al actualizar el contexto consolidado en la DB: {update_res['error']}")
                            
                    result_data = {
                        "job_id": job_id,
                        "user_id": st.session_state["user"].id,
                        "project_id": p["id"],
                        "filename": uploaded_file.name,
                        "project_name": p["name"],
                        "success_probability": consolidated.success_probability,
                        "is_valid": consolidated.is_valid_project_documentation,
                        "infractions": [inf.model_dump() for inf in consolidated.consolidated_infractions],
                        "summary_notes": consolidated.consolidated_context,
                        "observaciones": p_obs.strip()
                    }
                    
                    out_json = os.path.join(results_dir, f"{job_id}.json")
                    with open(out_json, "w", encoding="utf-8") as handle:
                        json.dump(result_data, handle, ensure_ascii=False, indent=2)
                        
                    out_html = os.path.join(results_dir, f"{job_id}.html")
                    with open(out_html, "w", encoding="utf-8") as handle:
                        handle.write(render_html_report(uploaded_file.name, result_data))
                        
                    st.session_state["file_uploader_key"] = f"file_uploader_{uuid.uuid4()}"
                    st.session_state["docs_cache"] = None
                    st.session_state["history_cache"] = None
                    st.query_params["job_id"] = job_id
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Ocurrió un error durante la validación: {e}")
                
        if active_job_id:
            st.divider()
            path = os.path.join(results_dir, f"{active_job_id}.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        result_data = json.load(handle)
                    if result_data.get("user_id") == st.session_state["user"].id:
                        display_results(result_data)
                    else:
                        st.error("No tienes autorización para ver este reporte.")
                except (OSError, ValueError) as err:
                    st.error(f"Error cargando el archivo de resultados: {err}")
            else:
                st.error("El análisis seleccionado no existe o fue eliminado.")
                
    elif st.session_state["active_tab"] == "Documentos Asociados":
        st.subheader("Documentos Asociados al Proyecto", anchor=False)
        st.markdown("Lista de planos y especificaciones técnicas oficiales cargados en este proyecto:")
        
        def get_display_label(doc):
            dtype = doc.get("document_type")
            fname = doc.get("file_name", "")
            if dtype == "other":
                if fname.startswith("[Techumbre]"):
                    return "Techumbre"
                elif fname.startswith("[Otro]"):
                    return "Otro documento"
                return "Otro documento"
            
            labels = {
                "cip": "Certificado de Informaciones Previas (CIP)",
                "ett": "Especificaciones Técnicas (ETT)",
                "site_plan": "Plano de emplazamiento",
                "sections": "Plano de arquitectura",
                "elevations": "Elevaciones / cortes"
            }
            return labels.get(dtype, dtype)
            
        docs = st.session_state["docs_cache"] or []
        if docs:
            for d in docs:
                dt_str = ""
                if d.get("created_at"):
                    try:
                        dt_obj = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
                        st.session_state.setdefault("chile_tz", None)
                        if st.session_state["chile_tz"]:
                            dt_chile = dt_obj.astimezone(st.session_state["chile_tz"])
                            dt_str = dt_chile.strftime("%Y-%m-%d %H:%M")
                        else:
                            dt_str = str(d["created_at"])[:16]
                    except Exception:
                        dt_str = str(d["created_at"])[:16]
                        
                col_d1, col_d2, col_d3, col_d4 = st.columns([3, 2, 1, 1])
                with col_d1:
                    display_name = d.get('file_name', '')
                    if display_name.startswith("[Techumbre] "):
                        display_name = display_name[len("[Techumbre] "):]
                    elif display_name.startswith("[Otro] "):
                        display_name = display_name[len("[Otro] "):]
                    st.markdown(f"**{display_name}**")
                    st.caption(f"Subido el {dt_str}")
                with col_d2:
                    st.markdown(f"**Tipo:** {get_display_label(d)}")
                with col_d3:
                    if st.button("Ver", key=f"view_assoc_pdf_{d.get('id')}", use_container_width=True):
                        st.session_state["viewing_pdf_id"] = d.get("id")
                        st.rerun()
                with col_d4:
                    if st.button("Eliminar", key=f"delete_assoc_doc_{d.get('id')}", use_container_width=True):
                        confirm_delete_document(d.get("id"), display_name, p["id"], oguc_content)
                st.divider()
                
            viewing_id = st.session_state.get("viewing_pdf_id")
            if viewing_id:
                selected_doc = next((doc for doc in docs if doc["id"] == viewing_id), None)
                if selected_doc:
                    st.subheader(f"Visualizador: {selected_doc.get('file_name')}", anchor=False)
                    
                    with st.spinner("Cargando archivo PDF..."):
                        file_bytes = get_document_file_bytes(selected_doc, st.session_state["jwt_token"])
                        
                    if file_bytes:
                        col_ctrl1, col_ctrl2 = st.columns([1, 1])
                        with col_ctrl1:
                            st.download_button(
                                label="Descargar PDF original",
                                data=file_bytes,
                                file_name=selected_doc.get("file_name"),
                                mime="application/pdf",
                                key="dl_viewing_pdf",
                                use_container_width=True
                            )
                        with col_ctrl2:
                            if st.button("Cerrar Visualizador", use_container_width=True):
                                st.session_state["viewing_pdf_id"] = None
                                st.rerun()
                                
                        try:
                            base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
                            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" style="border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 15px;"></iframe>'
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error al renderizar el visualizador PDF: {e}")
                    else:
                        st.error("No se pudo obtener el archivo de este documento en el almacenamiento.")
                        if st.button("Cerrar", use_container_width=True):
                            st.session_state["viewing_pdf_id"] = None
                            st.rerun()
        else:
            st.info("Aún no se han subido documentos a este proyecto. Ve a la pestaña 'Validar Nuevo Documento' para subir tu primer plano o ETT.")
            
    else:
        st.subheader("Historial de Aprobación del Proyecto", anchor=False)
        history_jobs = st.session_state["history_cache"] or []
        
        if history_jobs:
            st.markdown("Línea de tiempo de evaluaciones normativas y cambios en el porcentaje de aprobación del proyecto:")
            
            history_sorted = sorted(history_jobs, key=lambda x: x["mtime"])
            
            deltas = {}
            prev_prob = None
            for idx, job in enumerate(history_sorted):
                curr_prob = job["success_probability"]
                if prev_prob is None:
                    delta = None
                else:
                    delta = curr_prob - prev_prob
                deltas[job["job_id"]] = delta
                prev_prob = curr_prob
                
            history_recent = list(reversed(history_sorted))
            
            for job in history_recent:
                st.session_state.setdefault("chile_tz", None)
                if st.session_state["chile_tz"]:
                    dt = datetime.fromtimestamp(job['mtime'], tz=st.session_state["chile_tz"])
                    dt_str = dt.strftime('%Y-%m-%d %H:%M')
                else:
                    dt_str = str(datetime.fromtimestamp(job['mtime']))[:16]
                    
                delta_val = deltas.get(job["job_id"])
                
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    st.markdown(f"**Archivo Subido:** `{job['filename']}`")
                    st.caption(f"Evaluación realizada el {dt_str}")
                with col_h2:
                    if delta_val is None:
                        st.metric(
                            label="Viabilidad", 
                            value=f"{job['success_probability']:.1f}%",
                            help="Porcentaje inicial del proyecto"
                        )
                    elif delta_val == 0:
                        st.metric(
                            label="Viabilidad",
                            value=f"{job['success_probability']:.1f}%",
                            delta="+0.0%",
                            delta_color="off"
                        )
                    else:
                        st.metric(
                            label="Viabilidad", 
                            value=f"{job['success_probability']:.1f}%",
                            delta=f"{delta_val:+.1f}%",
                            delta_color="normal" if delta_val > 0 else "inverse"
                        )
                st.divider()
        else:
            st.info("Aún no se han registrado evaluaciones normativas para este proyecto. Sube un documento en la pestaña 'Validar Nuevo Documento' para comenzar.")

    st.divider()
    col_g1, col_g2 = st.columns([1, 3])
    with col_g1:
        st.metric(
            label="Cumplimiento Global del Proyecto",
            value=f"{float(p.get('success_probability', 0.0)):.1f}%"
        )
    with col_g2:
        st.markdown("**Contexto Consolidado del Proyecto (Memoria IA):**")
        st.caption(p.get("consolidated_context", "Aún no se han cargado documentos en este proyecto para consolidar un contexto."))