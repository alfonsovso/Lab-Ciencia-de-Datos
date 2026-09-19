from datetime import datetime

import pyodbc

DB_CONFIG = {
    "driver": "{ODBC Driver 18 for SQL Server}",
    "server": "localhost,1433",
    "database": "LabCadenaSuministro",
    "username": "sa",
    "password": "password",
}


def get_connection():
    conn_str = (
        f"DRIVER={DB_CONFIG['driver']};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['username']};"
        f"PWD={DB_CONFIG['password']};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)


DIAS_SIMULACION = 2520
FECHA_INICIO = datetime(2019, 1, 1)
SEMILLA = 12345
TEMP_AMBIENTE_MAX = 25.0

ESCENARIO = {
    "prob_pedido_diaria": 0.40,
    "max_pedidos_por_dia": 2,
    "cantidad_min": 50,
    "cantidad_max": 300,
    "multiplicador_demanda": 1.0,

    "multiplicador_oferta": 0.85,
    "dias_extra_entre_lotes": 0,
    "multiplicador_retraso_proveedor": 1.0,

    "prob_falla_diaria": 0.0002,
    "duracion_falla_min": 30,
    "duracion_falla_max": 240,
    "multiplicador_severidad": 1.0,
    "margen_termico": 0.0,
    "intervalo_min": 30,
    "presupuesto_excursion_mult": 1.0,

    "max_dias_espera": 12,

    "costos_operativos_mult": 1.0,
}

PRESETS = {
    "normal": {

    },
    "estres": {
        "multiplicador_demanda": 1.5,
        "multiplicador_oferta": 0.8,
        "dias_extra_entre_lotes": 4,
        "prob_falla_diaria": 0.02,
        "multiplicador_severidad": 1.5,
        "max_dias_espera": 8,
        "presupuesto_excursion_mult": 0.7,
    },
    "critico": {
        "multiplicador_demanda": 2.0,
        "multiplicador_oferta": 0.6,
        "dias_extra_entre_lotes": 8,
        "multiplicador_retraso_proveedor": 1.8,
        "prob_falla_diaria": 0.04,
        "duracion_falla_max": 480,
        "multiplicador_severidad": 2.0,
        "margen_termico": 1.5,
        "max_dias_espera": 5,
        "presupuesto_excursion_mult": 0.4,
    },
}


def aplicar_preset(nombre):
    if nombre not in PRESETS:
        raise ValueError(f"Preset desconocido: {nombre!r}. Validos: {', '.join(PRESETS)}")
    ESCENARIO.update(PRESETS[nombre])