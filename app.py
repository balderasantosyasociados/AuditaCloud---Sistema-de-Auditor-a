import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="AuditaCloud - Sistema de Auditoría", layout="wide", page_icon="🔒")

# --- SIMULACIÓN DE BASE DE DATOS (STATE) ---
if 'audits' not in st.session_state:
    st.session_state.audits = [
        {"id": "AUD-001", "proceso": "Contabilidad y Finanzas", "riesgo": "Alto", "estado": "En Ejecución", "progreso": 60},
        {"id": "AUD-002", "proceso": "Seguridad de la Información (TI)", "riesgo": "Crítico", "estado": "Planificado", "progreso": 10},
        {"id": "AUD-003", "proceso": "Compras y Adquisiciones", "riesgo": "Medio", "estado": "Finalizado", "progreso": 100},
    ]

if 'findings' not in st.session_state:
    st.session_state.findings = [
        {"id": "HALL-01", "auditoria": "AUD-001", "descripcion": "Falta de conciliación bancaria mensual", "criticidad": "Alta", "estado": "Abierto"},
        {"id": "HALL-02", "auditoria": "AUD-001", "descripcion": "Accesos de usuarios duplicados en ERP", "criticidad": "Media", "estado": "En Proceso"},
    ]

# --- BARRA LATERAL DE NAVEGACIÓN ---
st.sidebar.title("🔒 AuditaCloud v1.0")
st.sidebar.subheader("Menú de Módulos")
menu = st.sidebar.radio(
    "Seleccione un módulo:",
    ["📊 Dashboard General", "📅 Planificación y Riesgos", "📝 Ejecución y Papeles", "🔔 Seguimiento de Hallazgos"]
)

st.sidebar.markdown("---")
st.sidebar.info("Usuario: **Auditor Líder**\n\nRol: **Administrador**\n\nEntorno: **Seguro (AES-256)**")

# ==========================================
# MÓDULO 1: DASHBOARD GENERAL
# ==========================================
if menu == "📊 Dashboard General":
    st.title("📊 Panel de Control Directivo")
    st.markdown("Visión en tiempo real del estado de los procesos de control de la organización.")
    
    # Métricas clave
    df_audits = pd.DataFrame(st.session_state.audits)
    total_auditorias = len(df_audits)
    finalizadas = len(df_audits[df_audits['estado'] == 'Finalizado'])
    en_curso = len(df_audits[df_audits['estado'] == 'En Ejecución'])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Auditorías", total_auditorias)
    col2.metric("En Ejecución", en_curso, delta_color="normal")
    col3.metric("Finalizadas", finalizadas)
    col4.metric("Hallazgos Críticos Abiertos", len([f for f in st.session_state.findings if f['estado'] != 'Cerrado']))
    
    st.markdown("---")
    
    # Gráficos estadísticos rápidos
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Progreso por Proceso Auditado")
        fig_bar = px.bar(df_audits, x='proceso', y='progreso', color='riesgo', text='progreso',
                         labels={'progreso': '% de Avance', 'proceso': 'Proceso'},
                         color_discrete_map={"Crítico": "#ef553b", "Alto": "#ab63fa", "Medio": "#636efa"})
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with c2:
        st.subheader("Distribución de Riesgos en el Plan Anual")
        fig_pie = px.pie(df_audits, names='riesgo', color='riesgo',
                         color_discrete_map={"Crítico": "#ef553b", "Alto": "#ab63fa", "Medio": "#636efa"})
        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# MÓDULO 2: PLANIFICACIÓN Y RIESGOS
# ==========================================
elif menu == "📅 Planificación y Riesgos":
    st.title("📅 Planificación Anual y Matriz de Riesgos")
    st.markdown("Defina el alcance de sus auditorías basándose en el nivel de criticidad.")
    
    # Formulario para agregar al Plan Anual
    with st.expander("➕ Registrar Nueva Auditoría en el Plan Anual", expanded=False):
        with st.form("form_planificacion"):
            nuevo_proceso = st.text_input("Nombre del Proceso / Área Organizacional:")
            probabilidad = st.slider("Probabilidad de Ocurrencia del Riesgo (1-5)", 1, 5, 3)
            impacto = st.slider("Impacto Financiero/Operacional (1-5)", 1, 5, 3)
            
            # Cálculo de criticidad automático
            score = probabilidad * impacto
            if score >= 15: riesgo_calculado = "Crítico"
            elif score >= 8: riesgo_calculado = "Alto"
            else: riesgo_calculado = "Medio"
            
            btn_guardar = st.form_submit_button("Añadir al Plan Anual")
            
            if btn_guardar and nuevo_proceso:
                nuevo_id = f"AUD-00{len(st.session_state.audits) + 1}"
                st.session_state.audits.append({
                    "id": nuevo_id,
                    "proceso": nuevo_proceso,
                    "riesgo": riesgo_calculado,
                    "estado": "Planificado",
                    "progreso": 0
                })
                st.success(f"¡Auditoría {nuevo_id} para '{nuevo_proceso}' guardada exitosamente con Nivel: {riesgo_calculado}!")
                st.rerun()

    # Tabla del plan anual actual
    st.subheader("Universo de Auditoría Actual")
    st.dataframe(pd.DataFrame(st.session_state.audits), use_container_width=True)

# ==========================================
# MÓDULO 3: EJECUCIÓN Y PAPELES
# ==========================================
elif menu == "📝 Ejecución y Papeles":
    st.title("📝 Ejecución en Campo y Evidencias (Papeles de Trabajo)")
    st.markdown("Cargue hallazgos de forma directa y adjunte la documentación de soporte.")
    
    df_audits = pd.DataFrame(st.session_state.audits)
    lista_auditorias = df_audits['id'] + " - " + df_audits['proceso']
    
    seleccion = st.selectbox("Seleccione la Auditoría Activa en la que va a trabajar:", lista_auditorias)
    id_seleccionado = seleccion.split(" - ")[0]
    
    st.markdown("---")
    
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        st.subheader("Documentar Hallazgo Encontrado")
        with st.form("form_hallazgo"):
            desc_hallazgo = st.text_area("Descripción del hallazgo o brecha detectada:")
            criticidad_hallazgo = st.selectbox("Criticidad:", ["Baja", "Media", "Alta", "Crítica"])
            
            uploaded_file = st.file_uploader("Subir evidencia digital (PDF, PNG, XLSX)", type=["pdf", "png", "xlsx", "docx"])
            
            btn_hallazgo = st.form_submit_button("Firmar y Guardar Papel de Trabajo")
            
            if btn_hallazgo and desc_hallazgo:
                nuevo_id_f = f"HALL-0{len(st.session_state.findings) + 1}"
                st.session_state.findings.append({
                    "id": nuevo_id_f,
                    "auditoria": id_seleccionado,
                    "descripcion": desc_hallazgo,
                    "criticidad": criticidad_hallazgo,
                    "estado": "Abierto"
                })
                st.success(f"Hallazgo {nuevo_id_f} registrado con firma digital inmutable.")
                if uploaded_file is not None:
                    st.info(f"Archivo adjuntado con éxito: {uploaded_file.name}")
                st.rerun()
                
    with col_der:
        st.subheader("Papeles de Trabajo Registrados en esta Auditoría")
        df_findings = pd.DataFrame(st.session_state.findings)
        filtrados = df_findings[df_findings['auditoria'] == id_seleccionado]
        
        if not filtrados.empty:
            st.dataframe(filtrados[['id', 'descripcion', 'criticidad', 'estado']], use_container_width=True)
        else:
            st.warning("No hay hallazgos documentados todavía para este proceso.")

# ==========================================
# MÓDULO 4: SEGUIMIENTO DE HALLAZGOS
# ==========================================
elif menu == "🔔 Seguimiento de Hallazgos":
    st.title("🔔 Plan de Remediación y Seguimiento")
    st.markdown("Monitoree las acciones correctivas aplicadas por los líderes de proceso auditados.")
    
    df_findings = pd.DataFrame(st.session_state.findings)
    
    for index, row in df_findings.iterrows():
        with st.container():
            st.markdown(f"#### 🔎 [{row['id']}] - Código de Auditoría: {row['auditoria']}")
            st.write(f"**Descripción:** {row['descripcion']}")
            
            # Formato de etiquetas de criticidad
            color_crit = "🔴" if row['criticidad'] in ["Alta", "Crítica"] else "🟡"
            st.write(f"**Criticidad:** {color_crit} {row['criticidad']} | **Estado Actual:** `{row['estado']}`")
            
            # Simulación de interacción de actualización de estado
            nuevo_estado = st.selectbox(
                f"Cambiar estado de {row['id']}:", 
                ["Abierto", "En Proceso", "Cerrado"], 
                index=["Abierto", "En Proceso", "Cerrado"].index(row['estado']),
                key=f"select_{row['id']}"
            )
            
            if nuevo_estado != row['estado']:
                st.session_state.findings[index]['estado'] = nuevo_estado
                st.success(f"Estado de {row['id']} actualizado a {nuevo_estado}.")
                st.rerun()
                
            st.markdown("---")
