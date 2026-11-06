import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="AuditaCloud Enterprise", layout="wide", page_icon="🔒")

# --- CONTROL DE SESIÓN Y BASE DE DATOS SIMULADA ---
if 'audits' not in st.session_state:
    st.session_state.audits = [
        {"id": "AUD-001", "proceso": "Contabilidad y Finanzas", "riesgo": "Alto", "normativa": "SOX (Sección 404)", "estado": "En Ejecución", "progreso": 60},
        {"id": "AUD-002", "proceso": "Gestión de Calidad Operativa", "riesgo": "Medio", "normativa": "ISO 9001:2015", "estado": "Planificado", "progreso": 10},
        {"id": "AUD-003", "proceso": "Seguridad de TI", "riesgo": "Crítico", "normativa": "ISO 27001 / SOX", "estado": "Finalizado", "progreso": 100},
    ]

if 'findings' not in st.session_state:
    st.session_state.findings = [
        {"id": "HALL-01", "auditoria": "AUD-001", "normativa_ref": "SOX - Control de Accesos", "descripcion": "Falta de conciliación bancaria mensual", "criticidad": "Alta", "estado": "Abierto", "comentario_auditado": ""},
        {"id": "HALL-02", "auditoria": "AUD-001", "normativa_ref": "SOX - Segregación de Funciones", "descripcion": "Accesos de usuarios duplicados en ERP", "criticidad": "Media", "estado": "En Proceso", "comentario_auditado": "En revisión por TI."},
    ]

# --- MÓDULO DE CONTROL DE ACCESO (ROLES) ---
st.sidebar.title("🔒 AuditaCloud Enterprise")
st.sidebar.markdown("---")

st.sidebar.subheader("👤 Control de Acceso")
rol_usuario = st.sidebar.selectbox("Seleccione su Rol:", ["Auditor Líder (Admin)", "Auditado (Líder de Proceso)"])

# Menú dinámico adaptado según el Rol
if rol_usuario == "Auditor Líder (Admin)":
    menu = st.sidebar.radio(
        "Menú de Módulos:",
        ["📊 Dashboard General", "📅 Planificación y Riesgos (ISO/SOX)", "📝 Ejecución y Papeles", "🔔 Seguimiento de Hallazgos", "📥 Generación de Reportes"]
    )
    st.sidebar.info("Permisos: **Lectura, Escritura y Firmas**")
else:
    menu = st.sidebar.radio(
        "Menú de Módulos:",
        ["📊 Dashboard General", "🔔 Responder a Hallazgos"]
    )
    st.sidebar.warning("Permisos: **Responder acciones correctivas**")

st.sidebar.markdown("---")
st.sidebar.caption(f"Entorno Seguro • {datetime.now().strftime('%Y-%m-%d')}")

# ==========================================
# MÓDULO: DASHBOARD GENERAL (Ambos Roles)
# ==========================================
if menu == "📊 Dashboard General":
    st.title("📊 Panel de Control Directivo")
    st.markdown(f"Bienvenido al sistema. Rol activo actual: **{rol_usuario}**")
    
    df_audits = pd.DataFrame(st.session_state.audits)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Auditorías", len(df_audits))
    col2.metric("En Ejecución", len(df_audits[df_audits['estado'] == 'En Ejecución']))
    col3.metric("Finalizadas", len(df_audits[df_audits['estado'] == 'Finalizado']))
    col4.metric("Hallazgos Abiertos", len([f for f in st.session_state.findings if f['estado'] != 'Cerrado']))
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Progreso y Marco Normativo Asociado")
        fig_bar = px.bar(df_audits, x='proceso', y='progreso', color='normativa', text='progreso',
                         labels={'progreso': '% de Avance', 'proceso': 'Proceso Organismo'})
        st.plotly_chart(fig_bar, use_container_width=True)
    with c2:
        st.subheader("Criticidad de Hallazgos Totales")
        df_find = pd.DataFrame(st.session_state.findings)
        fig_pie = px.pie(df_find, names='criticidad', color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# MÓDULO: PLANIFICACIÓN Y RIESGOS (Solo Auditor)
# ==========================================
elif menu == "📅 Planificación y Riesgos (ISO/SOX)":
    st.title("📅 Planificación Anual y Matrices Normativas")
    
    with st.expander("➕ Vincular Nueva Auditoría al Plan de Cumplimiento", expanded=False):
        with st.form("form_planificacion"):
            nuevo_proceso = st.text_input("Área o Proceso:")
            normativa_select = st.selectbox("Marco de Cumplimiento Target:", ["ISO 9001:2015 (Calidad)", "SOX Sección 404 (Financiero)", "ISO 27001 (Seguridad)", "ISO 14001 (Ambiental)", "Multi-Norma"])
            probabilidad = st.slider("Probabilidad de Ocurrencia (1-5)", 1, 5, 3)
            impacto = st.slider("Impacto en la Organización (1-5)", 1, 5, 3)
            
            score = probabilidad * impacto
            riesgo_calculado = "Crítico" if score >= 15 else ("Alto" if score >= 8 else "Medio")
            
            btn_guardar = st.form_submit_button("Añadir al Plan de Trabajo")
            if btn_guardar and nuevo_proceso:
                st.session_state.audits.append({
                    "id": f"AUD-00{len(st.session_state.audits) + 1}",
                    "proceso": nuevo_proceso,
                    "riesgo": riesgo_calculado,
                    "normativa": normativa_select,
                    "estado": "Planificado",
                    "progreso": 0
                })
                st.success("Nueva auditoría agregada con alineación normativa.")
                st.rerun()

    st.subheader("Universo Normativo Planificado")
    st.dataframe(pd.DataFrame(st.session_state.audits), use_container_width=True)

# ==========================================
# MÓDULO: EJECUCIÓN Y PAPELES (Solo Auditor)
# ==========================================
elif menu == "📝 Ejecución y Papeles":
    st.title("📝 Ejecución en Campo y Evidencias")
    
    df_audits = pd.DataFrame(st.session_state.audits)
    seleccion = st.selectbox("Seleccione Auditoría:", df_audits['id'] + " - " + df_audits['proceso'])
    id_sel = seleccion.split(" - ")[0]
    
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("Documentar Hallazgo")
        with st.form("form_hallazgo"):
            normativa_ref = st.text_input("Cláusula / Punto de Control Afectado (Ej: Cláusula 9.2 ISO o Control Internal SOX):")
            desc_hallazgo = st.text_area("Descripción de la Deficiencia / Brecha:")
            criticidad_hallazgo = st.selectbox("Criticidad del Hallazgo:", ["Baja", "Media", "Alta", "Crítica"])
            st.file_uploader("Evidencia Digital Soportada")
            
            if st.form_submit_button("Guardar Papel de Trabajo"):
                st.session_state.findings.append({
                    "id": f"HALL-0{len(st.session_state.findings) + 1}",
                    "auditoria": id_sel,
                    "normativa_ref": normativa_ref,
                    "descripcion": desc_hallazgo,
                    "criticidad": criticidad_hallazgo,
                    "estado": "Abierto",
                    "comentario_auditado": ""
                })
                st.success("Hallazgo certificado con sello de auditoría.")
                st.rerun()
                
    with col_der:
        st.subheader("Evidencias Levantadas")
        df_f = pd.DataFrame(st.session_state.findings)
        st.dataframe(df_f[df_f['auditoria'] == id_sel][['id', 'normativa_ref', 'descripcion', 'criticidad']], use_container_width=True)

# ==========================================
# MÓDULO: SEGUIMIENTO DE HALLAZGOS (Solo Auditor)
# ==========================================
elif menu == "🔔 Seguimiento de Hallazgos":
    st.title("🔔 Panel de Gestión de Brechas y Cierre")
    
    for idx, row in pd.DataFrame(st.session_state.findings).iterrows():
        with st.expander(f"🔎 {row['id']} - Auditoría {row['auditoria']} ({row['criticidad']})", expanded=True):
            st.write(f"**Referencia Normativa:** {row['normativa_ref']}")
            st.write(f"**Falla Detectada:** {row['descripcion']}")
            st.info(f"**Respuesta del Auditado:** {row['comentario_auditado'] if row['comentario_auditado'] else 'Sin respuesta aún'}")
            
            nuevo_est = st.selectbox("Actualizar Acción de Cierre:", ["Abierto", "En Proceso", "Cerrado"], index=["Abierto", "En Proceso", "Cerrado"].index(row['estado']), key=f"aud_{row['id']}")
            if nuevo_est != row['estado']:
                st.session_state.findings[idx]['estado'] = nuevo_est
                st.success("Estado de control modificado.")
                st.rerun()

# ==========================================
# MÓDULO: RESPONDER A HALLAZGOS (Solo Auditado)
# ==========================================
elif menu == "🔔 Responder a Hallazgos":
    st.title("🔔 Panel de Acciones Correctivas (Área Auditada)")
    st.markdown("Por favor, ingrese sus planes de acción y comentarios de remediación para las brechas asignadas.")
    
    hay_pendientes = False
    for idx, row in pd.DataFrame(st.session_state.findings).iterrows():
        if row['estado'] != "Cerrado":
            hay_pendientes = True
            with st.form(f"form_reply_{row['id']}"):
                st.markdown(f"#### Hallazgo: {row['id']} ({row['criticidad']})")
                st.write(f"**Control Incumplido:** {row['normativa_ref']}")
                st.write(f"**Evidencia del Auditor:** {row['descripcion']}")
                
                comentario = st.text_area("Plan de Acción / Compromiso de Remediación:", value=row['comentario_auditado'])
                
                if st.form_submit_button(f"Enviar Respuesta {row['id']}"):
                    st.session_state.findings[idx]['comentario_auditado'] = comentario
                    st.session_state.findings[idx]['estado'] = "En Proceso"
                    st.success("Plan de acción enviado al Auditor Líder con éxito.")
                    st.rerun()
    if not hay_pendientes:
        st.success("🎉 ¡Excelente! Su área no tiene brechas ni hallazgos pendientes de mitigar.")

# ==========================================
