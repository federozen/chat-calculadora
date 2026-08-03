# Brief: el mejor sistema posible para cálculos y contenidos del fútbol argentino (LPF 2026)

## 0. Objetivo del encargo
Rediseñá y llevá al máximo una herramienta para una **redacción deportiva**. Tiene que servir para dos cosas:
1. **Cálculos rápidos y correctos** sobre la situación de cada equipo (qué necesita, qué puede pasar, qué le conviene) para cada objetivo.
2. **Generar contenido publicable** para las **previas** de cada fecha y para el **análisis posterior** a los resultados.

Tenés **libertad para proponer la mejor arquitectura e interfaz** (chat, tablero, formularios, o una combinación): lo que mejor cumpla el objetivo. Buscá las mejores opciones para mejorar **a la vez en tres frentes**: **(1) la lógica de las cuentas, (2) la narrativa/contenido y (3) el sistema e interfaz.**

Trabajá **iterando**: primero auditá y dejá impecables las cuentas (validándolas), después la narrativa, después el sistema/interfaz y los gráficos. No rompas lo que ya funciona de un saque; validá cada paso.

## 1. Casos de uso (para qué se usa)
- **Previa de la fecha:** qué se juega cada equipo, qué necesita para cada objetivo, qué le conviene que pase en otras canchas, escenarios y variantes.
- **Post-resultados:** cargar lo que pasó y recalcular al instante — qué cambió, quién quedó mejor o peor, las cuentas nuevas.
- **Notas por objetivo:** playoffs, Libertadores, Sudamericana, no descender — para cada equipo, con piso, techo, todas las posibilidades, variantes, árboles y conveniencias.

El resultado tiene que ser **contenido claro y listo para publicar**, en **español rioplatense**.

## 2. Estado actual y libertad de rediseño
Hoy existe una app **Streamlit** de una sola pieza (`calculadora_futbol_argentino.py`, ~6200 líneas) con una **interfaz de chat por palabras clave** (no depende de ningún LLM: hay un router de intents). Funciona, pero:
- las **explicaciones no son del todo claras**,
- **algunas cuentas no convencen**,
- la **interfaz y el formato de salida** se pueden mejorar mucho.

**Podés rediseñar lo que haga falta** (arquitectura, interfaz, formato de salida, incluso modularizar el código). Mantené algo **simple de desplegar y correr**: hoy se despliega en **Streamlit Community Cloud (gratuito)**; si seguís en Streamlit, mejor; si proponés otra cosa, que sea igual de liviana y directa. Evitá dependencias pesadas o servicios pagos.

## 3. Principio innegociable (calidad de las cuentas)
Todas las cuentas y todos los textos con números los produce **código determinístico**, no un LLM (si usás un LLM, que solo interprete la pregunta o pula la redacción, nunca que calcule ni invente cifras). Separá **siempre** lo **EXACTO** (ya clasificó / quedó afuera / puntos que faltan para asegurar / mejor y peor puesto de una fecha) de lo **ESTIMADO** (probabilidades por simulación) y **rotulá** lo estimado como tal. **Auditá y validá cada cálculo** (idealmente con tests y fuerza bruta) y **documentá los supuestos y las aproximaciones**. El usuario no quedó convencido de algunas cuentas: revisalas a fondo.

## 4. Reglas del torneo (LPF 2026) — CONFIRMALAS con el reglamento vigente
> Estos números cambian por temporada. **Verificalos** antes de calcular; no los des por sentados.
- **Formato:** dos zonas (A y B) de **15 equipos**. A los **playoffs (octavos)** entran los **8 primeros de cada zona**.
- **Tabla Anual** (Apertura + Clausura): define plazas a copas y **un** descenso.
- **Copas 2027:** se usa la **tabla anual SIN CAMPEONES** (la "reducida"). Entran **N a Libertadores** (según los cupos que queden libres) y los **6 siguientes a Sudamericana**. Los **campeones** (Apertura, Clausura, Copa Argentina) ya tienen plaza, **salen de la tabla y liberan cupo**. **Libertadores es más importante que Sudamericana** → mostralas **separadas**.
- **Descenso:** bajan **2** — **1 por la Tabla Anual** (el último) y **1 por Promedios** (el peor promedio). Regla de reasignación: **si el mismo equipo es último en las dos, desciende por promedios y el 2º peor de la anual toma el descenso por anual.** Los recién ascendidos pueden **no tener promedio** (no bajan por esa vía su primer año).

## 5. Qué hace hoy (funciones actuales, para conservar y mejorar)
- **Playoffs:** qué necesita un equipo · tabla · octavos (cruces si terminara hoy) · relato de la zona · chances (probabilidades) · proyección · quién clasifica · está eliminado · máximos.
- **Descenso:** panorama · se salva un equipo (exacto por promedio y anual) · promedios · chances de descenso · qué le conviene para salvarse.
- **Copas:** panorama · qué necesita para Libertadores/Sudamericana · chances por cada copa (separadas) · qué le conviene por cada copa · tabla anual.
- **Previa y escenarios por equipo:** previa por equipo (mejor y peor puesto tras la fecha, por objetivo) · qué le conviene (la "otra cancha", incluidos cruces futuros entre rivales) · árbol de decisión + partido bisagra · previa de la fecha (todos los partidos con probabilidad).
- **Por equipo:** ficha · forma / racha / local-visitante · comparar · calendario · rivales que restan.
- **Datos:** carga offline completa en un clic · actualización en vivo desde ESPN (tablas + resultados) · carga de resultados partido a partido · chequeo de si los datos están al día · un "¿por qué?" que desarma cada cuenta.

## 6. Cómo están hechas las cuentas hoy (auditá cada una)
- **Techo (pmax):** `pts + 3 × partidos_restantes`.
- **Piso seguro** ("qué necesita para asegurar"): función `_linea_garantia`. Busca (búsqueda binaria) el **máximo puntaje que el k-ésimo rival puede alcanzar en el peor caso**, descontando los **mano a mano** (cuando dos rivales se enfrentan, de ese partido salen 3 puntos al par, no 6). Es una **cota segura** (nunca dice "entrás" si no). La usan por igual **playoffs, descenso y copas** (cambia `base` y `k`). Estaba validada con un test Monte-Carlo de seguridad; **re-auditala igual**.
- **Opciones del piso:** piso **condicional** si ganás tus cruces directos (mano a mano) y lista de **rivales a superar** con su techo.
- **Chances (probabilidades):** **Monte Carlo**. Modela cada partido con **fuerza por puntos/partido + forma reciente**, **localía** y **probabilidad de empate**, sobre el **fixture real**. Por objetivo: playoffs (posición en la zona, top 8), Libertadores/Sudamericana (posición en la reducida), descenso (último de promedios ∪ último de anual, con reasignación).
  - **Invariante de validación:** la suma de las probabilidades de un objetivo debe dar la **cantidad de cupos** (Libertadores = n_lib, Sudamericana = 6, descenso = 2, playoffs = 16). Conservá este chequeo.
- **Previa por equipo (mejor/peor puesto tras la fecha):** cálculo **exacto y separable** (cada equipo juega una vez por fecha). Va **por puntos, desempatando por la diferencia de gol de hoy**. ⚠️ **Aproximación conocida:** no recalcula la DG que cambiaría con el resultado del propio partido, así que en un empate en puntos muy justo puede variar un puesto. **Mejorá o documentá esto.**
- **"Qué le conviene" (la otra cancha):** fuerza cada resultado de los partidos de los rivales y mide el **impacto en la probabilidad del objetivo** (con números aleatorios comunes para comparar limpio). Incluye **cruces futuros entre rivales**. Marca "da igual" cuando el impacto entra en el ruido.
- **Árbol:** cómo cambian las chances según gane/empate/pierda el próximo, + **partido bisagra**.
- **Forma / rachas / local-visitante:** desde los resultados partido a partido.

## 7. Foco del rediseño (los tres frentes)
**(1) Lógica de las cuentas.** Auditá y corregí todo; validá con fuerza bruta o tests; documentá supuestos. Casos ya detectados/corregidos (verificá que sigan bien y buscá otros):
- El "por qué" de copas ahora aclara los cruces entre los de arriba aun cuando no bajan la línea.
- La previa daba "2º en la anual" para River por asumir que ganaba los desempates; se corrigió a desempatar por **DG real** (dio 3º).
- Consignar a los **campeones que ya tienen plaza** (ej. Belgrano) y por qué salen de la tabla.

**(2) Narrativa / contenido.** Reescribí **todos** los textos para que se entiendan sin jerga y sirvan para una nota. En cada respuesta, explicá con claridad: el **piso** (qué asegura y por qué), el **techo**, **todas las posibilidades** del escenario, las **variantes** (qué pasa con cada resultado), el **árbol**, **qué le conviene** según el objetivo y la **previa de la fecha**. Que cada respuesta cierre con un "por qué" verificable. Pensá formatos listos para publicar (titular + bajada + cuerpo, o bullets, según convenga).

**(3) Sistema e interfaz.** Diseñá la mejor experiencia para una redacción: **carga rápida de resultados** y recálculo instantáneo, **informes por equipo y objetivo en pocos clics**, modos **previa** y **post-resultado**, y las gráficas del punto siguiente. La interfaz puede seguir siendo un chat, o pasar a un tablero/formularios, o combinar ambos — lo que sea más rápido y claro para trabajar contra el cierre.

## 8. Narrativa gráfica (didáctica, además del texto)
Mostrá los datos de forma visual para ilustrar una nota. Usá lo que mejor sirva en cada caso:
- **Cuadros de doble entrada:** rival × resultado → tu situación; equipo × objetivo → piso / techo / chance; fecha × equipo → puntos proyectados.
- **Tablas** de posiciones con piso, techo, chance y estado (adentro / en pelea / afuera).
- **Árboles** (de decisión o de escenarios): con `st.graphviz_chart` (DOT), que **no requiere instalar nada extra**.
- **Barras de probabilidad**, **líneas de proyección**, **mapas de calor** de "qué me conviene".
- Todo debe renderizar en el entorno liviano elegido: `st.dataframe`, `st.graphviz_chart`, `st.plotly_chart` (agregá `plotly` al requirements si lo usás), `st.altair_chart` (viene con Streamlit), `matplotlib`, o HTML/SVG.

## 9. Entregable esperado
**Informes completos y explicativos por equipo y objetivo**, listos para copiar a una nota: **narrativa textual clara + apoyo gráfico**, tanto en modo **previa** como **post-resultado**. La herramienta tiene que ser **rápida de usar** en una redacción.

## 10. Datos que ya vienen en el código
- **Fixture completo** de las 16 fechas (`LPF_FIXTURE_2026`) + parser.
- **Tablas** Zona A / Zona B, **Tabla Anual**, **Promedios** (constantes, **previo a la fecha 2** del Clausura 2026).
- **Resultados de la fecha 1** (`RESULTADOS_LPF_2026`).
- **`canon_club()`**: normaliza los **30** nombres y resuelve homónimos (Gimnasia La Plata vs Gimnasia de Mendoza; Estudiantes de La Plata vs Estudiantes de Río Cuarto; Independiente vs Independiente Rivadavia; Central Córdoba vs Rosario Central; etc.). **Usalo siempre** con cualquier dato nuevo.
- Cargadores: carga offline por constantes y actualización desde ESPN (tablas + resultados). La Tabla Anual no se actualiza por ESPN (ESPN da solo el Clausura); mejorarlo es deseable.

## 11. Checklist de calidad (antes de entregar)
- [ ] Cada cuenta validada (fuerza bruta o test) y con supuestos documentados.
- [ ] Exacto vs estimado, siempre separado y rotulado.
- [ ] Reglas del torneo confirmadas con el reglamento vigente.
- [ ] `canon_club` aplicado a todo dato nuevo.
- [ ] Explicaciones claras para un lector no técnico y listas para publicar.
- [ ] Gráficos que aportan (no decorativos) y que renderizan en el entorno elegido.
- [ ] Interfaz rápida para una redacción (previa y post-resultado).
- [ ] Corre de arriba a abajo sin romper funciones previas; código que compila.
- [ ] Español rioplatense.

## 12. Archivos adjuntos
- `calculadora_futbol_argentino.py` — la app actual completa (auditá y rediseñá sobre esto).
- `requirements.txt` — dependencias base (agregá lo que uses para gráficos, p. ej. `plotly`).
