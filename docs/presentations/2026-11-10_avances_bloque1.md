# Presentación de avances · AITCHazard (10 de noviembre de 2026)

Material base para la reunión con la tutora. Cada diapositiva tiene un título que dice la
conclusión, el contenido, la figura (si la hay) y notas para quien presenta. Las figuras
están en `docs/results/figures/emily_2005/`. Los detalles técnicos están en
`docs/results/2026-11-08_block1_benchmark_emily.md` y `docs/block1-aifs.md`.

---

## 1. AITCHazard: el peligro por ciclones tropicales de ITCHI, ahora pronosticado

- Doctorado: peligrosidad de los ciclones tropicales (CT) en México.
- **ITCHI** mide el peligro observado: lluvia de MSWEP y viento paramétrico a partir de las trayectorias observadas.
- **AITCHazard** produce los mismos insumos a partir de pronósticos de IA (AIFS) para
  calcular ITCHI con 0 a 72 h de anticipación.

*Notas:* AITCHazard no es un índice nuevo. Es la capa de pronóstico de ITCHI (fase F5 del
plan v0.3: ¿con cuánta anticipación se detecta cada nivel?).

---

## 2. El flujo tiene cuatro bloques y un módulo de seguimiento

Figura: diagrama de `docs/framework.md`.

| Bloque | Qué hace | Estado |
|---|---|---|
| 1 | Pronósticos AIFS 1.1 con condiciones iniciales de ERA5, 2000–2025 | Validado; falta la campaña |
| 2 | Corrección y reducción de escala de la lluvia (SwAIther-Precip → MSWEP V3.16) | Diseño decidido |
| Seguimiento | Centro, trayectoria, Vmax y Pmin (TempestExtremes, protocolo TCBench) | Diseño decidido |
| 3 | Peligro por viento con el esquema de ITCHI (W06, 2 m/s, Saffir-Simpson) | Diseño decidido; falta corregir la intensidad |
| 4 | ITCHI por anticipación frente a ITCHI observado | Diseño decidido |

---

## 3. Bloque 1: 22 256 pronósticos de 72 h sobre México

| Elemento | Decisión |
|---|---|
| Modelo | AIFS Single v1.1 (ECMWF) |
| Condiciones iniciales | ERA5 (t−6 h y t0) |
| Periodo | Mayo–noviembre, 2000–2025 |
| Ciclos | 00, 06, 12 y 18 UTC |
| Horizonte | 0–72 h cada 6 h |
| Dominios | Regional 5–35°N, 130–60°W (lluvia); extendido −5–45°N, 140–50°W (seguimiento) |

*Notas:* toda la temporada, no solo los días con ciclón. Así hay datos para entrenar la
corrección de la lluvia y una climatología del modelo por anticipación.

---

## 4. El modelo 1.1 no cargaba con las librerías actuales; quedó resuelto

- El checkpoint guarda el modelo completo con referencias a las librerías del entrenamiento.
- Con anemoi-models 0.9.3 falla (falta un módulo de `torch_geometric`).
- Las versiones del entrenamiento están en los metadatos del checkpoint: torch_geometric
  2.4.0 y anemoi-models 0.4.2 (≈0.5.0).
- Solución: el contenedor actual más una capa con esas versiones. El modelo carga (253 M de parámetros).

*Notas:* queda pendiente fijar este entorno en una receta de contenedor reproducible.

---

## 5. Un pronóstico de 72 h tarda 12.6 s; la campaña completa, unas 100 horas de GPU

| | Primera versión | Optimizada |
|---|---|---|
| Tiempo por pronóstico | 52 s | **12.6 s** |
| Uso de la GPU | 15 % | 44 % |
| Campaña (con margen) | 420 h-GPU | **~100 h-GPU** |
| Memoria GPU | 21 de 40 GB | 21 de 40 GB |
| Almacenamiento | 0.5–0.8 TB de salida + 4.4 TB de ERA5 | igual |

*Notas:* el cuello de botella era la interpolación de la malla del modelo a 0.25°. Ahora
se interpola solo la región de interés y todas las variables a la vez, con los mismos pesos
(diferencia 0.0 frente al método original). Con este costo ya no hace falta bajar a 2
ciclos diarios.

---

## 6. Tres verificaciones resueltas

- **t0:** el modelo no entrega el tiempo inicial; se toma de ERA5 con la misma interpolación.
- **Variables:** lluvia total, lluvia convectiva y nubosidad están en la salida.
- **Lluvia:** AIFS entrega la lluvia de cada intervalo de 6 h, no la acumulada desde el
  inicio. Coincide con la ventana (T−6 h, T] de MSWEP 6 h, la que ya usa ITCHI.

---

## 7. Emily 2005: la trayectoria se pronostica bien

Figura: `emily_trayectorias.png`.

- Cuatro inicios del 17 de julio de 2005 (00, 06, 12 y 18 UTC).
- Las trayectorias siguen a IBTrACS del Caribe a Yucatán y a Tamaulipas.
- Ligero desvío al norte sobre el Golfo en los inicios de 00 y 06 UTC.

*Notas:* el centro se siguió con un método simple (mínimo de presión). La evaluación formal
será con TempestExtremes y el protocolo TCBench.

---

## 8. Emily 2005: la intensidad queda muy por debajo, y la diferencia ya está en t0

Figura: `emily_intensidad.png`.

| | AIFS / ERA5 | IBTrACS |
|---|---|---|
| Presión mínima | 971–993 hPa | 929–984 hPa |
| Viento máximo | 22–31 m s⁻¹ | 33–72 m s⁻¹ |

- En t0, ERA5 ya tiene a Emily en ~990 hPa contra 929 hPa observados.
- AIFS reproduce la forma (debilitamiento sobre Yucatán y reintensificación en el Golfo),
  pero con mucha menos amplitud.

*Notas:* el viento de AIFS es el máximo en una malla de 0.25°, y el de IBTrACS es el viento
sostenido de 1 minuto: no son equivalentes. Por esto el bloque 3 necesita una corrección de
intensidad antes de aplicar el perfil de viento.

---

## 9. Emily 2005: así se ven los campos sobre México

Figura: `emily_2005071712_campos.png` (inicio 17 de julio, 12 UTC).

- Fila superior: presión y viento a 10 m a +0, 24, 48 y 72 h.
- Fila inferior: lluvia en 6 h a +6, 24, 48 y 72 h. Núcleo compacto, con máximos de ~50–75 mm.
- Falta comparar la lluvia con MSWEP: es la tarea del bloque 2.

---

## 10. Lo que significa para los bloques 2 a 4

- **Lluvia (bloque 2):** objetivo MSWEP V3.16 de 6 h, el mismo producto de ITCHI;
  altitud del Continuo de Elevaciones Mexicano de INEGI (15 m).
- **Viento (bloque 3):** perfil de Willoughby et al. (2006) por cuadrante, hasta el radio
  donde el viento cae a 2 m/s, normalizado a categorías Saffir-Simpson, como en ITCHI.
  Antes hay que corregir la intensidad.
- **Índice (bloque 4):** la lluvia antecedente de 72 h combina MSWEP observado antes de t0
  y el pronóstico después de t0.
- **Cambio de distribución:** los pronósticos con ERA5 heredan vórtices débiles. En
  operación, con análisis de mayor resolución, el vórtice inicial será más intenso.

---

## 11. Decisiones para discutir

Con la tutora:
1. Corrección de la lluvia pronosticada: SwAIther frente a la climatología observada, AIFS
   frente a su propia climatología por anticipación (ITCHI v0.3, P3), o ambas.
2. Forma exacta de la normalización Saffir-Simpson y corte de la cola de viento.
3. Lluvia antecedente: mezcla de MSWEP observado y pronóstico.

Con Tom y Milton (16 o 23 de noviembre):
1. ¿Correr primero 2023–2025 (fuera de la muestra de entrenamiento de AIFS)?
2. Variables extra para el viento (cizalladura) antes de la campaña.
3. Corrección de intensidad y radios de viento a partir de AIFS.
4. Parámetros exactos del seguimiento de TCBench.

---

## 12. Próximos pasos

| Paso | Qué | Cuándo |
|---|---|---|
| 1 | Runner de producción por mes y descarga mensual de ERA5 | Semana del 9 de noviembre |
| 2 | Piloto de un mes (mayo de 2023) y receta del contenedor | Semana del 9 de noviembre |
| 3 | Prueba de TempestExtremes sobre las salidas | Antes de la campaña |
| 4 | Reunión con Tom y Milton: decisiones de la campaña | 16 o 23 de noviembre |
| 5 | Campaña 2023–2025 y después 2000–2022 | Después de la reunión |
| 6 | MSWEP 6 h y el DEM de INEGI en Curnagl; conversor para SwAIther | En paralelo |
