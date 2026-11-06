import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io
import math
import uuid
from datetime import datetime, timedelta

# =========================================================================
# ⚙️ CONFIGURACIÓN DE INFRAESTRUCTURA Y CAPA DE DATOS (PERSISTENCIA SAAS)
# =========================================================================
st.set_page_config(page_title="AuditaCloud Matrix AI - Corporate Suite", layout="wide", page_icon="🌐")

# Inicialización de bases de datos relacionales en memoria persistente de sesión
if 'db_empresas' not in st.session_state:
    st.session_state.db_empresas = {
        "EMP-881": {"rnc": "101-00123-4", "nombre": "Corporación Dominicana Beta", "moneda": "DOP (RD$)"},
        "EMP-992": {"rnc": "102-45678-9", "nombre": "Consorcio Financiero Global SA", "moneda": "USD ($)"}
    }

if 'db_usuarios' not in st.session_state:
    st.session_state.db_usuarios = {
        "admin@auditacloud.com": {"clave": "AuditAdmin2026*", "rol": "Administrador Global", "nombre": "Oficial Master AI", "empresa_id": "Todas", "telefono": "8095551234", "identificacion": "001-0000000-1"},
        "auditor1@beta.com": {"clave": "Auditor2026*", "rol": "Auditor Senior", "nombre": "Lic. Juan Pérez", "empresa_id": "EMP-881", "telefono": "8095554321", "identificacion": "001-1234567-8"},
        "enlace@beta.com": {"clave": "Enlace2026*", "rol": "Enlace Corporativo / Auditado", "nombre": "Ing. María Ramos", "empresa_id": "EMP-881", "telefono": "8095557890", "identificacion": "001-9876543-2"}
    }

if 'universo_auditorias' not in st.session_state:
    st.session_state.universo_auditorias = [
        {"id": "AUD-2026-001", "empresa_id": "EMP-881", "tipo": "Auditoría Forense y de Investigación", "marco": "Gubernamental RD: Control Interno (NOBACI)", "componente": "NOBACI - Actividades de Control", "objeto": "Expedientes de Licitaciones de Obras Públicas", "riesgo": "Crítico", "monto": 45000000.0, "estado": "En Ejecución"},
        {"id": "AUD-2026-002", "empresa_id": "EMP-881", "tipo": "Auditoría Financiera y de Gestión", "marco": "Privado: Financiera y Contable (NIIF / NIA)", "componente": "Existencia de Saldos", "objeto": "Inventario de Propiedades y Equipos", "riesgo": "Alto", "monto": 12500000.0, "estado": "Planificado"},
        {"id": "AUD-2026-003", "empresa_id": "EMP-992", "tipo": "Auditoría Forense y de Investigación", "marco": "Estructural: Control Interno Orgánico (COSO)", "componente": "Evaluación de Riesgos", "objeto": "Transferencias Electrónicas Interbancarias", "riesgo": "Crítico", "monto": 89000000.0, "estado": "En Ejecución"}
    ]

if 'db_pagos' not in st.session_state:
    st.session_state.db_pagos = {"EMP-881": True, "EMP-992": False}  # Licencia pagada vs Prueba temporal

if 'registro_pruebas' not in st.session_state:
    st.session_state.registro_pruebas = {"EMP-992": datetime.now()}  # Fecha de inicio de prueba de 10 días

if 'user_logged' not in st.session_state: st.session_state.user_logged = None
if 'user_rol' not in st.session_state: st.session_state.user_rol = None
if 'user_empresa' not in st.session_state: st.session_state.user_empresa = None
if 'sub_menu_recuperacion' not in st.session_state: st.session_state.sub_menu_recuperacion = False

PAISES_MASTER = {
    "República Dominicana 🇩🇴": {"moneda": "DOP (RD$)", "leyes": ["Ley 10-07 de la Contraloría General", "NOBACI (Normas Básicas de Control Interno)", "Ley 126-01 de Contabilidad Gubernamental", "Ley 449-06 de Compras y Contrataciones", "Ley 155-17 contra el Lavado de Activos"]},
    "Estados Unidos 🇺🇸": {"moneda": "USD ($)", "leyes": ["Sarbanes-Oxley Act (SOX 404)", "PCAOB Standards", "Foreign Corrupt Practices Act (FCPA)"]}
}

MARCOS_MASTER = {
    "Privado: Financiera y Contable (NIIF / NIC / NIA)": ["Existencia de Saldos", "Reconocimiento de Ingresos", "Revelaciones Contables"],
    "Gubernamental RD: Control Interno Sector Público (NOBACI)": ["NOBACI - Ambiente de Control", "NOBACI - Actividades de Control", "NOBACI - Monitoreo"],
    "Tecnológica: Sistemas de Información (COBIT / ISACA)": ["Seguridad de la Información", "Gobernanza de Datos ERP"]
}

# =========================================================================
# 🔐 CAPA DE AUTENTICACIÓN, REGISTRO MULTIEMPRESA Y RECUPERACIÓN DE CLAVES
# =========================================================================
if st.session_state.user_logged is None:
    t1, t2, t3 = st.tabs(["🔒 Iniciar Sesión", "🏢 Registrar Empresa y Auditor", "🔑 Recuperar Acceso"])
    
    with t1:
        st.subheader("Acceso Protegido Enterprise")
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
                    st.success(f"✓ Empresa registrada con Código Único: {emp_id}. Dispone de 10 días de prueba válida en la nube.")
                else:
                    st.error("Por favor, complete todos los campos mandatorios.")
                    
    with t3:
        st.subheader("Motor de Recuperación de Credenciales Homologado")
        tipo_recup = st.selectbox("Buscar cuenta mediante variable de identidad corporativa:", ["Correo Electrónico", "WhatsApp / Teléfono", "RNC Empresa", "Cédula de Identidad"])
        valor_recup = st.text_input("Introduzca el valor de búsqueda:")
        
        if st.button("Ejecutar Rastreo de Credenciales"):
            encontrado = False
            for email, data in st.session_state.db_usuarios.items():
                if tipo_recup == "Correo Electrónico" and email == valor_recup: encontrado = (data, email)
                elif tipo_recup == "WhatsApp / Teléfono" and data["telefono"] == valor_recup: encontrado = (data, email)
                elif tipo_recup == "Cédula de Identidad" and data["identificacion"] == valor_recup: encontrado = (data, email)
                elif tipo_recup == "RNC Empresa":
                    emp_id_found = data["empresa_id"]
                    if emp_id_found in st.session_state.db_empresas and st.session_state.db_empresas[emp_id_found]["rnc"] == valor_recup:
                        encontrado = (data, email)
            if encontrado:
                st.success(f"🔒 Cuenta localizada con éxito.\n\nUsuario: **{encontrado[1]}**\n\nClave Maestra Recuperada: `{encontrado[0]['clave']}`\n\nRol: **{encontrado[0]['rol']}**")
            else:
                st.error("No se encontraron registros de auditoría asociados al valor de identidad ingresado.")
    st.stop()

# =========================================================================
# 💳 VALIDACIÓN DE LICENCIA CORPORATIVA (PAGO VS PRUEBA TEMPORAL 10 DÍAS)
# =========================================================================
empresa_activa = st.session_state.user_empresa
rol_activo = st.session_state.user_rol

if rol_activo != "Administrador Global":
    is_pagado = st.session_state.db_pagos.get(empresa_activa, False)
    fecha_reg = st.session_state.registro_pruebas.get(empresa_activa, datetime.now())
    dias_restantes = 10 - (datetime.now() - fecha_reg).days
    
    if not is_pagado:
        if dias_restantes <= 0:
            st.error(f"🚨 Período de prueba expirado (Validez: 10 Días). Bloqueo preventivo de tablas relacionales. Por favor ejecute su pago corporativo.")
            if st.button("💳 Simular Pago de Licencia Anual"):
                st.session_state.db_pagos[empresa_activa] = True
                st.success("Pago procesado con éxito vía pasarela bancaria. Módulos desbloqueados.")
                st.rerun()
            st.stop()
        else:
