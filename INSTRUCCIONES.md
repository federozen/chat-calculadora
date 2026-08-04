# Cómo instalar la versión 3.7.2

## En cada repositorio

### Reemplazar en la raíz

- `calculadora_futbol_argentino.py`
- `lpf_data_quality.py`

### Agregar en la raíz

- `lpf_fixture_sources.py`

### Agregar dentro de `data`

- `data/lpf_fixture_last_valid.json`

### Verificar `requirements.txt`

Debe contener, como mínimo:

```text
requests>=2.31
lxml>=5.0
beautifulsoup4>=4.12
html5lib>=1.1
```

El paquete incluye un `requirements.txt` completo. Si el repositorio ya tiene esas dependencias, no es obligatorio reemplazarlo.

## En GitHub

Para crear el archivo dentro de la carpeta, usar **Add file → Create new file** y escribir:

```text
data/lpf_fixture_last_valid.json
```

O subir la carpeta `data` incluida en el ZIP.

Después del commit, esperar el redeploy. Si Streamlit no reinicia, usar **Manage app → Reboot app**.

## Primera prueba

1. Presionar **Actualizar a hoy (automático)**.
2. Revisar el texto `Partidos y programación:`.
3. Debe indicar ESPN o FutbolArgentino.com.
4. Abrir **Datos y auditoría**: `Sin confirmar` debería quedar en 0.
5. Consultar la previa de un club con un partido postergado. Debe elegir el próximo encuentro por fecha y hora real.

El JSON comienza vacío y se completa automáticamente después de la primera carga válida. Si el hosting no permite escribir en disco, la aplicación conserva el respaldo durante la sesión y muestra una advertencia.
