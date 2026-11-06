# BASA SUPERSISTEMA V27 — Streamlit Cloud

## Archivos
- `app.py` — aplicación única.
- `requirements.txt` — dependencias.
- `.streamlit/config.toml` — configuración básica.

## Despliegue
1. Cree un repositorio GitHub.
2. Suba `app.py`, `requirements.txt` y `.streamlit/config.toml`.
3. En Streamlit Community Cloud seleccione `app.py` como archivo principal.
4. Configure Secrets antes de uso empresarial.

## Secrets recomendados

```toml
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "CAMBIAR_POR_UNA_CLAVE_LARGA_Y_UNICA"
DEFAULT_COMPANY = "Baldera Santos & Asociados SRL"
DEFAULT_RNC = "133378711"
DATABASE_URL = "postgresql+psycopg://USUARIO:CLAVE@HOST:5432/BASE"
```

No publique `secrets.toml` en GitHub.

## Modo SQLite
Si no existe `DATABASE_URL`, la app utiliza SQLite local. Es útil para pruebas, pero no debe considerarse almacenamiento empresarial persistente en un entorno cloud efímero.

## Módulos incluidos
- Dashboard ejecutivo.
- Risk Engine 1–25.
- Programas de auditoría.
- ADA / Big Four Analytics.
- Benford.
- Detección de duplicados exactos.
- Detección fuzzy por similitud de proveedor.
- Indicador de posible fraccionamiento.
- Importación CSV/XLSX/XLS/JSON/TXT.
- Registro documental y SHA-256.
- Cadena de eventos hash-encadenada.
- Gestión de empresas.
- Gestión de usuarios.
- Registro de auditoría.
- Exportación Excel.

## Seguridad
La aplicación no contiene una contraseña administrativa fija en el código. Si `ADMIN_PASSWORD` no existe en Secrets, genera una contraseña temporal para la sesión inicial. En producción configure Secrets.

## Nota profesional
El sistema es una herramienta de apoyo para auditoría, control y análisis. Las referencias a NIA/ISA, NIIF/IFRS, NOBACI y Ley 18-24 deben ser revisadas según el encargo, período, entidad y normativa vigente antes de emitir conclusiones profesionales.
