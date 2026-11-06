import streamlit as st
import pandas as pd
import plotly.express as px
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="AuditaCloud Global Autonomous AI", layout="wide", page_icon="🌐")

# =========================================================================
# 🔒 SISTEMA DE AUTENTICACIÓN (CLAVE MAESTRA CORPORATIVA)
# =========================================================================
CLAVE_MAESTRA = "AuditAdmin2026*"  # Configura aquí tu contraseña master

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acceso Seguro a AuditaCloud Enterprise")
    st.markdown("Por favor, introduzca las credenciales de cifrado del servidor central para continuar.")
    
    password_input = st.text_input("Clave Maestra de Infraestructura:", type="password")
    btn_login = st.button("Validar Credenciales")
    
    if btn_login:
        if password_input == CLAVE_MAESTRA:
            st.session_state.autenticado = True
            st.success("Acceso concedido. Cargando motor de auditoría...")
            st.rerun()
        else:
            st.error("Clave Maestra incorrecta o revocada por el administrador del sistema.")
    st.stop()

# =========================================================================
# 🗺️ BASE DE DATOS DE LOCALIZACIÓN EXPANDIDA (PRIORIDAD RD + LATAM)
# =========================================================================
PAISES_CONFIG = {
    "República Dominicana 🇩🇴": {
        "moneda": "DOP (RD$)", 
        "idioma": "Español", 
        "leyes": ["Ley 10-07 de la Contraloría General", "Ley 126-01 de Contabilidad Gubernamental", "Ley 449-06 de Compras y Contrataciones", "Normas de la Superintendencia de Bancos"]
    },
    "Estados Unidos 🇺🇸": {"moneda": "USD ($)", "idioma": "English / Español", "leyes": ["SOX Act Section 404", "AICPA SAS", "GAAS"]},
    "España 🇪🇸": {"moneda": "EUR (€)", "idioma": "Español", "leyes": ["Ley 22/2015 de Auditoría de Cuentas", "Código de Comercio"]},
    "México 🇲🇽": {"moneda": "MXN ($)", "idioma": "Español", "leyes": ["Código Fiscal de la Federación Art. 52", "NIF (CINIF)"]},
    "Colombia 🇨🇴": {"moneda": "COP ($)", "idioma": "Español", "leyes": ["Ley 43 de 1990", "Decreto Único Reglamentario 2420"]},
    "Argentina 🇦🇷": {"moneda": "ARS ($)", "idioma": "Español", "leyes": ["Ley 20.488", "Resolución Técnica FACPCE N° 37"]},
    "Chile 🇨🇱": {"moneda": "CLP ($)", "idioma": "Español", "leyes": ["Ley N° 18.046 de Sociedades Anónimas", "Normas de la CMF"]},
    "Perú 🇵🇪": {"moneda": "PEN (S/.)", "idioma": "Español", "leyes": ["Ley N° 28716 de Control Interno", "Normas de la SBS"]},
    "Ecuador 🇪🇨": {"moneda": "USD ($)", "idioma": "Español", "leyes": ["Ley Orgánica de la Contraloría General", "Normas de Control Interno CGE"]},
    "Panamá 🇵🇦": {"moneda": "USD / PAB (B/.)", "idioma": "Español", "leyes": ["Ley 38 de 2000", "Acuerdos de la Superintendencia de Bancos"]},
    "Otro País (Adaptación Automática IA) 🌐": {"moneda": "Divisa Local (Div)", "idioma": "Idioma Local", "leyes": ["Estándares Internacionales Transversales", "INTOSAI Framework", "IFAC IFRS"]}
}

if 'audits' not in st.session_state:
    st.session_state.audits = [
        {"id": "AUD-001", "tipo": "Financiera y de Gestión", "proceso": "Tesorería y Caja", "riesgo": "Alto", "normativa": "Leyes Locales de Cumplimiento", "moneda": "Local", "monto": 1500000},
        {"id": "AUD-002", "tipo": "Forense", "proceso": "Nómina y Viáticos", "riesgo": "Crítico", "normativa": "Marco Normativo / ACFE", "moneda": "Local", "monto": 450000}
    ]

# --- BARRA LATERAL DE CONFIGURACIÓN ---
st.sidebar.title("🌐 Configuración Global Autónoma")
pais_sel = st.sidebar.selectbox("🗺️ Seleccionar País de Operación:", list(PAISES_CONFIG.keys()))
moneda_simbolo = PAISES_CONFIG[pais_sel]["moneda"]
leyes_vigentes = PAISES_CONFIG[pais_sel]["leyes"]

st.sidebar.markdown("---")
st.sidebar.subheader("👤 Control de Acceso Localizado")
rol_usuario = st.sidebar.selectbox("Seleccione su Rol:", ["Auditor Líder (Admin)", "Auditado / Enlace Técnico"])

# Filtrado de Módulos según Rol
if rol_usuario == "Auditor Líder (Admin)":
    menu = st.sidebar.radio("Módulos:", ["📊 Dashboard e Indicadores", "🧮 Motor de Fórmulas Automatizadas", "📝 Ejecución y Leyes Locales", "📥 Descarga de Informes"])
else:
    menu = st.sidebar.radio("Módulos:", ["📊 Dashboard e Indicadores", "📝 Ejecución y Leyes Locales"])

# ==========================================
# MÓDULO 1: DASHBOARD GLOBAL
# ==========================================
if menu == "📊 Dashboard e Indicadores":
    st.title("📊 Panel de Control y Analítica de Control Interno")
    st.markdown(f"Jurisdicción activa: **{pais_sel}** | Moneda de Reporte configurada: **{moneda_simbolo}**")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Leyes Locales Activas en el Motor", len(leyes_vigentes), help=", ".join(leyes_vigentes))
    col2.metric("Auditorías en Curso", len(st.session_state.audits))
    col3.metric("Monto Total Bajo Muestreo", f"{moneda_simbolo} {sum([a['monto'] for a in st.session_state.audits]):,}")

    st.markdown("---")
    st.subheader("Exposición Financiera por Disciplina de Control")
    df_audits = pd.DataFrame(st.session_state.audits)
    fig = px.bar(df_audits, x="tipo", y="monto", color="riesgo", title=f"Distribución de Carga en {moneda_simbolo}")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MÓDULO 2: MOTOR DE FÓRMULAS AUTOMATIZADAS
# ==========================================
elif menu == "🧮 Motor de Fórmulas Automatizadas":
    st.title("🧮 Motor de Fórmulas y Ratios Automatizados")
    st.markdown("Cálculos científicos paramétricos basados en las metodologías de los órganos rectores internacionales.")

    tipo_auditoria = st.selectbox("Seleccione la Disciplina de Auditoría a Ejecutar:", 
                                  ["Auditoría Financiera y de Gestión", "Auditoría de Riesgo", "Auditoría de Cumplimiento", "Auditoría Forense / Especial"])

    st.markdown("---")

    if tipo_auditoria == "Auditoría Financiera y de Gestión":
        st.subheader("📊 Ratios de Gestión e Índices de Liquidez (IFAC / Órganos Rectores)")
        c1, c2 = st.columns(2)
        with c1:
            activo_circ = st.number_input(f"Activo Circulante ({moneda_simbolo}):", min_value=1.0, value=500000.0)
            pasivo_circ = st.number_input(f"Pasivo Circulante ({moneda_simbolo}):", min_value=1.0, value=250000.0)
            ratio_liquidez = activo_circ / pasivo_circ
        with c2:
            st.metric("Índice de Liquidez Corriente", f"{ratio_liquidez:.2f}")
            if ratio_liquidez < 1.0:
                st.error("🚨 Alerta de Gestión: Riesgo de insolvencia operativa a corto plazo.")
            elif ratio_liquidez > 2.0:
                st.warning("⚠️ Alerta de Gestión: Capital de trabajo ocioso.")
            else:
                st.success("✅ Estabilidad Financiera: Ratio dentro del rango óptimo internacional (1.5 - 2.0).")

    elif tipo_auditoria == "Auditoría de Riesgo":
        st.subheader("🎯 Cálculo Matemático de Riesgo Inherente y Residual (ISO 31000 / COSO)")
        c1, c2 = st.columns(2)
        with c1:
            prob = st.slider("Probabilidad de Ocurrencia (1 a 5):", 1, 5, 3)
            imp = st.slider("Impacto Financiero u Operativo (1 a 5):", 1, 5, 4)
            mitigacion = st.slider("Efectividad de Controles de Mitigación (%):", 0, 100, 60)
            
            riesgo_inherente = prob * imp
            riesgo_residual = riesgo_inherente * (1 - (mitigacion / 100))
        with c2:
            st.metric("Score Riesgo Inherente", f"{riesgo_inherente} / 25")
            st.metric("Score Riesgo Residual Anualizado", f"{riesgo_residual:.2f} / 25")
            if riesgo_residual > 12:
                st.error("🚨 Riesgo Fuera de Tolerancia: Requiere intervención prioritaria inmediata.")
            else:
                st.success("✅ Riesgo Aceptable: Mitigación dentro del umbral institucional.")

    elif tipo_auditoria == "Auditoría de Cumplimiento":
        st.subheader("⚖️ Índice de Severidad de Incumplimiento Normativo (INTOSAI)")
        c1, c2 = st.columns(2)
        with c1:
            controles_totales = st.number_input("Total de Controles Clave Evaluados:", min_value=1, value=50)
            controles_fallidos = st.number_input("Total de Controles No Cumplidos / Fallidos:", min_value=0, value=8)
            tasa_incumplimiento = (controles_fallidos / controles_totales) * 100
        with c2:
            st.metric("Tasa de Incumplimiento Regulatorio", f"{tasa_incumplimiento:.2f}%")
            if tasa_incumplimiento > 10.0:
                st.error("🚨 Brecha de Cumplimiento Crítica: Supera el límite permisible.")
            else:
                st.success("✅ Cumplimiento Regulatorio Conforme.")

    elif tipo_auditoria == "Auditoría Forense / Especial":
        st.subheader("🕵️ Algoritmo de Detección de Anomalías Numéricas (Ley de Benford)")
        datos_ejemplo = st.text_area("Inserte los primeros dígitos de la muestra de transacciones (Separados por coma):", "1,2,1,4,5,1,1,2,3,9,8,1,2,7,1,1,3")
        try:
            lista_digitos = [int(x.strip()) for x in datos_ejemplo.split(",") if x.strip().isdigit()]
            total_digitos = len(lista_digitos)
            unos = lista_digitos.count(1)
            porcentaje_unos = (unos / total_digitos) * 100 if total_digitos > 0 else 0
            st.metric("Frecuencia del Dígito '1' en la Muestra", f"{porcentaje_unos:.1f}%")
            if abs(porcentaje_unos - 30.1) > 10.0:
                st.error("🚨 Alerta Forense: La distribución numérica diverge significativamente de la Ley de Benford.")
            else:
                st.success("✅ Consistencia Numérica Estándar.")
        except:
