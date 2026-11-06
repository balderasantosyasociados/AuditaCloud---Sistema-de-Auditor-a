import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
import math
import uuid
from datetime import datetime

# =========================================================================
# ⚙️ CONFIGURACIÓN DE INFRAESTRUCTURA Y CAPA DE DATOS
# =========================================================================
st.set_page_config(page_title="AuditaCloud Matrix AI - Corporate Suite", layout="wide", page_icon="🌐")

# Inicialización de estados y bases de datos relacionales en memoria persistente
if 'db_empresas' not in st.session_state:
    st.session_state.db_empresas = {
        "EMP-881": {"rnc": "101-00123-4", "nombre": "Corporación Dominicana Beta", "moneda": "DOP (RD$)"},
        "EMP-992": {"rnc": "102-45678-9", "nombre": "Consorcio Financiero Global SA", "moneda": "USD ($)"}
    }

if 'db_usuarios' not in st.session_state:
    st.session_state.db_usuarios = {
        "admin@auditacloud.com": {"clave": "AuditAdmin2026*", "rol": "Administrador Global", "nombre": "Oficial Master AI", "empresa_id": "Todas", "telefono": "8095551234", "identificacion": "001-0000000-1"},
        "auditor1@beta.com": {"clave": "Auditor2026*", "rol": "Auditor Senior", "nombre": "Lic. Juan Pérez", "empresa_id": "EMP-881", "telefono": "8095554321", "identificacion": "001-1234567-8"}
    }

if 'universo_auditorias' not in st.session_state:
    st.session_state.universo_auditorias = [
        {"id": "AUD-001", "empresa_id": "EMP-881", "tipo": "Auditoría Forense y de Investigación", "programa": "Investigación de Fraude en Adquisiciones", "dependencia": "Ninguna (Fase Inicial)", "objeto": "Licitaciones de Obras Públicas", "probabilidad": 4, "impacto": 5, "riesgo_score": 20, "estado": "En Ejecución", "monto": 45000000.0},
        {"id": "AUD-002", "empresa_id": "EMP-881", "tipo": "Auditoría Financiera y de Gestión", "programa": "Auditoría de Efectivo y Equivalentes", "dependencia": "AUD-001", "objeto": "Conciliaciones Bancarias de Proyectos", "probabilidad": 3, "impacto": 4, "riesgo_score": 12, "estado": "Planificado"}
    ]

if 'db_pagos' not in st.session_state:
    st.session_state.db_pagos = {"EMP-881": True, "EMP-992": False}

if 'registro_pruebas' not in st.session_state:
    st.session_state.registro_pruebas = {"EMP-992": datetime.now()}

if 'user_logged' not in st.session_state: st.session_state.user_logged = None
if 'user_rol' not in st.session_state: st.session_state.user_rol = None
if 'user_empresa' not in st.session_state: st.session_state.user_empresa = None

# CATALOGO MAESTRO DE PROGRAMAS DE AUDITORÍA Y COMPONENTES
PROGRAMAS_MASTER = {
    "Auditoría Financiera Corporativa (NIA/NIIF)": [
        "Auditoría de Efectivo y Equivalentes de Efectivo",
        "Auditoría de Cuentas por Cobrar e Ingresos Ordinarios",
        "Auditoría de Inventarios y Costo de Ventas",
        "Auditoría de Propiedades, Planta y Equipo"
    ],
    "Auditoría Forense Avanzada (ACFE)": [
        "Investigación de Fraude en Adquisiciones y Compras",
        "Auditoría Forense de Nóminas y Empleados Fantasma",
        "Rastreo de Malversación de Activos y Desvíos de Fondos",
        "Detección de Lavado de Activos y Transacciones Sospechosas"
    ],
    "Auditoría Gubernamental (Gubernamental/NOBACI RD)": [
        "Auditoría de Ejecución Presupuestaria General",
        "Auditoría de Cumplimiento de Normas Básicas de Control Interno (NOBACI)",
        "Fiscalización de Fondos Públicos y Rendición de Cuentas",
        "Auditoría Especial de Procesos de Compras Públicas (Ley 449-06)"
    ],
    "Auditoría de Sistemas y TI (COBIT/ISACA)": [
        "Auditoría de Seguridad Lógica y Controles de Acceso ERP",
        "Auditoría de Continuidad de Negocio y Respaldo de Datos (BCP/DRP)",
        "Evaluación de Segregación de Funciones Automatizadas"
    ],
    "Auditoría Legal y de Cumplimiento Regulatorio": [
        "Auditoría de Cumplimiento de Obligaciones Fiscales (DGII)",
        "Revisión de Cumplimiento Normativo de Contratos Comerciales",
        "Auditoría de Prevención de Riesgos Legales y Estatutarios"
    ]
}

# =========================================================================
# 🔐 CAPA DE AUTENTICACIÓN, REGISTRO Y RECUPERACIÓN
# =========================================================================
if st.session_state.user_logged is None:
    t1, t2, t3 = st.tabs(["🔒 Iniciar Sesión", "🏢 Registrar Empresa y Auditor", "🔑 Recuperar Acceso"])
    
    with t1:
        st.subheader("Acceso Seguro Enterprise")
        user_input = st.text_input("Correo Electrónico Corporativo:")
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
                
    with t2:
        st.subheader("Crear Cuenta Multiempresa (Prueba Gratuita 10 Días)")
        with st.form("form_registro"):
            rnc_new = st.text_input("RNC / Identificación Fiscal de la Empresa:")
            nombre_emp_new = st.text_input("Nombre o Razón Social Corporativa:")
            moneda_new = st.selectbox("Moneda de Operación:", ["DOP (RD$)", "USD ($)", "EUR (€)"])
            st.markdown("---")
            admin_name = st.text_input("Nombre Completo del Auditor Líder:")
            admin_email = st.text_input("Correo Electrónico de Usuario:")
            admin_pass = st.text_input("Definir Contraseña de Acceso:", type="password")
            admin_tel = st.text_input("Número de WhatsApp / Teléfono:")
            admin_ced = st.text_input("Cédula / Pasaporte de Identidad:")
            
            if st.form_submit_button("Crear Infraestructura Organizacional"):
                if rnc_new and nombre_emp_new and admin_email and admin_pass:
                    emp_id = f"EMP-{uuid.uuid4().hex[:3].upper()}"
                    st.session_state.db_empresas[emp_id] = {"rnc": rnc_new, "nombre": nombre_emp_new, "moneda": moneda_new}
                    st.session_state.db_usuarios[admin_email] = {"clave": admin_pass, "rol": "Auditor Senior", "nombre": admin_name, "empresa_id": emp_id, "telefono": admin_tel, "identificacion": admin_ced}
                    st.session_state.db_pagos[emp_id] = False
                    st.session_state.registro_pruebas[emp_id] = datetime.now()
                    st.success(f"✓ Empresa registrada con Código Único: {emp_id}. Dispone de 10 días de prueba válida.")
                    st.rerun()
                else:
                    st.error("Por favor, complete todos los campos obligatorios.")
                    
    with t3:
        st.subheader("Motor de Recuperación de Credenciales")
        tipo_recup = st.selectbox("Buscar por:", ["Correo Electrónico", "WhatsApp / Teléfono", "Cédula de Identidad"])
        valor_recup = st.text_input("Introduzca el valor de búsqueda:")
        if st.button("Ejecutar Rastreo"):
            encontrado = False
            for email, data in st.session_state.db_usuarios.items():
                if tipo_recup == "Correo Electrónico" and email == valor_recup: encontrado = data
                elif tipo_recup == "WhatsApp / Teléfono" and data["telefono"] == valor_recup: encontrado = data
                elif tipo_recup == "Cédula de Identidad" and data["identificacion"] == valor_recup: encontrado = data
            if encontrado:
                st.success(f"🔒 Cuenta localizada.\n\nContraseña: `{encontrado['clave']}`\n\nRol: **{encontrado['rol']}**")
            else:
                st.error("No se encontraron registros asociados.")
    st.stop()

# =========================================================================
# 💳 VALIDACIÓN DE LICENCIA CORPORATIVA (10 DÍAS DE PRUEBA)
# =========================================================================
empresa_activa = st.session_state.user_empresa
rol_activo = st.session_state.user_rol

if rol_activo != "Administrador Global":
    is_pagado = st.session_state.db_pagos.get(empresa_activa, False)
    fecha_reg = st.session_state.registro_pruebas.get(empresa_activa, datetime.now())
    dias_restantes = 10 - (datetime.now() - fecha_reg).days
    
    if not is_pagado:
        if dias_restantes <= 0:
            st.error("🚨 Período de prueba expirado (Validez: 10 Días). Bloqueo preventivo de seguridad. Active su licencia.")
            if st.button("💳 Simular Pago de Licencia"):
                st.session_state.db_pagos[empresa_activa] = True
                st.success("Pago procesado. Módulos desbloqueados."); st.rerun()
            st.stop()
        else:
            st.warning(f"⏳ Modo de Demostración Activo. Datos guardados en carpeta temporal válida por {dias_restantes} días.")

# =========================================================================
# 🗺️ CONFIGURACIÓN DE CONSOLA MULTIEMPRESA Y FILTROS
# =========================================================================
st.sidebar.title("🌐 AuditaCloud Core AI")
st.sidebar.markdown(f"Usuario: **{st.session_state.user_logged}**\n\nRol: **{rol_activo}**")

if st.sidebar.button("🚪 Cerrar Sesión Segura"):
    st.session_state.user_logged = None; st.rerun()

st.sidebar.markdown("---")

if rol_activo == "Administrador Global":
    empresa_seleccionada = st.sidebar.selectbox("Inspeccionar Empresa:", list(st.session_state.db_empresas.keys()), format_func=lambda x: st.session_state.db_empresas[x]["nombre"])
