# Cómo instalar la versión 3.6.3

Si el repositorio ya tiene la versión 3.6.2, reemplazá en la raíz estos cuatro archivos:

1. `calculadora_futbol_argentino.py`
2. `lpf_competition_narratives.py`
3. `lpf_competitive_context.py`
4. `lpf_exact.py`

No hace falta modificar:

- `requirements.txt`
- `lpf_display.py`
- `lpf_scenarios.py`
- `data/lpf_last_valid.json`

Después del commit, esperá el redeploy de Streamlit y comprobá:

1. Una tabla de zonas: debe mostrar puntos, PJ y nombres editoriales.
2. El informe de playoffs: debe hablar de puntos totales y frecuencias del modelo.
3. El informe de copas: no debe repetir el bloque general de cruces en Sudamericana.
4. La previa de fecha: debe identificar a los equipos que juegan dos veces y calcular su rango global.

Pruebas ejecutadas:

```bash
python -m py_compile calculadora_futbol_argentino.py lpf_competition_narratives.py lpf_competitive_context.py lpf_exact.py
PYTHONPATH=. pytest -q
```

Resultado esperado: `13 passed`.
