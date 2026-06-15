### notebook ya considera

- inventario de variables de Single v2;
- estados \(t-6\) h y \(t_0\);
- transformaciones de oleaje, suelo y geopotencial;
- integridad estructural de `input_state`;
- inferencia opcional de 6 h;
- interpolación N320 → 0.25°;
- recorte regional y NetCDF pequeño.

### Para el repositorio 

1. separar `config`, `data`, `inference` y `postprocess`;
2. usar YAML/TOML y una CLI;
3. incorporar `logging`;
4. añadir pruebas unitarias e integración;
5. implementar reintentos de descarga;
6. escribir estados incrementalmente;
7. fijar el entorno en `pyproject.toml` o `environment.yml`;
8. añadir CI sin inferencia GPU completa;
9. completar metadatos CF;
10. comparar contra una salida de referencia de ECMWF.