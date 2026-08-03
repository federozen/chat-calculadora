# Calculadora del Fútbol Argentino · LPF 2026 · versión 3.5.4

Aplicación editorial en Python y Streamlit para analizar playoffs por zonas, Tabla Anual, Libertadores, Sudamericana, descenso, promedios y escenarios de una fecha.

La versión 3 prioriza tres objetivos:

1. **Base coherente:** Zonas, Tabla Anual, promedios, fixture y resultados se reconcilian antes de habilitar una cuenta.
2. **Explicación honesta:** distingue hechos exactos, garantías matemáticas, cotas conservadoras y estimaciones.
3. **Uso guiado:** ya no es necesario recordar preguntas del chat; el Explorador permite elegir equipo, objetivo y tarea.

## Corrección 3.5.4

- Mantiene intactos los panoramas individuales de **playoffs, Libertadores y Sudamericana**.
- La previa general deja de publicar rangos exactos pero poco útiles como “1º a 15º”; en esos casos cuenta si el equipo puede entrar, salir o asegurar el top 8.
- El panorama completo de un equipo que juega dos veces se muestra una sola vez para evitar duplicaciones.
- En modo LPF se muestra la regla real: clasifican los 8 primeros de cada zona; se oculta la configuración genérica de “2 directos”.
- “Partidos pendientes” pasa a llamarse **Partidos por jugar**, porque el número incluye el resto del fixture y no sólo postergados.
- Una fecha parcialmente disputada ya no se rotula como una fecha completa faltante o como datos desactualizados.
- Se ampliaron las pruebas de regresión de 6 a 9.

Ver `ACTUALIZACION_3_5_4.md` para el detalle.

## Mejora 3.5.2

- El **Chat libre** pasó a funcionar también como **Chat guiado**.
- Nuevo explorador con selector de equipo, rival para comparar y categorías temáticas.
- Buscador de funciones por palabra: playoffs, Libertadores, Sudamericana, descenso, promedios, previa, distribución y otras.
- Cada opción se ejecuta con un botón y envía automáticamente la consulta al chat.
- Se agregó un índice completo de capacidades y se mantiene el campo de texto para preguntas propias y seguimientos.
- Se incorporaron pruebas de regresión para conservar el catálogo, el buscador y la entrada libre.

Ver `ACTUALIZACION_3_5_2.md` para el detalle.

## Corrección 3.5.1

- Restaurados como botones visibles los seis espacios principales.
- Accesos directos desde el comienzo a todas las herramientas de Escenarios, incluida **Distribución**.
- Las herramientas de Escenarios ya no quedan ocultas dentro de pestañas: se eligen desde un selector visible.
- Se mantienen sin cambios las narrativas de la fecha, Copas y Descenso de la versión 3.5.

Ver `ACTUALIZACION_3_5_1.md` para el detalle.

## Novedades 3.5

- La previa de cada partido puede sumar ahora el impacto en **Libertadores, Sudamericana y descenso**.
- Nuevo selector para activar o desactivar por separado las capas **Copas** y **Descenso**.
- Copas muestra posición en la Anual, lugar en la carrera por los cupos, cupo actual, distancia al corte y rango posible de la ventana.
- La vista individual explica qué cambia si el equipo gana, empata o pierde y distingue zona de Libertadores, Sudamericana o fuera de copas.
- Descenso se limita a los últimos puestos de la Tabla Anual o de los promedios.
- Para los promedios informa el coeficiente exacto posterior a una victoria, empate o derrota.
- La narrativa evita saturar: no incluye equipos con posibilidades matemáticas remotas al comienzo del torneo.

Ver `ACTUALIZACION_3_5.md` para el detalle.

## Novedades 3.4

- Nueva narrativa breve para la previa de una fecha completa.
- Pantallazo inicial de las dos zonas con líder, corte, primero afuera, puntos y diferencia de gol.
- Relato partido por partido con posición actual, situación respecto del top 8 y rango posible al cierre de la ventana.
- Selector **Toda la fecha / Un partido** dentro de la Mesa de redacción.
- En la vista individual se agregan ramas exactas: qué puesto puede ocupar cada equipo si gana, empata o pierde.
- Los postergados aparecen identificados con su fecha original y los equipos que juegan dos veces no reciben un rango simplificado incorrecto.
- Las probabilidades permanecen separadas y rotuladas como estimación.

Ver `ACTUALIZACION_3_4.md` para el detalle.

## Novedades 3.3

- Relatos de zonas con PTS, PJ, DG, GF, igualdad del corte y tabla resumida.
- Panoramas narrativos de Libertadores, Sudamericana y descenso.
- Explicación de cómo los campeones pueden hacer correr los cupos por la Tabla General.
- Seguimiento editable y cotejable de los equipos vivos en Copa Argentina.
- Campo para el reemplazo de ARGENTINA 3 cuando la plaza debe heredarse dentro de Copa Argentina.
- Nuevos accesos guiados para no depender de memorizar preguntas del chat.

Ver `ACTUALIZACION_3_3.md` para el detalle de esa entrega.

## Instalación

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run calculadora_futbol_argentino.py
```

## Espacios de trabajo

- **Panel por equipo:** acceso principal. Elegí equipo, objetivo y pregunta.
- **Escenarios:** herramientas adaptadas de la calculadora del Mundial: gana/empata/pierde, qué pasa si, puesto puntual, mejor/peor caso, distribución y clasificados/eliminados.
- **Mesa de redacción:** informes de previa y post fecha listos para trabajar.
- **Visualizaciones:** vistas por equipo, zona, próxima fecha, otra cancha y Radar final.
- **Chat guiado + libre:** catálogo por categorías, buscador, botones por equipo y consultas abiertas para seguimientos contextuales.
- **Datos y auditoría:** semáforo de calidad, inconsistencias, partidos inferidos y respaldo.

## Flujo recomendado

1. Cargar la foto offline, actualizar desde el proveedor disponible o pegar los datos.
2. Abrir **Datos y auditoría**.
3. Corregir cualquier bloqueo de Zonas, Tabla Anual o Promedios.
4. Trabajar desde el **Panel por equipo**.
5. Abrir **Escenarios** para explorar combinaciones concretas sin recordar comandos.
6. Abrir **Visualizaciones** o **Mesa de redacción** para profundizar y publicar.

## Cuatro referencias distintas

La aplicación evita llamar “piso” a números diferentes:

- **Corte actual:** puntos que tiene hoy el último clasificado.
- **Mínimo todavía posible:** menor puntaje con el que existe una combinación favorable.
- **Garantía matemática:** puntaje con el que entra sin depender de otros resultados ni desempates.
- **Corte estimado:** rango probable de la simulación; nunca se presenta como certeza.

Cuando quedan más de seis partidos, el informe puede usar una **garantía conservadora**. Esa cota es segura, pero podría pedir algún punto de más. Con seis partidos o menos, el Radar habilita un optimizador exacto para construir la escalera de puntajes.

## Datos y fuente de verdad

La prioridad de la versión 3 es:

1. Resultados explícitos para identificar partidos jugados.
2. Foto fija del Apertura más las zonas vigentes para reconstruir la Tabla Anual.
3. Tabla Anual directa solamente si pasa los controles.
4. Inferencia por PJ únicamente como respaldo, siempre rotulada.

Los partidos tienen identidad propia. Un encuentro postergado no se considera jugado solo porque el equipo haya disputado una fecha posterior.

## Exacto, garantía y estimación

- **Exacto:** puntos, PJ, techo, rango por resultados, escenarios factibles y escalera calculada por optimización.
- **Garantía conservadora:** línea segura usada cuando el cálculo exacto completo no se activa.
- **Estimado:** Monte Carlo, dificultad, corte probable e impacto de otras canchas.

El modelo de lenguaje opcional interpreta consultas y redacta. Los números salen siempre de Python.

## Arquitectura

- `calculadora_futbol_argentino.py`: aplicación y compatibilidad con la versión anterior.
- `lpf_models.py`: objetos de dominio, auditoría y resultados estructurados.
- `lpf_data_quality.py`: normalización y reconciliación de Zonas, Anual, Promedios, fixture y resultados.
- `lpf_scenarios.py`: optimización exacta para escalera, rangos y ventanas con postergados.
- `lpf_exact.py`: núcleo determinístico original y cotas seguras.
- `tests/`: pruebas unitarias, fuerza bruta e invariantes.

Más detalle en [ARCHITECTURE.md](ARCHITECTURE.md).

## Verificación

```bash
python -m py_compile calculadora_futbol_argentino.py lpf_models.py lpf_data_quality.py lpf_scenarios.py lpf_exact.py
python -m pytest -q
```

## Documentación

- `AUDITORIA.md`: reglas, alcance de exactitud y controles.
- `ARCHITECTURE.md`: flujo técnico y módulos.
- `GUIA_REDACCION.md`: uso diario y criterio de publicación.
- `GUIA_DATOS.md`: actualización, reconciliación y resolución de conflictos.
- `CHANGELOG.md`: cambios de esta versión.
