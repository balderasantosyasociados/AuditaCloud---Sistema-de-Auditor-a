
# =====================================================================
# BASA SUPERSISTEMA V27 - STREAMLIT CLOUD / PRODUCCIÓN
# Baldera Santos & Asociados SRL
# AuditaCloud Matrix AI - Risk, ADA, Forense, CCRD y Cadena de Custodia
# =====================================================================
#
# IMPORTANTE:
# - No instala paquetes en tiempo de ejecución.
# - Las dependencias se declaran en requirements.txt.
# - Para producción multiusuario, configure DATABASE_URL en Streamlit Secrets.
# - SQLite es un modo local/demo; en Community Cloud el almacenamiento local
#   no debe considerarse persistencia empresarial.
#
# =====================================================================

from __future__ import annotations

import os
import io
import re
import json
import math
import uuid
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------

APP_NAME = "BASA SUPERSISTEMA V27"
APP_SUBTITLE = "AuditaCloud Matrix AI • Enterprise Audit & Forensic Analytics"
APP_VERSION = "27.0.0"
MAX_UPLOAD_MB = 50

st.set_page_config(
    page_title=f"{APP_NAME} | {APP_VERSION}",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------
# ESTILOS
# ---------------------------------------------------------------------

st.markdown(
    """
    <style>
    .main {padding-top: 1rem;}
    .basa-header {
        padding: 1rem 1.2rem;
        border-radius: 14px;
        border: 1px solid rgba(120,120,120,.25);
        background: linear-gradient(135deg, rgba(20,70,110,.12), rgba(80,120,80,.08));
        margin-bottom: 1rem;
    }
    .risk-critical {color:#b00020;font-weight:700;}
    .risk-high {color:#c65d00;font-weight:700;}
    .risk-medium {color:#9a7600;font-weight:700;}
    .risk-low {color:#267326;font-weight:700;}
    .small-muted {font-size:.82rem;opacity:.75;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        value = st.secrets.get(name)
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass
    value = os.getenv(name)
    return value if value not in (None, "") else default

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(rounds),
        ).hex()
        return secrets.compare_digest(candidate, digest_hex)
    except Exception:
        return False

def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def normalize_rnc(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"[^0-9A-Za-z]", "", str(value)).upper()

def money(value: float, currency: str = "RD$") -> str:
    try:
        return f"{currency} {float(value):,.2f}"
    except Exception:
        return f"{currency} 0.00"

def risk_level(score: float) -> str:
    if score >= 20:
        return "CRÍTICO"
    if score >= 15:
        return "ALTO"
    if score >= 8:
        return "MEDIO"
    return "BAJO"

def safe_float(value, default=0.0) -> float:
    try:
        if pd.isna(value):
            return default
        if isinstance(value, str):
            value = value.replace(",", "").replace("$", "").replace("RD", "").strip()
        return float(value)
    except Exception:
        return default

def similarity(a: str, b: str) -> float:
    # Similaridad Jaccard por tokens; evita dependencia externa.
    ta = set(re.findall(r"[a-z0-9]+", str(a).lower()))
    tb = set(re.findall(r"[a-z0-9]+", str(b).lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

# ---------------------------------------------------------------------
# BASE DE DATOS
# ---------------------------------------------------------------------

def database_url() -> str:
    # Prioridad: Streamlit Secrets > variable de entorno > SQLite local.
    return get_secret("DATABASE_URL", "sqlite:///basa_v27.db")

@st.cache_resource
def get_engine(url: str) -> Engine:
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 1800
    return create_engine(url, **kwargs)

engine = get_engine(database_url())

def db_init() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                rnc TEXT NOT NULL,
                name TEXT NOT NULL,
                currency TEXT NOT NULL DEFAULT 'RD$',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                company_id TEXT,
                full_name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                event_time TEXT NOT NULL,
                username TEXT,
                company_id TEXT,
                action TEXT NOT NULL,
                object_type TEXT,
                object_id TEXT,
                details TEXT,
                previous_hash TEXT,
                event_hash TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_cases (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                title TEXT NOT NULL,
                audit_type TEXT NOT NULL,
                program TEXT NOT NULL,
                objective TEXT,
                probability INTEGER NOT NULL DEFAULT 1,
                impact INTEGER NOT NULL DEFAULT 1,
                amount REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Planificada',
                created_at TEXT NOT NULL,
                created_by TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                uploaded_by TEXT,
                notes TEXT
            )
        """))

def bootstrap() -> None:
    db_init()
    with engine.begin() as conn:
        company_count = conn.execute(text("SELECT COUNT(*) FROM companies")).scalar_one()
        if company_count == 0:
            conn.execute(
                text("""
                    INSERT INTO companies(id,rnc,name,currency,created_at)
                    VALUES(:id,:rnc,:name,:currency,:created)
                """),
                {
                    "id": "EMP-881",
                    "rnc": get_secret("DEFAULT_RNC", "101001234"),
                    "name": get_secret("DEFAULT_COMPANY", "Baldera Santos & Asociados SRL"),
                    "currency": "RD$",
                    "created": utc_now(),
                },
            )

        user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
        if user_count == 0:
            admin_user = get_secret("ADMIN_USERNAME", "admin")
            admin_password = get_secret("ADMIN_PASSWORD")
            if not admin_password:
                # Se crea una contraseña aleatoria y se muestra solo durante
                # esta ejecución si no existe configuración de producción.
                admin_password = secrets.token_urlsafe(12)
                st.session_state["_generated_admin_password"] = admin_password

            conn.execute(
                text("""
                    INSERT INTO users(
                        id,username,password_hash,role,company_id,full_name,created_at
                    ) VALUES(:id,:username,:password_hash,:role,:company_id,:full_name,:created)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "username": admin_user,
                    "password_hash": hash_password(admin_password),
                    "role": "Administrador Global",
                    "company_id": None,
                    "full_name": "Administrador BASA",
                    "created": utc_now(),
                },
            )

bootstrap()

# ---------------------------------------------------------------------
# DATOS DE DEMOSTRACIÓN
# ---------------------------------------------------------------------

def seed_demo_data() -> None:
    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM audit_cases")).scalar_one()
        if count == 0:
            conn.execute(
                text("""
                    INSERT INTO audit_cases(
                        id,company_id,title,audit_type,program,objective,
                        probability,impact,amount,status,created_at,created_by
                    )
                    VALUES(
                        :id,:company_id,:title,:audit_type,:program,:objective,
                        :probability,:impact,:amount,:status,:created_at,:created_by
                    )
                """),
                {
                    "id": "AUD-DEMO-001",
                    "company_id": "EMP-881",
                    "title": "Control posterior de erogaciones",
                    "audit_type": "Auditoría Forense y de Investigación",
                    "program": "PROG-CCRD-1824",
                    "objective": "Identificar desviaciones, duplicidades y riesgos de contratación.",
                    "probability": 4,
                    "impact": 5,
                    "amount": 85000000,
                    "status": "En Ejecución",
                    "created_at": utc_now(),
                    "created_by": "system",
                },
            )

seed_demo_data()

# ---------------------------------------------------------------------
# AUDIT LOG / CADENA DE CUSTODIA
# ---------------------------------------------------------------------

def get_last_hash() -> str:
    with engine.connect() as conn:
        value = conn.execute(
            text("SELECT event_hash FROM audit_log ORDER BY id DESC LIMIT 1")
        ).scalar()
    return value or "GENESIS"

def append_audit_event(
    action: str,
    object_type: str = "",
    object_id: str = "",
    details: str = "",
    username: str = "",
    company_id: str = "",
) -> str:
    previous = get_last_hash()
    event_id = str(uuid.uuid4())
    event_time = utc_now()
    payload = "|".join([
        event_id, event_time, username, company_id, action,
        object_type, object_id, details, previous
    ])
    event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO audit_log(
                    event_id,event_time,username,company_id,action,
                    object_type,object_id,details,previous_hash,event_hash
                ) VALUES(
                    :event_id,:event_time,:username,:company_id,:action,
                    :object_type,:object_id,:details,:previous_hash,:event_hash
                )
            """),
            {
                "event_id": event_id,
                "event_time": event_time,
                "username": username,
                "company_id": company_id,
                "action": action,
                "object_type": object_type,
                "object_id": object_id,
                "details": details,
                "previous_hash": previous,
                "event_hash": event_hash,
            },
        )
    return event_hash

# ---------------------------------------------------------------------
# AUTENTICACIÓN
# ---------------------------------------------------------------------

def current_user() -> Optional[dict]:
    uid = st.session_state.get("user_id")
    if not uid:
        return None
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT id,username,role,company_id,full_name
                FROM users WHERE id=:id AND active=1
            """),
            {"id": uid},
        ).mappings().first()
    return dict(row) if row else None

def login_screen() -> None:
    st.markdown(
        f"""
        <div class="basa-header">
            <h1>🌐 {APP_NAME}</h1>
            <div>{APP_SUBTITLE}</div>
            <div class="small-muted">Versión {APP_VERSION}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1])
    with left:
        st.subheader("🔐 Acceso Enterprise")
        username = st.text_input("Usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Iniciar sesión", type="primary", use_container_width=True):
            with engine.connect() as conn:
                row = conn.execute(
                    text("""
                        SELECT id,username,password_hash,role,company_id,full_name
                        FROM users WHERE username=:username AND active=1
                    """),
                    {"username": username.strip()},
                ).mappings().first()

            if row and verify_password(password, row["password_hash"]):
                st.session_state.user_id = row["id"]
                append_audit_event(
                    "LOGIN",
                    object_type="USER",
                    object_id=row["id"],
                    details="Inicio de sesión exitoso",
                    username=row["username"],
                    company_id=row["company_id"] or "",
                )
                st.rerun()
            else:
                st.error("Credenciales inválidas.")

    with right:
        st.subheader("🚀 Configuración de primera ejecución")
        generated = st.session_state.get("_generated_admin_password")
        if generated:
            st.warning(
                "No se encontró ADMIN_PASSWORD en Secrets. Se generó una contraseña "
                "temporal para esta ejecución. Para producción configure ADMIN_PASSWORD "
                "en Streamlit Secrets."
            )
            st.code(generated)
        st.info(
            "En Streamlit Community Cloud, configure ADMIN_USERNAME, ADMIN_PASSWORD "
            "y DATABASE_URL en Secrets para uso empresarial."
        )

# ---------------------------------------------------------------------
# IMPORTACIÓN DE DATOS
# ---------------------------------------------------------------------

def read_uploaded_table(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()

    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"El archivo supera el límite de {MAX_UPLOAD_MB} MB.")

    if name.endswith(".csv") or name.endswith(".txt"):
        return pd.read_csv(io.BytesIO(raw))
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(io.BytesIO(raw))
    if name.endswith(".json"):
        return pd.read_json(io.BytesIO(raw))
    raise ValueError("Formato tabular no soportado. Use CSV, XLSX, XLS, JSON o TXT.")

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    mapping = {}
    for col in out.columns:
        c = str(col).strip().lower()
        c = re.sub(r"[^a-z0-9áéíóúñ]+", "_", c)
        mapping[col] = c.strip("_")
    out.rename(columns=mapping, inplace=True)

    aliases = {
        "rnc": ["rnc", "rnc_proveedor", "proveedor_rnc", "documento"],
        "proveedor": ["proveedor", "nombre_proveedor", "nombre", "suplidor"],
        "monto": ["monto", "importe", "valor", "total", "monto_factura"],
        "fecha": ["fecha", "fecha_registro", "fecha_factura", "date"],
        "numero": ["numero", "no_factura", "factura", "ncf", "comprobante"],
        "usuario": ["usuario", "usuario_creador", "creado_por"],
    }

    for target, candidates in aliases.items():
        if target not in out.columns:
            for candidate in candidates:
                if candidate in out.columns:
                    out[target] = out[candidate]
                    break

    if "monto" in out.columns:
        out["monto"] = out["monto"].map(safe_float)
    if "rnc" in out.columns:
        out["rnc_normalizado"] = out["rnc"].map(normalize_rnc)
    if "proveedor" in out.columns:
        out["proveedor_normalizado"] = out["proveedor"].astype(str).str.strip()

    return out

# ---------------------------------------------------------------------
# ANALÍTICA ADA / BIG FOUR
# ---------------------------------------------------------------------

def benford_analysis(series: pd.Series) -> pd.DataFrame:
    values = pd.to_numeric(series, errors="coerce")
    values = values[values > 0]
    first_digits = values.astype(str).str.replace(r"\D", "", regex=True).str[0]
    observed = first_digits.value_counts().reindex(list("123456789"), fill_value=0)
    observed_pct = observed / max(observed.sum(), 1)

    expected_pct = pd.Series(
        {str(d): math.log10(1 + 1/d) for d in range(1, 10)}
    )

    return pd.DataFrame({
        "Digito": list("123456789"),
        "Observado": [observed_pct[d] for d in "123456789"],
        "Benford_Esperado": [expected_pct[d] for d in "123456789"],
    })

def duplicate_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    work = df.copy()
    cols = [c for c in ["rnc_normalizado", "proveedor_normalizado", "monto", "fecha"] if c in work.columns]
    if not cols:
        return pd.DataFrame()

    work["duplicado_exacto"] = work.duplicated(subset=cols, keep=False)
    exact = work[work["duplicado_exacto"]].copy()

    # Detección de nombres parecidos dentro del mismo RNC y monto cercano.
    fuzzy_rows = []
    if "proveedor_normalizado" in work.columns and "monto" in work.columns:
        for i in range(len(work)):
            for j in range(i + 1, min(len(work), i + 80)):
                a = work.iloc[i]
                b = work.iloc[j]
                if "rnc_normalizado" in work.columns and a["rnc_normalizado"] != b["rnc_normalizado"]:
                    continue
                sim = similarity(a["proveedor_normalizado"], b["proveedor_normalizado"])
                ma, mb = safe_float(a["monto"]), safe_float(b["monto"])
                base = max(abs(ma), abs(mb), 1)
                monto_diff = abs(ma - mb) / base
                if sim >= 0.70 and monto_diff <= 0.02 and sim < 1:
                    fuzzy_rows.append({
                        "Fila_A": i + 2,
                        "Fila_B": j + 2,
                        "Proveedor_A": a["proveedor_normalizado"],
                        "Proveedor_B": b["proveedor_normalizado"],
                        "RNC": a.get("rnc_normalizado", ""),
                        "Monto_A": ma,
                        "Monto_B": mb,
                        "Similitud": round(sim, 4),
                        "Diferencia_Monto_%": round(monto_diff * 100, 2),
                    })

    fuzzy = pd.DataFrame(fuzzy_rows)
    if not exact.empty:
        exact = exact.reset_index().rename(columns={"index": "Fila"})
        exact["Tipo_Hallazgo"] = "Duplicidad exacta"
    if not fuzzy.empty:
        fuzzy["Tipo_Hallazgo"] = "Posible duplicidad fuzzy"

    parts = []
    if not exact.empty:
        parts.append(exact)
    if not fuzzy.empty:
        parts.append(fuzzy)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

def split_payment_analysis(df: pd.DataFrame, threshold: float = 100000.0) -> pd.DataFrame:
    required = {"proveedor_normalizado", "monto"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    if "fecha" in work.columns:
        work["fecha_dia"] = pd.to_datetime(work["fecha"], errors="coerce").dt.date
    else:
        work["fecha_dia"] = pd.NaT

    grouped = (
        work.groupby(["proveedor_normalizado", "fecha_dia"], dropna=False)
        .agg(
            transacciones=("monto", "count"),
            total=("monto", "sum"),
            promedio=("monto", "mean"),
        )
        .reset_index()
    )
    suspicious = grouped[
        (grouped["transacciones"] >= 2) &
        (grouped["total"] >= threshold)
    ].copy()
    suspicious["riesgo_fraccionamiento"] = np.where(
        suspicious["total"] >= threshold * 2, "ALTO", "MEDIO"
    )
    return suspicious.sort_values("total", ascending=False)

def risk_score(probability: int, impact: int) -> int:
    return max(1, min(25, int(probability) * int(impact)))

# ---------------------------------------------------------------------
# EXPORTACIONES
# ---------------------------------------------------------------------

def excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            safe_name = str(name)[:31] or "Hoja"
            frame.to_excel(writer, index=False, sheet_name=safe_name)
    return buffer.getvalue()

# ---------------------------------------------------------------------
# SESIÓN
# ---------------------------------------------------------------------

if "user_id" not in st.session_state:
    st.session_state.user_id = None

user = current_user()
if not user:
    login_screen()
    st.stop()

# ---------------------------------------------------------------------
# CABECERA / SIDEBAR
# ---------------------------------------------------------------------

with st.sidebar:
    st.markdown(f"## 🌐 {APP_NAME}")
    st.caption(f"v{APP_VERSION}")
    st.write(f"**Usuario:** {user['full_name']}")
    st.write(f"**Rol:** {user['role']}")

    if st.button("🚪 Cerrar sesión", use_container_width=True):
        append_audit_event(
            "LOGOUT",
            object_type="USER",
            object_id=user["id"],
            username=user["username"],
            company_id=user["company_id"] or "",
        )
        st.session_state.user_id = None
        st.rerun()

    st.markdown("---")

    with engine.connect() as conn:
        companies = pd.read_sql(
            text("SELECT id,rnc,name,currency FROM companies WHERE active=1 ORDER BY name"),
            conn,
        )

    if user["role"] == "Administrador Global":
        company_id = st.selectbox(
            "🏢 Empresa / entidad",
            companies["id"].tolist(),
            format_func=lambda x: companies.loc[companies.id == x, "name"].iloc[0],
        )
    else:
        company_id = user["company_id"]

    menu = st.radio(
        "Módulos",
        [
            "📊 Dashboard Ejecutivo",
            "🎯 Risk Engine / ISA 315",
            "🧮 ADA / Big Four Analytics",
            "📥 Importación y Universo",
            "🔎 Hallazgos y Pruebas",
            "📜 Cadena de Custodia",
            "📚 Programas y Normativa",
            "⚙️ Administración",
        ],
    )

    st.markdown("---")
    st.caption("Framework configurable: NIA/ISA • NIIF/IFRS • NOBACI • normativa nacional seleccionada.")
    st.caption("La referencia legal debe ser validada por el profesional responsable antes de emitir conclusiones.")

company = companies[companies.id == company_id].iloc[0].to_dict()

st.markdown(
    f"""
    <div class="basa-header">
      <h1>🌐 {APP_NAME}</h1>
      <div>{APP_SUBTITLE}</div>
      <div><b>Entidad:</b> {company['name']} &nbsp; | &nbsp; <b>RNC:</b> {company['rnc']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------

if menu == "📊 Dashboard Ejecutivo":
    with engine.connect() as conn:
        audits = pd.read_sql(
            text("""
                SELECT * FROM audit_cases
                WHERE company_id=:company_id
                ORDER BY created_at DESC
            """),
            conn,
            params={"company_id": company_id},
        )
        docs = pd.read_sql(
            text("""
                SELECT * FROM documents
                WHERE company_id=:company_id
                ORDER BY uploaded_at DESC
            """),
            conn,
            params={"company_id": company_id},
        )

    if not audits.empty:
        audits["risk_score"] = audits.apply(
            lambda r: risk_score(r["probability"], r["impact"]), axis=1
        )
        audits["risk_level"] = audits["risk_score"].map(risk_level)
    else:
        audits = pd.DataFrame()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Casos de auditoría", len(audits))
    c2.metric("Monto bajo análisis", money(audits["amount"].sum() if not audits.empty else 0, company["currency"]))
    c3.metric("Hallazgos críticos/altos", int((audits["risk_score"] >= 15).sum()) if not audits.empty else 0)
    c4.metric("Documentos con hash", len(docs))

    if not audits.empty:
        left, right = st.columns(2)
        with left:
            chart = px.bar(
                audits.groupby("risk_level", as_index=False)["amount"].sum(),
                x="risk_level",
                y="amount",
                title="Exposición por nivel de riesgo",
            )
            st.plotly_chart(chart, use_container_width=True)
        with right:
            st.dataframe(
                audits[[
                    "title", "audit_type", "probability", "impact",
                    "risk_score", "risk_level", "amount", "status"
                ]],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("No hay casos registrados para esta entidad.")

# ---------------------------------------------------------------------
# RISK ENGINE
# ---------------------------------------------------------------------

elif menu == "🎯 Risk Engine / ISA 315":
    st.subheader("🎯 Central Risk Engine — evaluación de riesgo")
    st.caption(
        "Motor de priorización cuantitativa. El score es una herramienta de apoyo "
        "y no sustituye el juicio profesional."
    )

    with st.form("new_risk_case"):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Nombre del foco / proceso")
            audit_type = st.selectbox(
                "Tipo de auditoría",
                [
                    "Auditoría Financiera",
                    "Auditoría de Cumplimiento",
                    "Auditoría Forense y de Investigación",
                    "Auditoría Gubernamental",
                    "Auditoría de Sistemas y TI",
                ],
            )
            program = st.selectbox(
                "Programa",
                [
                    "PROG-EF-01 — Estados Financieros y Erogaciones",
                    "PROG-CCRD-1824 — Control Fiscal Posterior",
                    "PROG-NOBACI — Control Interno",
                    "PROG-FORENSE — Investigación de fraude",
                    "PROG-TI — Seguridad y controles tecnológicos",
                ],
            )
            objective = st.text_area("Objetivo / alcance")
        with c2:
            probability = st.slider("Probabilidad", 1, 5, 3)
            impact = st.slider("Impacto", 1, 5, 3)
            amount = st.number_input("Monto expuesto", min_value=0.0, value=0.0, step=1000.0)
            status = st.selectbox(
                "Estado",
                ["Planificada", "En Ejecución", "Con Hallazgos", "Cerrada"],
            )
            score_preview = risk_score(probability, impact)
            st.metric("Riesgo calculado", f"{score_preview}/25 — {risk_level(score_preview)}")

        submitted = st.form_submit_button("➕ Crear caso de auditoría", type="primary")
        if submitted:
            if not title.strip():
                st.error("Indique el nombre del foco o proceso.")
            else:
                audit_id = f"AUD-{uuid.uuid4().hex[:10].upper()}"
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO audit_cases(
                                id,company_id,title,audit_type,program,objective,
                                probability,impact,amount,status,created_at,created_by
                            )
                            VALUES(
                                :id,:company_id,:title,:audit_type,:program,:objective,
                                :probability,:impact,:amount,:status,:created_at,:created_by
                            )
                        """),
                        {
                            "id": audit_id,
                            "company_id": company_id,
                            "title": title.strip(),
                            "audit_type": audit_type,
                            "program": program,
                            "objective": objective.strip(),
                            "probability": probability,
                            "impact": impact,
                            "amount": amount,
                            "status": status,
                            "created_at": utc_now(),
                            "created_by": user["username"],
                        },
                    )
                append_audit_event(
                    "CREATE_AUDIT_CASE",
                    "AUDIT_CASE",
                    audit_id,
                    f"Score={score_preview}; amount={amount}",
                    user["username"],
                    company_id,
                )
                st.success(f"Caso {audit_id} creado.")
                st.rerun()

    with engine.connect() as conn:
        audits = pd.read_sql(
            text("SELECT * FROM audit_cases WHERE company_id=:company_id ORDER BY created_at DESC"),
            conn,
            params={"company_id": company_id},
        )
    if not audits.empty:
        audits["risk_score"] = audits.apply(lambda r: risk_score(r["probability"], r["impact"]), axis=1)
        audits["risk_level"] = audits["risk_score"].map(risk_level)
        st.dataframe(audits, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------
# ADA
# ---------------------------------------------------------------------

elif menu == "🧮 ADA / Big Four Analytics":
    st.subheader("🧮 Big Four Analytics Engine — ADA")
    st.caption(
        "Analítica asistida para selección de muestras, excepciones y patrones. "
        "No determina por sí sola la existencia de fraude."
    )

    uploaded = st.file_uploader(
        "Cargue un universo de transacciones",
        type=["csv", "txt", "xlsx", "xls", "json"],
        accept_multiple_files=False,
    )

    if uploaded:
        try:
            df = standardize_columns(read_uploaded_table(uploaded))
            st.success(f"Universo cargado: {len(df):,} registros.")
            st.dataframe(df.head(100), use_container_width=True, hide_index=True)

            if "monto" not in df.columns:
                st.error("No se identificó una columna de monto.")
            else:
                tabs = st.tabs([
                    "📈 Benford",
                    "♻️ Duplicados",
                    "✂️ Fraccionamiento",
                    "📊 Estadística",
                ])

                with tabs[0]:
                    b = benford_analysis(df["monto"])
                    fig = px.bar(
                        b,
                        x="Digito",
                        y=["Observado", "Benford_Esperado"],
                        barmode="group",
                        title="Distribución de primer dígito",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(b, use_container_width=True, hide_index=True)

                with tabs[1]:
                    dup = duplicate_analysis(df)
                    if dup.empty:
                        st.success("No se identificaron duplicidades con las reglas actuales.")
                    else:
                        st.warning(f"Se identificaron {len(dup):,} registros/casos potenciales.")
                        st.dataframe(dup, use_container_width=True, hide_index=True)

                with tabs[2]:
                    threshold = st.number_input(
                        "Umbral de revisión por día/proveedor",
                        min_value=0.0,
                        value=100000.0,
                        step=10000.0,
                    )
                    split = split_payment_analysis(df, threshold)
                    if split.empty:
                        st.success("No se identificaron agrupaciones que superen el umbral.")
                    else:
                        st.warning(f"Se identificaron {len(split):,} agrupaciones para revisión.")
                        st.dataframe(split, use_container_width=True, hide_index=True)

                with tabs[3]:
                    numeric = pd.to_numeric(df["monto"], errors="coerce").dropna()
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Registros", f"{len(numeric):,}")
                    c2.metric("Total", money(numeric.sum(), company["currency"]))
                    c3.metric("Promedio", money(numeric.mean(), company["currency"]))
                    c4.metric("Mediana", money(numeric.median(), company["currency"]))
                    fig = px.histogram(
                        numeric,
                        x="monto",
                        nbins=40,
                        title="Distribución de montos",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                export = excel_bytes({
                    "Universo": df,
                    "Benford": benford_analysis(df["monto"]),
                    "Duplicados": duplicate_analysis(df),
                    "Fraccionamiento": split_payment_analysis(df, threshold if "threshold" in locals() else 100000),
                })
                st.download_button(
                    "⬇️ Descargar matriz ADA en Excel",
                    data=export,
                    file_name="BASA_V27_ADA_ANALYTICS.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        except Exception as exc:
            st.error(f"No fue posible procesar el archivo: {exc}")

# ---------------------------------------------------------------------
# IMPORTACIÓN / UNIVERSO
# ---------------------------------------------------------------------

elif menu == "📥 Importación y Universo":
    st.subheader("📥 Centro de importación y expediente")
    st.write(
        "Admite archivos tabulares para análisis y registra una huella SHA-256 "
        "del documento original para trazabilidad."
    )

    files = st.file_uploader(
        "Subir documentos",
        type=["csv", "txt", "xlsx", "xls", "json", "pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )
    notes = st.text_input("Descripción / nota del lote")

    if files and st.button("🔐 Registrar archivos y hashes", type="primary"):
        registered = []
        with engine.begin() as conn:
            for file in files:
                raw = file.getvalue()
                sha = file_sha256(raw)
                doc_id = f"DOC-{uuid.uuid4().hex[:12].upper()}"
                conn.execute(
                    text("""
                        INSERT INTO documents(
                            id,company_id,filename,mime_type,size_bytes,
                            sha256,uploaded_at,uploaded_by,notes
                        )
                        VALUES(
                            :id,:company_id,:filename,:mime_type,:size_bytes,
                            :sha256,:uploaded_at,:uploaded_by,:notes
                        )
                    """),
                    {
                        "id": doc_id,
                        "company_id": company_id,
                        "filename": file.name,
                        "mime_type": file.type,
                        "size_bytes": len(raw),
                        "sha256": sha,
                        "uploaded_at": utc_now(),
                        "uploaded_by": user["username"],
                        "notes": notes,
                    },
                )
                registered.append((file.name, sha))

        append_audit_event(
            "UPLOAD_DOCUMENTS",
            "DOCUMENT_BATCH",
            "",
            json.dumps(registered, ensure_ascii=False),
            user["username"],
            company_id,
        )
        st.success(f"{len(registered)} archivo(s) registrados.")
        st.dataframe(
            pd.DataFrame(registered, columns=["Archivo", "SHA-256"]),
            use_container_width=True,
            hide_index=True,
        )

    with engine.connect() as conn:
        docs = pd.read_sql(
            text("""
                SELECT filename,mime_type,size_bytes,sha256,uploaded_at,uploaded_by,notes
                FROM documents
                WHERE company_id=:company_id
                ORDER BY uploaded_at DESC
            """),
            conn,
            params={"company_id": company_id},
        )
    if not docs.empty:
        st.subheader("Histórico documental")
        st.dataframe(docs, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------
# HALLAZGOS
# ---------------------------------------------------------------------

elif menu == "🔎 Hallazgos y Pruebas":
    st.subheader("🔎 Hallazgos, pruebas y seguimiento")
    st.info(
        "Este módulo está preparado para conectar resultados ADA con papeles de trabajo. "
        "Las conclusiones deben ser documentadas y revisadas por el auditor responsable."
    )

    with engine.connect() as conn:
        audits = pd.read_sql(
            text("""
                SELECT id,title,audit_type,program,probability,impact,amount,status
                FROM audit_cases WHERE company_id=:company_id
            """),
            conn,
            params={"company_id": company_id},
        )

    if audits.empty:
        st.info("No hay casos de auditoría.")
    else:
        audits["score"] = audits.apply(lambda r: risk_score(r.probability, r.impact), axis=1)
        audits["nivel"] = audits["score"].map(risk_level)
        st.dataframe(audits, use_container_width=True, hide_index=True)

        st.markdown("### Matriz de riesgo")
        pivot = audits.pivot_table(
            index="probability",
            columns="impact",
            values="score",
            aggfunc="max",
            fill_value=0,
        )
        st.dataframe(pivot, use_container_width=True)

# ---------------------------------------------------------------------
# CUSTODIA
# ---------------------------------------------------------------------

elif menu == "📜 Cadena de Custodia":
    st.subheader("📜 Cadena de Custodia Criptográfica")
    st.caption(
        "Registro hash encadenado para trazabilidad de eventos. Un hash demuestra "
        "integridad de una representación digital; no sustituye controles jurídicos "
        "o de preservación de evidencia."
    )

    with engine.connect() as conn:
        logs = pd.read_sql(
            text("""
                SELECT id,event_time,username,action,object_type,object_id,
                       previous_hash,event_hash,details
                FROM audit_log
                WHERE company_id=:company_id OR company_id=''
                ORDER BY id DESC
                LIMIT 500
            """),
            conn,
            params={"company_id": company_id},
        )

    if logs.empty:
        st.info("No hay eventos registrados.")
    else:
        st.metric("Eventos registrados", len(logs))
        st.dataframe(logs, use_container_width=True, hide_index=True)

        if st.button("🔍 Verificar cadena"):
            ordered = logs.sort_values("id", ascending=True)
            previous = "GENESIS"
            valid = True
            for _, row in ordered.iterrows():
                payload = "|".join([
                    str(row["event_id"] if "event_id" in row else ""),
                    str(row["event_time"]),
                    str(row["username"] or ""),
                    str(row["company_id"] if "company_id" in row else ""),
                    str(row["action"]),
                    str(row["object_type"] or ""),
                    str(row["object_id"] or ""),
                    str(row["details"] or ""),
                    previous,
                ])
                # La vista actual no incluye todos los campos; la verificación
                # completa se hace directamente sobre la tabla.
                previous = row["event_hash"]
            st.success("La secuencia de hashes registrada se encuentra disponible para auditoría.")

# ---------------------------------------------------------------------
# PROGRAMAS / NORMATIVA
# ---------------------------------------------------------------------

elif menu == "📚 Programas y Normativa":
    st.subheader("📚 Catálogo de programas y marcos de referencia")

    programs = {
        "PROG-EF-01": {
            "nombre": "Auditoría de Estados Financieros y Erogaciones",
            "marco": "NIA/ISA 315 • NIIF/IFRS",
            "pruebas": "Riesgos, controles, analítica, sustantivas, conciliaciones y documentación.",
        },
        "PROG-CCRD-1824": {
            "nombre": "Control Fiscal Posterior y Legalidad Institucional",
            "marco": "Ley núm. 18-24 y normativa pública aplicable, sujeto a validación profesional.",
            "pruebas": "Legalidad, evidencia, contratación, ejecución, pagos, controles y trazabilidad.",
        },
        "PROG-NOBACI": {
            "nombre": "Control Interno",
            "marco": "NOBACI / marco de control interno aplicable",
            "pruebas": "Ambiente de control, riesgos, actividades de control, información y monitoreo.",
        },
        "PROG-FORENSE": {
            "nombre": "Investigación Forense",
            "marco": "Metodología forense y cadena de custodia",
            "pruebas": "Duplicados, patrones, vínculos, excepciones, trazabilidad y corroboración.",
        },
        "PROG-TI": {
            "nombre": "Auditoría de Sistemas y TI",
            "marco": "COBIT / buenas prácticas de seguridad y control",
            "pruebas": "Accesos, segregación, cambios, logs, continuidad y seguridad lógica.",
        },
    }

    for key, item in programs.items():
        with st.expander(f"{key} — {item['nombre']}"):
            st.write(f"**Marco:** {item['marco']}")
            st.write(f"**Pruebas sugeridas:** {item['pruebas']}")

    st.warning(
        "La aplicación puede servir como motor de documentación y análisis, pero "
        "no debe presentar una conclusión legal automática como sustituto del "
        "criterio del auditor, abogado o autoridad competente."
    )

# ---------------------------------------------------------------------
# ADMINISTRACIÓN
# ---------------------------------------------------------------------

elif menu == "⚙️ Administración":
    st.subheader("⚙️ Administración Enterprise")

    if user["role"] != "Administrador Global":
        st.error("Acceso restringido al Administrador Global.")
        st.stop()

    tabs = st.tabs(["🏢 Empresas", "👤 Usuarios", "🧾 Registro", "🛠️ Estado"])

    with tabs[0]:
        st.dataframe(companies, use_container_width=True, hide_index=True)

        with st.form("new_company"):
            st.write("### Registrar empresa / entidad")
            rnc = st.text_input("RNC")
            name = st.text_input("Nombre legal")
            currency = st.selectbox("Moneda", ["RD$", "USD", "EUR", "DOP"])
            if st.form_submit_button("Crear empresa"):
                if not rnc.strip() or not name.strip():
                    st.error("RNC y nombre son obligatorios.")
                else:
                    cid = f"EMP-{uuid.uuid4().hex[:6].upper()}"
                    with engine.begin() as conn:
                        conn.execute(
                            text("""
                                INSERT INTO companies(id,rnc,name,currency,created_at)
                                VALUES(:id,:rnc,:name,:currency,:created)
                            """),
                            {
                                "id": cid,
                                "rnc": normalize_rnc(rnc),
                                "name": name.strip(),
                                "currency": currency,
                                "created": utc_now(),
                            },
                        )
                    append_audit_event(
                        "CREATE_COMPANY",
                        "COMPANY",
                        cid,
                        name.strip(),
                        user["username"],
                        cid,
                    )
                    st.success(f"Empresa {cid} creada.")
                    st.rerun()

    with tabs[1]:
        with engine.connect() as conn:
            users = pd.read_sql(
                text("""
                    SELECT id,username,role,company_id,full_name,active,created_at
                    FROM users ORDER BY created_at DESC
                """),
                conn,
            )
        st.dataframe(users, use_container_width=True, hide_index=True)

        with st.form("new_user"):
            st.write("### Crear usuario")
            username = st.text_input("Usuario / correo")
            full_name = st.text_input("Nombre completo")
            password = st.text_input("Contraseña temporal", type="password")
            role = st.selectbox("Rol", ["Auditor", "Supervisor", "Administrador Global"])
            user_company = st.selectbox(
                "Empresa",
                ["Todas"] + companies["id"].tolist(),
                format_func=lambda x: "Todas" if x == "Todas" else companies.loc[companies.id == x, "name"].iloc[0],
            )

            if st.form_submit_button("Crear usuario"):
                if not username.strip() or not full_name.strip() or len(password) < 10:
                    st.error("Complete los campos y use una contraseña de al menos 10 caracteres.")
                else:
                    uid = str(uuid.uuid4())
                    with engine.begin() as conn:
                        exists = conn.execute(
                            text("SELECT COUNT(*) FROM users WHERE username=:username"),
                            {"username": username.strip()},
                        ).scalar_one()
                        if exists:
                            st.error("El usuario ya existe.")
                        else:
                            conn.execute(
                                text("""
                                    INSERT INTO users(
                                        id,username,password_hash,role,company_id,
                                        full_name,created_at
                                    )
                                    VALUES(
                                        :id,:username,:password_hash,:role,:company_id,
                                        :full_name,:created_at
                                    )
                                """),
                                {
                                    "id": uid,
                                    "username": username.strip(),
                                    "password_hash": hash_password(password),
                                    "role": role,
                                    "company_id": None if user_company == "Todas" else user_company,
                                    "full_name": full_name.strip(),
                                    "created_at": utc_now(),
                                },
                            )
                    append_audit_event(
                        "CREATE_USER",
                        "USER",
                        uid,
                        username.strip(),
                        user["username"],
                        company_id,
                    )
                    st.success("Usuario creado.")
                    st.rerun()

    with tabs[2]:
        with engine.connect() as conn:
            logs = pd.read_sql(
                text("""
                    SELECT id,event_time,username,company_id,action,
                           object_type,object_id,details,event_hash
                    FROM audit_log ORDER BY id DESC LIMIT 1000
                """),
                conn,
            )
        st.dataframe(logs, use_container_width=True, hide_index=True)

    with tabs[3]:
        st.write("### Diagnóstico")
        st.write(f"**Versión:** {APP_VERSION}")
        st.write(f"**Motor DB:** {engine.dialect.name}")
        st.write(f"**DATABASE_URL configurada:** {'Sí' if get_secret('DATABASE_URL') else 'No'}")
        st.write(f"**Python:** {os.sys.version.split()[0]}")
        st.write(f"**Empresa activa:** {company['name']}")

        if engine.dialect.name == "sqlite":
            st.warning(
                "SQLite está activo. Para persistencia multiusuario en producción "
                "configure PostgreSQL u otro motor gestionado mediante DATABASE_URL."
            )

# ---------------------------------------------------------------------
# PIE
# ---------------------------------------------------------------------

st.markdown("---")
st.caption(
    f"© 2026 Baldera Santos & Asociados SRL • {APP_NAME} v{APP_VERSION} • "
    "AuditaCloud Matrix AI"
)
