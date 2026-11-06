import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
import math
import uuid
import json
import hashlib
from datetime import datetime
from sqlalchemy import create_engine, text

# =========================================================================
# ⚙️ CONFIGURACIÓN DE INFRAESTRUCTURA DE INTERFAZ (BIG 4 COMPLIANT)
# =========================================================================
st.set_page_config(page_title="AuditaCloud Matrix AI - Corporate Suite", layout="wide", page_icon="🌐")

# Instanciación y persistencia del motor in-memory SQL (AUDIT-INTEL)
if 'engine_forense' not in st.session_state:
    st.session_state.engine_forense = create_engine("sqlite:///:memory:")
    with st.session_state.engine_forense.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS transacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor TEXT,
                monto REAL,
                fecha TEXT,
                rnc_cedula TEXT
            );
        """))
        # Inyección de transacciones de prueba (Duplicados y Benford)
        valores = [
            ('Proveedor Alfa', 15000.00, '2026-11-01', '101-00000-1'),
            ('Proveedor Alfa', 15000.00, '2026-11-01', '101-00000-1'),  
            ('Proveedor Beta', 4500.25, '2026-11-02', '102-55555-2'),
            ('Proveedor Beta', 4500.25, '2026-11-02', '102-55555-2'),  
            ('Proveedor Gamma', 1950.00, '2026-11-03', '103-99999-3'),
            ('Proveedor Delta', 8120.00, '2026-11-04', '104-11111-4'),
            ('Proveedor Delta', 8120.00, '2026-11-04', '104-11111-4'),  
            ('Proveedor Omega', 3200.00, '2026-11-05', '105-88888-5'),
        ]
        for i in range(1, 100):
            monto_anomalo = float(f"5{i}0.00") if i % 4 == 0 else float(f"{i % 9 + 1}{i}5.50")
            valores.append(('Proveedor General', monto_anomalo, '2026-11-05', '106-00000-6'))
        
        for val in valores:
            conn.execute(text("""
                INSERT INTO transacciones (proveedor, monto, fecha, rnc_cedula) 
                VALUES (:p, :m, :f, :r);
            """), {"p": val[0], "m": val[1], "f": val[2], "r": val[3]})
        conn.commit()

# Inicialización de bases de datos relacionales en memoria persistente de sesión
if 'db_empresas' not in st.session_state:
    st.session_state.db_empresas = {
        "EMP-881": {"rnc": "101-00123-4", "nombre": "Corporación Dominicana Beta", "moneda": "DOP (RD$)"},
        "EMP-992": {"rnc": "102-45678-9", "nombre": "Consorcio Financiero Global SA", "moneda": "USD ($)"}
    }

if 'db_usuarios' not in st.session_state:
    st.session_state.db_usuarios = {
        "admin@auditacloud.com": {"clave": "AuditAdmin2026*", "rol": "Administrador Global", "nombre": "Oficial Master AI", "empresa_id": "Todas", "telefono": "8095551234", "identificacion": "001-0000000-1"},
        "admin": {"clave": "AuditAdmin2026*", "rol": "Administrador Global", "nombre": "Oficial Master AI", "empresa_id": "Todas", "telefono": "8095551234", "identificacion": "001-0000000-1"}
    }

if 'universo_auditorias' not in st.session_state:
    st.session_state.universo_auditorias = [
        {"id": "AUD-001", "empresa_id": "EMP-881", "tipo": "Auditoría Forense y de Investigación", "programa": "Investigación de Fraude en Adquisiciones", "dependencia": "Ninguna (Fase Inicial)", "objeto": "Licitaciones de Obras Públicas", "probabilidad": 4, "impacto": 5, "riesgo_score": 20, "estado": "En Ejecución", "monto": 45000000.0}
    ]

if 'cadena_custodia_logs' not in st.session_state:
    st.session_state.cadena_custodia_logs = []

if 'user_logged' not in st.session_state: st.session_state.user_logged = None
if 'user_rol' not in st.session_state: st.session_state.user_rol = None
if 'user_empresa' not in st.session_state: st.session_state.user_empresa = None

PROGRAMAS_MASTER = {
    "Auditoría Financiera Corporativa (NIA/NIIF)": ["Auditoría de Efectivo y Equivalentes de Efectivo", "Auditoría de Cuentas por Cobrar e Ingresos Ordinarios"],
    "Auditoría Forense Avanzada (ACFE)": ["Investigación de Fraude en Adquisiciones y Compras", "Rastreo de Malversación de Activos"],
    "Auditoría Gubernamental (Gubernamental/NOBACI RD)": ["Auditoría de Cumplimiento de Normas Básicas de Control Interno (NOBACI)"],
    "Auditoría de Sistemas y TI (COBIT/ISACA)": ["Auditoría de Seguridad Lógica y Controles de Acceso ERP"]
}

# =========================================================================
# 🔐 CAPA DE AUTENTICACIÓN
# =========================================================================
if st.session_state.user_logged is None:
    t1, t2, t3 = st.tabs(["🔒 Iniciar Sesión", "🏢 Registrar Empresa y Auditor", "🔑 Recuperar Acceso"])
    with t1:
        st.subheader("Acceso Seguro Enterprise")
        user_input = st.text_input("Usuario o Correo Corporativo:")
        pass_input = st.text_input("Contraseña de Acceso:", type="password")
        if st.button("Autenticar en Servidor"):
            if user_input in st.session_state.db_usuarios and st.session_state.db_usuarios[user_input]["clave"] == pass_input:
                usr_data = st.session_state.db_usuarios[user_input]
                st.session_state.user_logged = user_input
                st.session_state.user_rol = usr_data["rol"]
                st.session_state.user_empresa = usr_data["empresa_id"]
                st.success(f"Token Validado. Bienvenido {usr_data['nombre']}")
                st.rerun()
            else:
                st.error("Credenciales de seguridad incorrectas.")
    st.stop()

# =========================================================================
# 🗺️ CONSOLA MULTIEMPRESA INTERACTIVA
# =========================================================================
st.sidebar.title("🌐 AuditaCloud Core AI")
st.sidebar.markdown(f"Usuario: **{st.session_state.user_logged}**\n\nRol: **{st.session_state.user_rol}**")

if st.sidebar.button("🚪 Cerrar Sesión Segura"):
    st.session_state.user_logged = None
    st.rerun()

st.sidebar.markdown("---")

if st.session_state.user_rol == "Administrador Global":
    empresa_seleccionada = st.sidebar.selectbox("Inspeccionar Empresa:", list(st.session_state.db_empresas.keys()), format_func=lambda x: st.session_state.db_empresas[x]["nombre"])
    moneda_simbolo = st.session_state.db_empresas[empresa_seleccionada]["moneda"]
else:
    empresa_seleccionada = st.session_state.user_empresa
    moneda_simbolo = st.session_state.db_empresas[empresa_seleccionada]["moneda"]

menu = st.sidebar.radio("Módulos del Sistema:", [
    "📊 Tablero e Indicadores de Riesgo",
    "🎯 Catálogo de Programas y Dependencias",
    "🧮 Motor Forense Avanzado (AUDIT-INTEL)",
    "📜 Cadena de Custodia Digital Pericial"
])

# ==========================================
# MÓDULO 1: TABLERO ANALÍTICO Y MATRIZ DE RIESGO
# ==========================================
if menu == "📊 Tablero e Indicadores de Riesgo":
    st.title("📊 Análisis de Riesgo Estructural (ISO 31000 / COSO)")
    st.markdown(f"Organización: **{st.session_state.db_empresas[empresa_seleccionada]['nombre']}**")
    
    df_audits = pd.DataFrame(st.session_state.universo_auditorias)
    df_filtrado = df_audits[df_audits['empresa_id'] == empresa_seleccionada] if not df_audits.empty else pd.DataFrame()
    
    if not df_filtrado.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Programas Planificados", len(df_filtrado))
        col2.metric("Monto Total Expuesto", f"{moneda_simbolo} {df_filtrado['monto'].sum():,.2f}")
        col3.metric("Riesgo Promedio de Cartera", f"{df_filtrado['riesgo_score'].mean():.1f} / 25")
        
        st.markdown("---")
        st.subheader("🗺️ Mapa de Calor y Dispersión del Riesgo")
        fig = px.scatter(df_filtrado, x="probabilidad", y="impacto", size="monto", color="riesgo_score", text="id", size_max=40, color_continuous_scale=px.colors.sequential.YlOrRd)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay programas o análisis registrados todavía para esta organización.")

# ==========================================
# MÓDULO 2: CATÁLOGOS Y PROGRAMAS
# ==========================================
elif menu == "🎯 Catálogo de Programas y Dependencias":
    st.title("🎯 Catálogo de Programas Maestros y Gestión de Dependencias")
    df_audits = pd.DataFrame(st.session_state.universo_auditorias)
    df_filtrado = df_audits[df_audits['empresa_id'] == empresa_seleccionada] if not df_audits.empty else pd.DataFrame()
    
    with st.form("form_add_programa"):
        tipo_aud = st.selectbox("Tipo de Marco Metodológico:", list(PROGRAMAS_MASTER.keys()))
        prog_det = st.selectbox("Seleccione el Programa Específico:", PROGRAMAS_MASTER[tipo_aud])
        objeto_det = st.text_input("Cuenta Analítica / Proceso Exacto a Evaluar:")
        monto_det = st.number_input(f"Monto Total Expuesto ({moneda_simbolo}):", min_value=0.0, value=50000.0)
        prob = st.slider("Probabilidad (1-5):", 1, 5, 3)
        imp = st.slider("Impacto (1-5):", 1, 5, 3)
        
        if st.form_submit_button("Sellar e Indexar Programa"):
            if objeto_det:
                st.session_state.universo_auditorias.append({
                    "id": f"AUD-{len(st.session_state.universo_auditorias)+1:03d}", "empresa_id": empresa_seleccionada, "tipo": tipo_aud, "programa": prog_det,
                    "dependencia": "Ninguna", "objeto": objeto_det, "probabilidad": prob, "impacto": imp, "riesgo_score": prob*imp, "estado": "Planificado", "monto": monto_det
                })
                st.success("✓ Programa guardado dentro del mapa relacional."); st.rerun()
                
    if not df_filtrado.empty:
        st.dataframe(df_filtrado[['id', 'tipo', 'programa', 'objeto', 'riesgo_score', 'estado']], use_container_width=True)

# ==========================================
# MÓDULO 3: MOTOR FORENSE AVANZADO
