import streamlit as st
from app.db import sign_in_user, sign_up_user, list_user_projects
from app.version import __version__

def render_auth_page():
    st.title(f"IANA v{__version__} — Validador Normativo de Proyectos")
    st.markdown("Verifica planos y especificaciones técnicas contra la **Ordenanza General de Urbanismo y Construcción (OGUC) de Chile** utilizando Inteligencia Artificial.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(
            """
            ### ¿Qué es IANA?
            IANA permite automatizar la revisión de planos de arquitectura, especificaciones técnicas y CIPs (Certificados de Informaciones Previas).
            
            *   **Contexto Acumulativo de IA:** IANA analiza cada documento y actualiza de manera incremental el contexto del proyecto, permitiendo que un plano resuelva las alertas de una especificación técnica previa.
            *   **Seguridad RLS:** Acceso exclusivo a tus proyectos personales.
            *   **Resguardo de Experiencia:** En caso de fallas de conexión, tus archivos se respaldan localmente de inmediato para que sigas trabajando.
            """
        )
        
    with col2:
        auth_tab1, auth_tab2 = st.tabs(["Iniciar Sesión", "Crear Cuenta"])
        
        with auth_tab1:
            st.subheader("Acceder a IANA")
            login_email = st.text_input("Correo electrónico", key="login_email")
            login_password = st.text_input("Contraseña", type="password", key="login_password")
            
            if st.button("Iniciar Sesión", type="primary", use_container_width=True):
                if login_email and login_password:
                    with st.spinner("Autenticando..."):
                        res = sign_in_user(login_email, login_password)
                        if res["success"]:
                            st.session_state["user"] = res["user"]
                            st.session_state["jwt_token"] = res["jwt_token"]
                            st.session_state["cookie_to_set"] = res["jwt_token"]
                            st.session_state["logged_out"] = False
                            st.success("¡Sesión iniciada con éxito!")
                            st.session_state["projects"] = list_user_projects(res["jwt_token"])
                            st.session_state["projects_loaded"] = True
                            st.session_state["active_project"] = None
                            st.rerun()
                        else:
                            st.error(f"Error de credenciales: {res['error']}")
                else:
                    st.warning("Por favor rellena todos los campos.")
                    
        with auth_tab2:
            st.subheader("Crear Cuenta Nueva")
            reg_email = st.text_input("Correo electrónico", key="reg_email")
            reg_password = st.text_input("Contraseña (mínimo 6 caracteres)", type="password", key="reg_password")
            reg_name = st.text_input("Nombre Completo", key="reg_name")
            reg_phone = st.text_input("Teléfono de Contacto", key="reg_phone")
            reg_rut = st.text_input("RUT (ej: 12.345.678-9)", key="reg_rut")
            reg_role = st.selectbox(
                "Rol del Usuario",
                options=["Arquitecto", "Desarrollador Independiente", "Ingeniería", "Construcción", "Admin. Pública (DOM)", "Jefatura Obras", "Gerencia"]   
            )
            
            if st.button("Registrarse", type="primary", use_container_width=True):
                if reg_email and reg_password and reg_name and reg_rut:
                    with st.spinner("Registrando..."):
                        res = sign_up_user(
                            email=reg_email,
                            password=reg_password,
                            name=reg_name,
                            phone=reg_phone,
                            rut=reg_rut,
                            role=reg_role
                        )
                        if res["success"]:
                            st.success("¡Registro completado! Ahora puedes iniciar sesión en la pestaña correspondiente.")
                        else:
                            st.error(f"Error al registrar: {res['error']}")
                else:
                    st.warning("Completa los campos obligatorios (Correo, Contraseña, Nombre y RUT).")