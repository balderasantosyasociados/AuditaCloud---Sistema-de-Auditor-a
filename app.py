# ================================================================
# BASA_03_TODOINTEGRADO — STREAMLIT CLOUD
# Incluye:
#   BASA_05_FISCAL
#   BASA_06_FORENSE
#   BASA_03_TODOINTEGRADO
#
# Baldera Santos & Asociados SRL
# ================================================================
#
# DISEÑO:
# - Un solo archivo app.py
# - Sin pip install durante la ejecución
# - SQLite para demo/local
# - PostgreSQL mediante DATABASE_URL para producción
# - Secrets para credenciales
# - Multiempresa
# - Fiscal: 606 / 607 / 608, validación, conciliación y exportación
# - Forense: duplicados, fuzzy, Benford, fraccionamiento, riesgo
# - Integrado: dashboard, expediente, cadena SHA-256 y trazabilidad
#
# ================================================================

from __future__ import annotations

import io
import os
import re
import json
import uuid
import math
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# ================================================================
# 1. CONFIGURACIÓN
# ================================================================

APP_NAME = "BASA 03 TODO INTEGRADO"
VERSION = "30.0.0"
MAX_FILE_MB = 50

st.set_page_config(
    page_title=f"{APP_NAME} | Fiscal + Forense + Integrado",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.basa-header {
    padding: 18px 22px;
    border-radius: 16px;
    border: 1px solid rgba(120,120,120,.25);
    margin-bottom: 18px;
}
.module-card {
    border: 1px solid rgba(120,120,120,.25);
    border-radius: 14px;
    padding: 14px;
    min-height: 110px;
}
.small {font-size: .82rem; opacity: .75;}
</style>
""", unsafe_allow_html=True)


# ================================================================
# 2. UTILIDADES
# ================================================================
def log_event_tx(
    conn,
    action,
    object_type="",
    object_id="",
    details="",
    username="",
    company_id=""
):
    """Registra el evento dentro de la transacción existente."""

    previous = conn.execute(text("""
        SELECT event_hash
        FROM event_log
        ORDER BY id DESC
        LIMIT 1
    """)).scalar() or "GENESIS"

    event_id = str(uuid.uuid4())
    event_time = now_iso()

    payload = "|".join([
        event_id,
        event_time,
        username,
        company_id or "",
        action,
        object_type,
        object_id,
        str(details),
        previous
    ])

    event_hash = hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()

    conn.execute(text("""
        INSERT INTO event_log (
            event_id, event_time, username,
            company_id, action, object_type,
            object_id, details, previous_hash,
            event_hash
        )
        VALUES (
            :event_id, :event_time, :username,
            :company_id, :action, :object_type,
            :object_id, :details, :previous_hash,
            :event_hash
        )
    """), {
        "event_id": event_id,
        "event_time": event_time,
        "username": username,
        "company_id": company_id or "",
        "action": action,
        "object_type": object_type,
        "object_id": object_id,
        "details": str(details)[:5000],
        "previous_hash": previous,
        "event_hash": event_hash
    })

    return event_hash
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def secret(name: str, default=None):
    try:
        value = st.secrets.get(name)
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def normalize_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())

def normalize_rnc(value) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", normalize_text(value)).upper()

def money(value, currency="RD$"):
    try:
        return f"{currency} {float(value):,.2f}"
    except Exception:
        return f"{currency} 0.00"

def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        if isinstance(value, str):
            value = (
                value.replace("RD$", "")
                     .replace("RD", "")
                     .replace("$", "")
                     .replace(",", "")
                     .strip()
            )
        return float(value)
    except Exception:
        return default

def risk_score(probability, impact):
    return max(1, min(25, int(probability) * int(impact)))

def risk_level(score):
    if score >= 20:
        return "CRÍTICO"
    if score >= 15:
        return "ALTO"
    if score >= 8:
        return "MEDIO"
    return "BAJO"

def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        310_000
    )
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"

def password_verify(password: str, encoded: str) -> bool:
    try:
        algo, rounds, salt_hex, digest_hex = encoded.split("$")
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            bytes.fromhex(salt_hex),
            int(rounds),
        ).hex()
        return secrets.compare_digest(digest, digest_hex)
    except Exception:
        return False


# ================================================================
# 3. BASE DE DATOS
# ================================================================

def db_url():
    return secret("DATABASE_URL", "sqlite:///basa_03_todointegrado.db")

@st.cache_resource
def engine_for(url: str) -> Engine:
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
        )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

ENGINE = engine_for(db_url())


def db_init():
    with ENGINE.begin() as conn:
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
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            mime_type TEXT,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            module TEXT NOT NULL,
            uploaded_by TEXT,
            uploaded_at TEXT NOT NULL,
            notes TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS audit_cases (
            id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            title TEXT NOT NULL,
            module TEXT NOT NULL,
            audit_type TEXT NOT NULL,
            program TEXT,
            objective TEXT,
            probability INTEGER NOT NULL DEFAULT 1,
            impact INTEGER NOT NULL DEFAULT 1,
            amount REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Planificada',
            created_by TEXT,
            created_at TEXT NOT NULL
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS event_log (
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

db_init()


# ================================================================
# 4. DATOS INICIALES
# ================================================================

def bootstrap():
    with ENGINE.begin() as conn:
        companies = conn.execute(
            text("SELECT COUNT(*) FROM companies")
        ).scalar_one()

        if companies == 0:
            conn.execute(text("""
                INSERT INTO companies(id,rnc,name,currency,created_at)
                VALUES(:id,:rnc,:name,:currency,:created)
            """), {
                "id": "EMP-BASA-001",
                "rnc": secret("DEFAULT_RNC", "133378711"),
                "name": secret(
                    "DEFAULT_COMPANY",
                    "Baldera Santos & Asociados SRL"
                ),
                "currency": "RD$",
                "created": now_iso(),
            })

        users = conn.execute(
            text("SELECT COUNT(*) FROM users")
        ).scalar_one()

        if users == 0:
            admin_password = secret("ADMIN_PASSWORD")
            if not admin_password:
                admin_password = secrets.token_urlsafe(14)
                st.session_state["_temporary_password"] = admin_password

            conn.execute(text("""
                INSERT INTO users(
                    id,username,password_hash,role,company_id,
                    full_name,created_at
                )
                VALUES(
                    :id,:username,:password_hash,:role,:company_id,
                    :full_name,:created_at
                )
            """), {
                "id": str(uuid.uuid4()),
                "username": secret("ADMIN_USERNAME", "admin"),
                "password_hash": password_hash(admin_password),
                "role": "Administrador Global",
                "company_id": None,
                "full_name": "Administrador BASA",
                "created_at": now_iso(),
            })

bootstrap()


# ================================================================
# 5. CADENA DE CUSTODIA
# ================================================================

def last_hash():
    with ENGINE.connect() as conn:
        row = conn.execute(
            text("""
                SELECT event_hash
                FROM event_log
                ORDER BY id DESC
                LIMIT 1
            """)
        ).scalar()
    return row or "GENESIS"

def log_event(
    action,
    object_type="",
    object_id="",
    details="",
    username="",
    company_id="",
):
    previous = last_hash()
    event_id = str(uuid.uuid4())
    event_time = now_iso()

    payload = "|".join([
        event_id,
        event_time,
        username,
        company_id or "",
        action,
        object_type,
        object_id,
        details,
        previous,
    ])

    event_hash = hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()

    with ENGINE.begin() as conn:
        conn.execute(text("""
            INSERT INTO event_log(
                event_id,event_time,username,company_id,
                action,object_type,object_id,details,
                previous_hash,event_hash
            )
            VALUES(
                :event_id,:event_time,:username,:company_id,
                :action,:object_type,:object_id,:details,
                :previous_hash,:event_hash
            )
        """), {
            "event_id": event_id,
            "event_time": event_time,
            "username": username,
            "company_id": company_id or "",
            "action": action,
            "object_type": object_type,
            "object_id": object_id,
            "details": details[:5000],
            "previous_hash": previous,
            "event_hash": event_hash,
        })

    return event_hash


# ================================================================
# 6. AUTENTICACIÓN
# ================================================================

def get_user():
    uid = st.session_state.get("user_id")
    if not uid:
        return None

    with ENGINE.connect() as conn:
        row = conn.execute(text("""
            SELECT id,username,role,company_id,full_name
            FROM users
            WHERE id=:id AND active=1
        """), {"id": uid}).mappings().first()

    return dict(row) if row else None


def login():
    st.markdown(f"""
    <div class="basa-header">
        <h1>🏛️ {APP_NAME}</h1>
        <b>Fiscal + Forense + Inteligencia de Auditoría</b>
        <div class="small">Versión {VERSION}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("🔐 Acceso seguro")
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")

        if st.button(
            "Entrar al sistema",
            type="primary",
            use_container_width=True
        ):
            with ENGINE.connect() as conn:
                row = conn.execute(text("""
                    SELECT *
                    FROM users
                    WHERE username=:username
                    AND active=1
                """), {"username": username.strip()}).mappings().first()

            if row and password_verify(password, row["password_hash"]):
                st.session_state.user_id = row["id"]

                log_event(
                    "LOGIN",
                    "USER",
                    row["id"],
                    "Inicio de sesión",
                    row["username"],
                    row["company_id"] or "",
                )

                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    with c2:
        st.subheader("☁️ Configuración Cloud")
        temp = st.session_state.get("_temporary_password")

        if temp:
            st.warning(
                "No existe ADMIN_PASSWORD en Secrets. "
                "Se generó una contraseña temporal."
            )
            st.code(temp)

        st.info("""
        Para producción configure en Streamlit Secrets:

        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD = "una-clave-segura"
        DATABASE_URL = "postgresql+psycopg://..."
        """)


# ================================================================
# 7. LECTURA DE ARCHIVOS
# ================================================================

def read_table(uploaded):
    name = uploaded.name.lower()
    raw = uploaded.getvalue()

    if len(raw) > MAX_FILE_MB * 1024 * 1024:
        raise ValueError(
            f"El archivo supera el límite de {MAX_FILE_MB} MB."
        )

    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(raw))

    if name.endswith((".csv", ".txt")):
        return pd.read_csv(io.BytesIO(raw))

    if name.endswith(".json"):
        return pd.read_json(io.BytesIO(raw))

    raise ValueError(
        "Formato no soportado para análisis tabular."
    )


def standardize(df):
    out = df.copy()

    rename = {}
    for col in out.columns:
        clean = str(col).strip().lower()
        clean = re.sub(r"[^a-z0-9áéíóúñ]+", "_", clean)
        rename[col] = clean.strip("_")

    out.rename(columns=rename, inplace=True)

    aliases = {
        "rnc": [
            "rnc",
            "rnc_proveedor",
            "proveedor_rnc",
            "documento",
        ],
        "proveedor": [
            "proveedor",
            "nombre_proveedor",
            "suplidor",
            "nombre",
        ],
        "monto": [
            "monto",
            "importe",
            "total",
            "valor",
            "monto_factura",
        ],
        "fecha": [
            "fecha",
            "fecha_factura",
            "fecha_registro",
        ],
        "ncf": [
            "ncf",
            "numero",
            "no_factura",
            "factura",
            "comprobante",
        ],
    }

    for target, names in aliases.items():
        if target not in out.columns:
            for name in names:
                if name in out.columns:
                    out[target] = out[name]
                    break

    if "monto" in out.columns:
        out["monto"] = out["monto"].map(safe_float)

    if "rnc" in out.columns:
        out["rnc_normalizado"] = out["rnc"].map(normalize_rnc)

    if "proveedor" in out.columns:
        out["proveedor_normalizado"] = (
            out["proveedor"].map(normalize_text)
        )

    if "fecha" in out.columns:
        out["fecha_normalizada"] = pd.to_datetime(
            out["fecha"],
            errors="coerce"
        )

    return out


# ================================================================
# 8. FISCAL — 606 / 607 / 608
# ================================================================

FIELDS_606 = [
    "rnc_cedula",
    "tipo_bienes_servicios",
    "ncf",
    "ncf_modificado",
    "fecha_comprobante",
    "fecha_pago",
    "monto_facturado",
    "itbis_facturado",
    "itbis_retenido",
    "isr_retenido",
    "itbis_proporcionalidad",
    "itbis_costo",
    "itbis_adelantado",
    "itbis_retenido_terceros",
    "monto_sujeto_retencion",
    "tipo_retencion",
    "forma_pago",
    "numero_comprobante",
    "fecha_retencion",
    "monto_retencion",
    "rnc_agente_retencion",
    "nombre_razon_social",
    "estado",
]

FIELDS_607 = [
    "rnc_cedula",
    "tipo_ingreso",
    "ncf",
    "ncf_modificado",
    "fecha_comprobante",
    "monto_facturado",
    "itbis_facturado",
    "itbis_retenido",
    "monto_exento",
    "monto_no_gravado",
    "forma_pago",
    "tipo_operacion",
]

FIELDS_608 = [
    "ncf",
    "ncf_modificado",
    "fecha_comprobante",
    "tipo_anulacion",
    "motivo",
]

def fiscal_mapping(df, form):
    fields = FIELDS_606 if form == "606" else FIELDS_607 if form == "607" else FIELDS_608

    result = pd.DataFrame(columns=fields)

    for field in fields:
        if field in df.columns:
            result[field] = df[field]

    # Alias adicionales
    if "rnc_cedula" in result.columns and result["rnc_cedula"].isna().all():
        if "rnc" in df.columns:
            result["rnc_cedula"] = df["rnc"]

    if "ncf" in result.columns and result["ncf"].isna().all():
        for c in ["numero", "factura", "comprobante"]:
            if c in df.columns:
                result["ncf"] = df[c]
                break

    if "monto_facturado" in result.columns and result["monto_facturado"].isna().all():
        if "monto" in df.columns:
            result["monto_facturado"] = df["monto"]

    for c in ["monto_facturado", "itbis_facturado", "itbis_retenido",
              "isr_retenido", "monto_exento", "monto_no_gravado",
              "monto_retencion"]:
        if c in result.columns:
            result[c] = result[c].map(safe_float)

    if "rnc_cedula" in result.columns:
        result["rnc_cedula"] = result["rnc_cedula"].map(normalize_rnc)

    return result

def fiscal_validation(df, form):
    issues = []

    if df.empty:
        return pd.DataFrame(
            columns=["Fila", "Campo", "Tipo", "Detalle"]
        )

    required = {
        "606": ["rnc_cedula", "ncf", "monto_facturado"],
        "607": ["rnc_cedula", "ncf", "monto_facturado"],
        "608": ["ncf", "fecha_comprobante"],
    }[form]

    for idx, row in df.iterrows():
        excel_row = idx + 2

        for field in required:
            value = row.get(field)

            if value is None or str(value).strip() in ("", "nan", "None"):
                issues.append({
                    "Fila": excel_row,
                    "Campo": field,
                    "Tipo": "ERROR",
                    "Detalle": "Campo requerido vacío",
                })

        if "rnc_cedula" in df.columns:
            rnc = normalize_rnc(row.get("rnc_cedula"))
            if rnc and len(rnc) not in (9, 11):
                issues.append({
                    "Fila": excel_row,
                    "Campo": "rnc_cedula",
                    "Tipo": "ADVERTENCIA",
                    "Detalle": "Longitud de RNC/Cédula no estándar",
                })

        if "monto_facturado" in df.columns:
            monto = safe_float(row.get("monto_facturado"))
            if monto < 0:
                issues.append({
                    "Fila": excel_row,
                    "Campo": "monto_facturado",
                    "Tipo": "ERROR",
                    "Detalle": "Monto negativo",
                })

    return pd.DataFrame(
        issues,
        columns=["Fila", "Campo", "Tipo", "Detalle"]
    )

def build_dgii_txt(df):
    # Generador de texto delimitado por |.
    # La estructura definitiva debe validarse contra el formato
    # DGII correspondiente al período antes de remitirla.
    lines = []
    for _, row in df.iterrows():
        values = []
        for value in row.tolist():
            if pd.isna(value):
                value = ""
            value = str(value).replace("|", " ")
            values.append(value)
        lines.append("|".join(values))
    return "\n".join(lines)


# ================================================================
# 9. FORENSE
# ================================================================

def token_similarity(a, b):
    aa = set(re.findall(r"[a-z0-9]+", str(a).lower()))
    bb = set(re.findall(r"[a-z0-9]+", str(b).lower()))

    if not aa or not bb:
        return 0.0

    return len(aa & bb) / len(aa | bb)

def exact_duplicates(df):
    cols = [
        c for c in [
            "rnc_normalizado",
            "proveedor_normalizado",
            "monto",
            "fecha_normalizada",
        ]
        if c in df.columns
    ]

    if not cols:
        return pd.DataFrame()

    mask = df.duplicated(
        subset=cols,
        keep=False
    )

    result = df.loc[mask].copy()
    result["tipo_hallazgo"] = "DUPLICADO_EXACTO"
    return result

def fuzzy_duplicates(df):
    if "proveedor_normalizado" not in df.columns:
        return pd.DataFrame()

    rows = []

    n = min(len(df), 1000)

    for i in range(n):
        for j in range(i + 1, n):
            a = df.iloc[i]
            b = df.iloc[j]

            if "rnc_normalizado" in df.columns:
                if (
                    a["rnc_normalizado"]
                    and b["rnc_normalizado"]
                    and a["rnc_normalizado"] != b["rnc_normalizado"]
                ):
                    continue

            sim = token_similarity(
                a["proveedor_normalizado"],
                b["proveedor_normalizado"]
            )

            ma = safe_float(a.get("monto"))
            mb = safe_float(b.get("monto"))

            diff = abs(ma - mb) / max(abs(ma), abs(mb), 1)

            if sim >= 0.70 and diff <= 0.02 and sim < 1:
                rows.append({
                    "Fila_A": i + 2,
                    "Fila_B": j + 2,
                    "Proveedor_A": a["proveedor_normalizado"],
                    "Proveedor_B": b["proveedor_normalizado"],
                    "RNC": a.get("rnc_normalizado", ""),
                    "Monto_A": ma,
                    "Monto_B": mb,
                    "Similitud": round(sim, 4),
                    "Diferencia_%": round(diff * 100, 2),
                    "tipo_hallazgo": "POSIBLE_DUPLICADO_FUZZY",
                })

    return pd.DataFrame(rows)

def benford(df):
    if "monto" not in df.columns:
        return pd.DataFrame()

    values = pd.to_numeric(
        df["monto"],
        errors="coerce"
    )

    values = values[values > 0]

    if values.empty:
        return pd.DataFrame()

    first = (
        values.astype(str)
        .str.replace(r"\D", "", regex=True)
        .str[0]
    )

    observed = (
        first.value_counts()
        .reindex(list("123456789"), fill_value=0)
    )

    observed = observed / observed.sum()

    expected = {
        str(d): math.log10(1 + 1 / d)
        for d in range(1, 10)
    }

    return pd.DataFrame({
        "Digito": list("123456789"),
        "Observado": [
            observed[d] for d in "123456789"
        ],
        "Benford": [
            expected[d] for d in "123456789"
        ],
    })

def split_payments(df, threshold=100000):
    required = {
        "proveedor_normalizado",
        "monto",
    }

    if not required.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()

    if "fecha_normalizada" in work.columns:
        work["dia"] = work[
            "fecha_normalizada"
        ].dt.date
    else:
        work["dia"] = "SIN_FECHA"

    grouped = (
        work.groupby(
            ["proveedor_normalizado", "dia"],
            dropna=False
        )
        .agg(
            operaciones=("monto", "count"),
            total=("monto", "sum"),
            promedio=("monto", "mean"),
        )
        .reset_index()
    )

    result = grouped[
        (grouped["operaciones"] >= 2)
        & (grouped["total"] >= threshold)
    ].copy()

    result["nivel"] = np.where(
        result["total"] >= threshold * 2,
        "ALTO",
        "MEDIO"
    )

    return result.sort_values(
        "total",
        ascending=False
    )


# ================================================================
# 10. EXPORTACIÓN
# ================================================================

def excel_export(sheets):
    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl"
    ) as writer:
        for name, df in sheets.items():
            df = df if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
            df.to_excel(
                writer,
                index=False,
                sheet_name=str(name)[:31]
            )

    return buffer.getvalue()


# ================================================================
# 11. LOGIN
# ================================================================

if "user_id" not in st.session_state:
    st.session_state.user_id = None

USER = get_user()

if USER is None:
    login()
    st.stop()


# ================================================================
# 12. EMPRESA
# ================================================================

with ENGINE.connect() as conn:
    companies = pd.read_sql(
        text("""
            SELECT id,rnc,name,currency
            FROM companies
            WHERE active=1
            ORDER BY name
        """),
        conn
    )

if companies.empty:
    st.error("No existe una empresa activa.")
    st.stop()

if USER["role"] == "Administrador Global":
    selected_company = st.sidebar.selectbox(
        "🏢 Empresa / entidad",
        companies["id"].tolist(),
        format_func=lambda x:
            companies.loc[
                companies.id == x,
                "name"
            ].iloc[0]
    )
else:
    selected_company = USER["company_id"]

if not selected_company:
    st.error("El usuario no tiene empresa asignada.")
    st.stop()

company = companies[
    companies.id == selected_company
].iloc[0].to_dict()


# ================================================================
# 13. SIDEBAR
# ================================================================

st.sidebar.markdown(
    f"## 🏛️ {APP_NAME}"
)

st.sidebar.caption(
    f"v{VERSION}"
)

st.sidebar.write(
    f"**Usuario:** {USER['full_name']}"
)

st.sidebar.write(
    f"**Rol:** {USER['role']}"
)

if st.sidebar.button(
    "🚪 Cerrar sesión",
    use_container_width=True
):
    log_event_tx(
    conn,
    "CREATE_USER",
    "USER",
    uid,
    username.strip(),
    USER["username"],
    selected_company
)
(
        "LOGOUT",
        "USER",
        USER["id"],
        "",
        USER["username"],
        selected_company,
    )

    st.session_state.user_id = None
    st.rerun()

st.sidebar.markdown("---")

MODULE = st.sidebar.radio(
    "MÓDULOS PRINCIPALES",
    [
        "🏛️ BASA_03_todointegrado",
        "🧾 BASA_05_Fiscal",
        "🔎 BASA_06_Forense",
        "📊 Dashboard",
        "📜 Cadena de Custodia",
        "⚙️ Administración",
    ]
)


# ================================================================
# 14. CABECERA
# ================================================================

st.markdown(f"""
<div class="basa-header">
<h1>🏛️ {APP_NAME}</h1>
<b>{company['name']}</b><br>
RNC: {company['rnc']} &nbsp; | &nbsp;
Moneda: {company['currency']} &nbsp; | &nbsp;
Módulo: {MODULE}
</div>
""", unsafe_allow_html=True)


# ================================================================
# 15. BASA_05_FISCAL
# ================================================================

if MODULE == "🧾 BASA_05_Fiscal":

    st.title("🧾 BASA_05_Fiscal")
    st.caption(
        "Centro fiscal integrado para 606 / 607 / 608, "
        "validación, conciliación y generación de archivo de trabajo."
    )

    fiscal_form = st.selectbox(
        "Seleccione formulario",
        ["606", "607", "608"]
    )

    uploaded = st.file_uploader(
        f"Cargar universo para {fiscal_form}",
        type=[
            "csv",
            "txt",
            "xlsx",
            "xls",
            "json",
        ],
        key=f"fiscal_{fiscal_form}"
    )

    if uploaded:

        try:
            raw = uploaded.getvalue()

            original = read_table(uploaded)
            normalized = standardize(original)
            fiscal = fiscal_mapping(
                normalized,
                fiscal_form
            )

            st.success(
                f"Archivo cargado correctamente: "
                f"{len(original):,} registros."
            )

            t1, t2, t3, t4 = st.tabs([
                "📄 Universo",
                "✅ Validación",
                "🔄 Conciliación",
                "⬇️ Exportación",
            ])

            with t1:
                st.dataframe(
                    fiscal,
                    use_container_width=True,
                    hide_index=True
                )

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Registros",
                    len(fiscal)
                )

                if "monto_facturado" in fiscal:
                    total = fiscal[
                        "monto_facturado"
                    ].sum()

                    c2.metric(
                        "Monto",
                        money(
                            total,
                            company["currency"]
                        )
                    )

                c3.metric(
                    "SHA-256",
                    sha256_bytes(raw)[:16] + "..."
                )

            with t2:
                validation = fiscal_validation(
                    fiscal,
                    fiscal_form
                )

                errors = (
                    (validation["Tipo"] == "ERROR").sum()
                    if not validation.empty
                    else 0
                )

                warnings = (
                    (validation["Tipo"] == "ADVERTENCIA").sum()
                    if not validation.empty
                    else 0
                )

                c1, c2 = st.columns(2)

                c1.metric(
                    "Errores",
                    errors
                )

                c2.metric(
                    "Advertencias",
                    warnings
                )

                if validation.empty:
                    st.success(
                        "No se detectaron inconsistencias "
                        "con las reglas básicas."
                    )
                else:
                    st.dataframe(
                        validation,
                        use_container_width=True,
                        hide_index=True
                    )

            with t3:
                st.subheader(
                    "Conciliación interna"
                )

                if "monto_facturado" in fiscal.columns:
                    total = fiscal[
                        "monto_facturado"
                    ].sum()

                    st.metric(
                        "Total universo",
                        money(
                            total,
                            company["currency"]
                        )
                    )

                    if "rnc_cedula" in fiscal.columns:
                        proveedores = (
                            fiscal[
                                "rnc_cedula"
                            ]
                            .replace("", np.nan)
                            .nunique()
                        )

                        st.metric(
                            "RNC/Cédulas únicos",
                            int(proveedores)
                        )

                st.info(
                    "Para conciliación contra DGII "
                    "se debe cargar también el universo "
                    "de referencia y definir período y "
                    "criterio de comparación."
                )

            with t4:
                txt = build_dgii_txt(
                    fiscal
                )

                st.download_button(
                    "⬇️ Descargar TXT de trabajo",
                    data=txt.encode("utf-8"),
                    file_name=f"BASA_{fiscal_form}_TRABAJO.txt",
                    mime="text/plain"
                )

                xlsx = excel_export({
                    f"DGII_{fiscal_form}": fiscal,
                    "Validacion": fiscal_validation(
                        fiscal,
                        fiscal_form
                    ),
                })

                st.download_button(
                    "⬇️ Descargar Excel de auditoría",
                    data=xlsx,
                    file_name=f"BASA_{fiscal_form}_AUDITORIA.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            doc_id = f"DOC-{uuid.uuid4().hex[:10].upper()}"

            with ENGINE.begin() as conn:
                conn.execute(text("""
                    INSERT INTO documents(
                        id,company_id,filename,mime_type,
                        size_bytes,sha256,module,
                        uploaded_by,uploaded_at,notes
                    )
                    VALUES(
                        :id,:company_id,:filename,:mime_type,
                        :size_bytes,:sha256,:module,
                        :uploaded_by,:uploaded_at,:notes
                    )
                """), {
                    "id": doc_id,
                    "company_id": selected_company,
                    "filename": uploaded.name,
                    "mime_type": uploaded.type,
                    "size_bytes": len(raw),
                    "sha256": sha256_bytes(raw),
                    "module": f"BASA_05_Fiscal_{fiscal_form}",
                    "uploaded_by": USER["username"],
                    "uploaded_at": now_iso(),
                    "notes": "Archivo fiscal procesado",
                })

            log_event(
                "FISCAL_FILE_PROCESSED",
                "DOCUMENT",
                doc_id,
                f"Formulario={fiscal_form}; filas={len(fiscal)}",
                USER["username"],
                selected_company,
            )

        except Exception as exc:
            st.error(
                f"No fue posible procesar el archivo: {exc}"
            )


# ================================================================
# 16. BASA_06_FORENSE
# ================================================================

elif MODULE == "🔎 BASA_06_Forense":

    st.title("🔎 BASA_06_Forense")

    st.caption(
        "Motor de análisis forense y auditoría asistida."
    )

    uploaded = st.file_uploader(
        "Cargar universo para análisis forense",
        type=[
            "csv",
            "txt",
            "xlsx",
            "xls",
            "json",
        ],
        key="forensic_file"
    )

    if uploaded:

        try:
            original = read_table(uploaded)
            df = standardize(original)

            st.success(
                f"Universo cargado: {len(df):,} registros."
            )

            tabs = st.tabs([
                "♻️ Duplicados",
                "🧠 Fuzzy",
                "📈 Benford",
                "✂️ Fraccionamiento",
                "⚠️ Riesgo",
            ])

            exact = exact_duplicates(df)
            fuzzy = fuzzy_duplicates(df)
            ben = benford(df)

            with tabs[0]:
                if exact.empty:
                    st.success(
                        "No se detectaron duplicados exactos."
                    )
                else:
                    st.warning(
                        f"Se detectaron {len(exact):,} "
                        "registros potencialmente duplicados."
                    )
                    st.dataframe(
                        exact,
                        use_container_width=True,
                        hide_index=True
                    )

            with tabs[1]:
                if fuzzy.empty:
                    st.success(
                        "No se detectaron coincidencias fuzzy "
                        "bajo las reglas actuales."
                    )
                else:
                    st.warning(
                        f"Se detectaron {len(fuzzy):,} "
                        "posibles coincidencias."
                    )
                    st.dataframe(
                        fuzzy,
                        use_container_width=True,
                        hide_index=True
                    )

            with tabs[2]:
                if ben.empty:
                    st.info(
                        "No hay datos numéricos suficientes."
                    )
                else:
                    fig = px.bar(
                        ben,
                        x="Digito",
                        y=[
                            "Observado",
                            "Benford"
                        ],
                        barmode="group",
                        title="Prueba exploratoria de Benford"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

                    st.dataframe(
                        ben,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.warning(
                        "Benford es una prueba exploratoria. "
                        "Una desviación no demuestra fraude."
                    )

            with tabs[3]:
                threshold = st.number_input(
                    "Umbral de revisión",
                    min_value=0.0,
                    value=100000.0,
                    step=10000.0
                )

                split = split_payments(
                    df,
                    threshold
                )

                if split.empty:
                    st.success(
                        "No se identificaron agrupaciones "
                        "que superen el umbral."
                    )
                else:
                    st.warning(
                        f"{len(split):,} agrupaciones "
                        "requieren revisión."
                    )

                    st.dataframe(
                        split,
                        use_container_width=True,
                        hide_index=True
                    )

            with tabs[4]:

                if "monto" in df.columns:
                    numeric = pd.to_numeric(
                        df["monto"],
                        errors="coerce"
                    ).dropna()

                    c1, c2, c3, c4 = st.columns(4)

                    c1.metric(
                        "Registros",
                        len(numeric)
                    )

                    c2.metric(
                        "Total",
                        money(
                            numeric.sum(),
                            company["currency"]
                        )
                    )

                    c3.metric(
                        "Promedio",
                        money(
                            numeric.mean(),
                            company["currency"]
                        )
                    )

                    c4.metric(
                        "Mediana",
                        money(
                            numeric.median(),
                            company["currency"]
                        )
                    )

                    fig = px.histogram(
                        df,
                        x="monto",
                        nbins=40,
                        title="Distribución de montos"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

            workbook = excel_export({
                "Universo": df,
                "Duplicados": exact,
                "Fuzzy": fuzzy,
                "Benford": ben,
                "Fraccionamiento": split_payments(
                    df,
                    threshold
                    if "threshold" in locals()
                    else 100000
                ),
            })

            st.download_button(
                "⬇️ Descargar matriz forense completa",
                data=workbook,
                file_name="BASA_06_FORENSE_MATRIZ.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            doc_id = f"DOC-{uuid.uuid4().hex[:10].upper()}"

            raw = uploaded.getvalue()

            with ENGINE.begin() as conn:
                conn.execute(text("""
                    INSERT INTO documents(
                        id,company_id,filename,mime_type,
                        size_bytes,sha256,module,
                        uploaded_by,uploaded_at,notes
                    )
                    VALUES(
                        :id,:company_id,:filename,:mime_type,
                        :size_bytes,:sha256,:module,
                        :uploaded_by,:uploaded_at,:notes
                    )
                """), {
                    "id": doc_id,
                    "company_id": selected_company,
                    "filename": uploaded.name,
                    "mime_type": uploaded.type,
                    "size_bytes": len(raw),
                    "sha256": sha256_bytes(raw),
                    "module": "BASA_06_Forense",
                    "uploaded_by": USER["username"],
                    "uploaded_at": now_iso(),
                    "notes": "Universo forense procesado",
                })

            log_event(
                "FORENSIC_FILE_PROCESSED",
                "DOCUMENT",
                doc_id,
                f"filas={len(df)}",
                USER["username"],
                selected_company,
            )

        except Exception as exc:
            st.error(
                f"Error durante el análisis forense: {exc}"
            )


# ================================================================
# 17. BASA_03_TODOINTEGRADO
# ================================================================

elif MODULE == "🏛️ BASA_03_todointegrado":

    st.title("🏛️ BASA_03_todointegrado")

    st.markdown("""
    ### Suite integrada

    **BASA_05_Fiscal**
    - 606
    - 607
    - 608
    - validación
    - conciliación
    - TXT de trabajo
    - Excel de auditoría

    **BASA_06_Forense**
    - duplicados
    - fuzzy matching
    - Benford
    - fraccionamiento
    - distribución estadística
    - matriz de riesgo

    **Core Integrado**
    - multiempresa
    - usuarios
    - expedientes
    - SHA-256
    - cadena de eventos
    - casos de auditoría
    - trazabilidad
    """)

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Módulo Fiscal",
        "606 / 607 / 608"
    )

    c2.metric(
        "Módulo Forense",
        "ADA + Riesgo"
    )

    c3.metric(
        "Trazabilidad",
        "SHA-256"
    )

    st.markdown("### Flujo recomendado")

    st.write("""
    1. Cargar documentos y conservar su SHA-256.
    2. Clasificar el expediente como fiscal, financiero o forense.
    3. Procesar 606/607/608.
    4. Ejecutar analítica forense sobre el universo.
    5. Revisar excepciones.
    6. Crear caso de auditoría.
    7. Documentar procedimiento y evidencia.
    8. Exportar matriz.
    9. Revisar profesionalmente antes de presentar resultados.
    """)

    if st.button(
        "🚀 Abrir BASA_05_Fiscal",
        type="primary"
    ):
        st.session_state["_goto"] = "🧾 BASA_05_Fiscal"
        st.rerun()

    if st.button(
        "🔎 Abrir BASA_06_Forense"
    ):
        st.session_state["_goto"] = "🔎 BASA_06_Forense"
        st.rerun()


# ================================================================
# 18. DASHBOARD
# ================================================================

elif MODULE == "📊 Dashboard":

    st.title("📊 Dashboard Ejecutivo")

    with ENGINE.connect() as conn:
        docs = pd.read_sql(
            text("""
                SELECT *
                FROM documents
                WHERE company_id=:company_id
                ORDER BY uploaded_at DESC
            """),
            conn,
            params={"company_id": selected_company},
        )

        cases = pd.read_sql(
            text("""
                SELECT *
                FROM audit_cases
                WHERE company_id=:company_id
                ORDER BY created_at DESC
            """),
            conn,
            params={"company_id": selected_company},
        )

logs = pd.read_sql(
    text("""
        SELECT
            id,event_time,
            username,company_id,
            action,object_type,
            object_id,details,
            event_hash
        FROM event_log
        ORDER BY id DESC
        LIMIT 1000
    """),
    conn,
)

    if not cases.empty:
        cases["risk"] = cases.apply(
            lambda r:
                risk_score(
                    r["probability"],
                    r["impact"]
                ),
            axis=1
        )

        cases["nivel"] = cases["risk"].map(
            risk_level
        )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Expedientes",
        len(docs)
    )

    c2.metric(
        "Casos",
        len(cases)
    )

    c3.metric(
        "Eventos",
        len(logs)
    )

    c4.metric(
        "Riesgos altos/críticos",
        int(
            (cases["risk"] >= 15).sum()
        )
        if not cases.empty
        else 0
    )

    if not cases.empty:

        left, right = st.columns(2)

        with left:
            chart = px.bar(
                cases.groupby(
                    "nivel",
                    as_index=False
                )["amount"].sum(),
                x="nivel",
                y="amount",
                title="Monto por nivel de riesgo"
            )

            st.plotly_chart(
                chart,
                use_container_width=True
            )

        with right:
            st.dataframe(
                cases[
                    [
                        "title",
                        "module",
                        "audit_type",
                        "risk",
                        "nivel",
                        "amount",
                        "status",
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )


# ================================================================
# 19. CADENA DE CUSTODIA
# ================================================================

elif MODULE == "📜 Cadena de Custodia":

    st.title("📜 Cadena de Custodia")

    with ENGINE.connect() as conn:
        logs = pd.read_sql(
            text("""
                SELECT
                    id,event_id,event_time,
                    username,action,
                    object_type,object_id,
                    details,
                    previous_hash,
                    event_hash
                FROM event_log
                WHERE company_id=:company_id
                ORDER BY id DESC
                LIMIT 1000
            """),
            conn,
            params={"company_id": selected_company},
        )

    st.metric(
        "Eventos",
        len(logs)
    )

    if not logs.empty:
        st.dataframe(
            logs,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Descargar registro",
            data=logs.to_csv(
                index=False
            ).encode("utf-8"),
            file_name="BASA_CADENA_CUSTODIA.csv",
            mime="text/csv"
        )

    st.info("""
    SHA-256 proporciona una huella de integridad del contenido registrado.
    No sustituye las reglas de preservación, autenticidad, admisibilidad
    o cadena de custodia jurídica que correspondan al caso.
    """)


# ================================================================
# 20. ADMINISTRACIÓN
# ================================================================

elif MODULE == "⚙️ Administración":

    st.title("⚙️ Administración")

    if USER["role"] != "Administrador Global":
        st.error(
            "Solo el Administrador Global puede administrar el sistema."
        )
        st.stop()

    t1, t2, t3 = st.tabs([
        "🏢 Empresas",
        "👤 Usuarios",
        "🧾 Registro"
    ])

    with t1:

        st.dataframe(
            companies,
            use_container_width=True,
            hide_index=True
        )

        with st.form("new_company"):
            st.subheader(
                "Registrar empresa"
            )

            rnc = st.text_input("RNC")
            name = st.text_input(
                "Nombre legal"
            )
            currency = st.selectbox(
                "Moneda",
                ["RD$", "USD", "EUR"]
            )

            if st.form_submit_button(
                "Crear empresa"
            ):
                if not rnc.strip() or not name.strip():
                    st.error(
                        "RNC y nombre son obligatorios."
                    )
                else:
                    cid = (
                        "EMP-"
                        + uuid.uuid4()
                        .hex[:8]
                        .upper()
                    )

                    with ENGINE.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO companies(
                                id,rnc,name,currency,created_at
                            )
                            VALUES(
                                :id,:rnc,:name,
                                :currency,:created_at
                            )
                        """), {
                            "id": cid,
                            "rnc": normalize_rnc(rnc),
                            "name": name.strip(),
                            "currency": currency,
                            "created_at": now_iso(),
                        })

                    log_event(
                        "CREATE_COMPANY",
                        "COMPANY",
                        cid,
                        name,
                        USER["username"],
                        cid,
                    )

                    st.success(
                        f"Empresa creada: {cid}"
                    )

                    st.rerun()

    with t2:

        with ENGINE.connect() as conn:
            users = pd.read_sql(
                text("""
                    SELECT
                        username,
                        role,
                        company_id,
                        full_name,
                        active,
                        created_at
                    FROM users
                    ORDER BY created_at DESC
                """),
                conn,
            )

        st.dataframe(
            users,
            use_container_width=True,
            hide_index=True
        )

        with st.form("new_user"):

            st.subheader(
                "Crear usuario"
            )

            username = st.text_input(
                "Usuario / correo"
            )

            full_name = st.text_input(
                "Nombre completo"
            )

            password = st.text_input(
                "Contraseña",
                type="password"
            )

            role = st.selectbox(
                "Rol",
                [
                    "Auditor",
                    "Supervisor",
                    "Administrador Global",
                ]
            )

            company_user = st.selectbox(
                "Empresa",
                ["Todas"]
                + companies["id"].tolist(),
                format_func=lambda x:
                    "Todas"
                    if x == "Todas"
                    else companies.loc[
                        companies.id == x,
                        "name"
                    ].iloc[0]
            )

            if st.form_submit_button(
                "Crear usuario"
            ):

                if (
                    not username.strip()
                    or not full_name.strip()
                    or len(password) < 10
                ):
                    st.error(
                        "Complete los datos y use "
                        "una contraseña de mínimo "
                        "10 caracteres."
                    )
                else:
                    uid = str(uuid.uuid4())

                    with ENGINE.begin() as conn:

                        exists = conn.execute(
                            text("""
                                SELECT COUNT(*)
                                FROM users
                                WHERE username=:username
                            """),
                            {
                                "username":
                                    username.strip()
                            }
                        ).scalar_one()

                        if exists:
                            st.error(
                                "El usuario ya existe."
                            )
                        else:
                            conn.execute(text("""
                                INSERT INTO users(
                                    id,username,password_hash,
                                    role,company_id,
                                    full_name,created_at
                                )
                                VALUES(
                                    :id,:username,
                                    :password_hash,
                                    :role,:company_id,
                                    :full_name,
                                    :created_at
                                )
                            """), {
                                "id": uid,
                                "username":
                                    username.strip(),
                                "password_hash":
                                    password_hash(
                                        password
                                    ),
                                "role": role,
                                "company_id":
                                    None
                                    if company_user == "Todas"
                                    else company_user,
                                "full_name":
                                    full_name.strip(),
                                "created_at":
                                    now_iso(),
                            })

                            log_event(
                                "CREATE_USER",
                                "USER",
                                uid,
                                username,
                                USER["username"],
                                selected_company,
                            )

                            st.success(
                                "Usuario creado."
                            )

    with t3:

        with ENGINE.connect() as conn:
            logs = pd.read_sql(
                text("""
                    SELECT
                        id,event_time,
                        username,company_id,
                        action,object_type,
                        object_id,details,
                        event_hash
                    FROM event_log
                    ORDER BY id DESC
                    LIMIT 1000
                """),
                conn,
            )

        st.dataframe(
            logs,
            use_container_width=True,
            hide_index=True
        )


# ================================================================
# 21. PIE
# ================================================================

st.markdown("---")

st.caption(
    f"© 2026 Baldera Santos & Asociados SRL | "
    f"{APP_NAME} v{VERSION} | "
    "Fiscal + Forense + Integrado"
)
