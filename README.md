# BASA_03_todointegrado

Aplicación Streamlit única que integra:

- BASA_05_Fiscal
- BASA_06_Forense
- BASA_03_todointegrado

## Despliegue

Archivo principal:

`app.py`

En Streamlit Community Cloud configure el archivo principal como `app.py`.

## requirements.txt

Use el archivo incluido.

## Secrets recomendados

```toml
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "CAMBIAR_POR_UNA_CLAVE_LARGA"
DEFAULT_COMPANY = "Baldera Santos & Asociados SRL"
DEFAULT_RNC = "133378711"
DATABASE_URL = "postgresql+psycopg://USUARIO:CLAVE@HOST:5432/BASE"
```

Si no se configura DATABASE_URL, la aplicación utiliza SQLite para pruebas.

## Módulo fiscal

Incluye procesamiento de trabajo para:
- 606
- 607
- 608
- validación
- conciliación interna
- TXT de trabajo
- Excel de auditoría
- SHA-256

## Módulo forense

Incluye:
- duplicados exactos
- coincidencias fuzzy
- Benford
- posibles pagos fraccionados
- distribución de montos
- matriz de riesgo

## Integrado

Incluye:
- dashboard
- empresas
- usuarios
- expedientes
- cadena de eventos
- trazabilidad
- exportación

## Importante

El TXT generado es un archivo de trabajo y debe validarse contra la estructura oficial de DGII correspondiente al período antes de remitirlo. Las conclusiones de auditoría, fraude o legalidad requieren revisión profesional.
