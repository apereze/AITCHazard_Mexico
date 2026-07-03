#!/bin/env python3
# -*- coding: utf-8 -*-

import datetime as dt
from collections import defaultdict
from typing import Iterable, Mapping, Callable

import numpy as np

import earthkit.data as ekd
import earthkit.regrid as ekr

def open_data_transformation(values: np.ndarray):
    if values.shape != (721, 1440):
        raise ValueError(
            "Se esperaba (721, 1440), pero se recibió "
            f"{values.shape} para {field.metadata('param')}."
        )

    values_transformed = np.roll(
        values,
        -(values.shape[1] // 2),
        axis=1,
    )

    values_transformed = ekr.interpolate(
        values_transformed,
        {"grid": (0.25, 0.25)},
        {"grid": "N320"},
    )

    return values_transformed

def get_data(
    *,
    date: dt.datetime,
    source: str = "ecmwf-open-data",
    server: str = "ecmwf",
    param: str | Iterable[str],
    levelist: Iterable[int] | None = None,
    transformation: Callable = lambda values: values,
    **kwargs,
) -> dict[str, np.ndarray]:
    """
    Recupera campos meteorológicos para los tiempos t-6 h y t0 en grilla N320.

    La función descarga los campos solicitados desde MARS usando ``earthkit``.
    Para cada variable, extrae los valores numéricos, ajusta la disposición
    longitudinal del arreglo y agrupa ambos tiempos en un único arreglo con
    dimensión temporal.

    Parámetros
    ----------
    date : dt.datetime
        Fecha de inicialización del pronóstico, correspondiente al tiempo t0.

    source : str
        Fuente de datos utilizada en la consulta.

    servidor : str
        Servidor para ejecutar la consulta (solo se aplicate para source=ecmwf-open-data).

    param : str | Iterable[str]
        Parámetro o lista de parámetros meteorológicos a recuperar.

    levelist : Iterable[int] | None, optional
        Niveles verticales solicitados. Si se proporciona, el nombre final de
        cada variable incluye el nivel correspondiente.

    **kwargs
        Argumentos adicionales enviados a ``ekd.from_source``.

    Retorna
    -------
    dict[str, np.ndarray]
        Diccionario donde cada clave corresponde al nombre de una variable y
        cada valor es un arreglo con los dos tiempos requeridos por el modelo:
        t-6 h y t0.
    """

    requested_levels = list(levelist) if levelist is not None else []
    collected: defaultdict[str, list[np.ndarray]] = defaultdict(list)

    for valid_date in (date - dt.timedelta(hours=6), date):
        data = ekd.from_source(
            source,
            date=valid_date,
            source=server,
            param=param,
            levelist=requested_levels,
            grid="N320",
            **kwargs,
        )

        for field in data:
            values = field.to_numpy()

            name = field.metadata("param")
            if requested_levels:
                name = f"{name}_{field.metadata('levelist')}"

            values = transformation(values)
            collected[name].append(values)

    return {
        name: np.stack(time_slices)
        for name, time_slices in collected.items()
    }

def assert_fields_present(
    fields: Mapping[str, np.ndarray],
    expected: Iterable[str],
    *,
    group_name: str,
) -> None:
    """
    Verifica que un conjunto de campos contenga todas las variables esperadas.

    Parámetros
    ----------
    fields : Mapping[str, np.ndarray]
        Diccionario con las variables descargadas.

    expected : Iterable[str]
        Nombres de las variables que deben estar presentes.

    group_name : str
        Nombre del grupo de variables usado para identificar el error.

    Raises
    ------
    KeyError
        Se lanza si falta alguna variable esperada.
    """

    missing = set(expected) - set(fields)
    if missing:
        raise KeyError(
            f"Faltan variables en {group_name}: {sorted(missing)}"
        )

def retrieve_raw_initial_conditions(
    *,
    date: dt.datetime,
    source: str,
    transformation: Callable = lambda values: values,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """
    Descarga las condiciones iniciales requeridas por AIFS Single v2.

    Recupera variables de superficie, oleaje, suelo y niveles de presión
    desde la fuente indicada. Después de cada descarga, verifica que las
    variables esperadas estén presentes.

    Parámetros
    ----------
    date : dt.datetime
        Fecha de inicialización del pronóstico.

    source : str
        Fuente de datos utilizada para la descarga, por ejemplo MARS u otra
        fuente compatible con ``get_data``.

    Retorna
    -------
    tuple[dict[str, np.ndarray], dict[str, np.ndarray]]
        Dos diccionarios: el primero contiene los campos meteorológicos
        principales y el segundo contiene los campos de suelo.
    """

    fields: dict[str, np.ndarray] = {}

    surface = get_data(
        date=date,
        source=source,
        transformation=transformation,
        param=PARAM_SFC,
        levtype="sfc",
    )
    assert_fields_present(surface, PARAM_SFC, group_name="superficie")
    fields.update(surface)

    wave = get_data(
        date=date,
        source=source,
        transformation=transformation,
        param=PARAM_WAVE,
        stream="wave",
    )
    assert_fields_present(wave, PARAM_WAVE, group_name="oleaje")
    fields.update(wave)

    soil = get_data(
        date=date,
        source=source,
        transformation=transformation,
        param=PARAM_SOIL,
        levelist=SOIL_LEVELS,
    )
    expected_soil = [
        f"{parameter}_{level}"
        for parameter in PARAM_SOIL
        for level in SOIL_LEVELS
    ]
    assert_fields_present(soil, expected_soil, group_name="suelo")

    pressure = get_data(
        date=date,
        source=source,
        transformation=transformation,
        param=PARAM_PL,
        levelist=LEVELS,
    )
    expected_pressure = [
        f"{parameter}_{level}"
        for parameter in PARAM_PL
        for level in LEVELS
    ]
    assert_fields_present(
        pressure,
        expected_pressure,
        group_name="niveles de presión",
    )
    fields.update(pressure)

    return fields, soil

def parse_utc_datetime(value: str) -> dt.datetime:
    """
    Convierte una fecha en texto a un objeto ``datetime`` en UTC sin zona horaria.

    Acepta cadenas en formato ISO, incluyendo fechas terminadas en ``Z``.
    Si la fecha incluye zona horaria, se convierte a UTC. Finalmente, la fecha
    se ajusta al inicio de la hora, eliminando minutos, segundos y microsegundos.

    Parámetros
    ----------
    value : str
        Fecha en formato ISO.

    Retorna
    -------
    dt.datetime
        Fecha normalizada en UTC, sin información explícita de zona horaria.
    """

    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed.replace(minute=0, second=0, microsecond=0)


if __name__ == '__main__':
    PARAM_SFC = [
        "10u", "10v", "2d", "2t", "msl", "skt", "sp",
        "tcw", "lsm", "z", "slor", "sdor", "sd",
    ]
    
    PARAM_SOIL = ["vsw", "sot"]
    
    PARAM_WAVE = [
        "wmb", "h1012", "h1214", "h1417", "h1721",
        "h2125", "h2530", "mwd", "cdww", "mwp", "swh",
    ]
    
    PARAM_PL = ["gh", "t", "u", "v", "q"]
    
    LEVELS = [
        1000, 925, 850, 700, 600, 500, 400,
        300, 250, 200, 150, 100, 50, 10,
    ]
    
    SOIL_LEVELS = [1, 2]

    raw_fields, raw_soil = retrieve_raw_initial_conditions(
        date=parse_utc_datetime("2026-06-17T00:00:00Z"),
        source="ecmwf-open-data",
        #transformation=open_data_transformation,
    )
