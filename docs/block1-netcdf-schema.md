# BLOCK 1 Netcdf OUTPUT schema

SwAIther-Precip usa, para cada horizonte, 11 canales: precipitación total y convectiva (en mm/6 h tras el preprocesamiento), nubosidad total, viento a 10 m (u y v), humedad específica, temperatura y geopotencial, cada uno en 500 y 850 hPa. A eso se suma la altitud como canal estático, que en tu caso debe salir de un DEM de México sobre la malla objetivo.

TempestExtremes, con la configuración de referencia para ciclones tropicales en ERA5, busca mínimos de MSL, exige un contorno cerrado en MSL y otro en la diferencia Z(300 hPa) − Z(500 hPa), y reporta la magnitud del viento a 10 m y la altura de superficie ZS. El umbral de espesor está en geopotencial: 58.8 m² s⁻², equivalente a 6 m de altura geopotencial. Por eso `z` debe guardarse en m² s⁻², sin convertir a gpm. En cambio, ZS se usa como altura en metros en el filtro de StitchNodes.

La unión da 13 campos dinámicos más 2 estáticos:

| Campo (nombre anemoi) | Unidades | SwAIther | TempestExtremes |
|---|---|---|---|
| `tp`, `cp` | m por paso de 6 h → mm/6 h | sí | no |
| `tcc` | 0–1 | sí | no |
| `10u`, `10v` | m s⁻¹ | sí | sí |
| `msl` | Pa | no | sí |
| `q_500`, `q_850` | kg kg⁻¹ | sí | no |
| `t_500`, `t_850` | K | sí | no |
| `z_500` | m² s⁻² | sí | sí |
| `z_850` | m² s⁻² | sí | no |
| `z_300` | m² s⁻² | no | sí |
| `zs = z_sfc/g`, `lsm` (estáticos, una sola vez) | m, 0–1 | altitud en malla fina | sí |

Para el bloque 3 conviene decidir ahora si agregas `100u`/`100v`, que AIFS v1 produce, y `u`/`v` en 200 y 850 hPa para cizalladura. Añadirlos después implica volver a correr toda la campaña.

