"""
config.py — Configuracion central de conexion y parametros de la simulacion.

Aqui se definen: los datos de conexion a la base de datos SQL Server, los
parametros generales de la simulacion (duracion, fecha de inicio, semilla
aleatoria), el escenario editable que controla el comportamiento de la
cadena de suministro, y un conjunto de presets predefinidos (normal, estres,
critico) que permiten reconfigurar el escenario rapidamente.

Author: Ing. G. Alfonso Vargas Solís
Email:  alfonso.vargas.solis@gmail.com
GitHub: alfonsovso
"""

from datetime import datetime

import pyodbc

# ============================= CONEXION =============================
# Datos de conexion a la instancia de SQL Server que almacena la base de
# datos "LabCadenaSuministro". Estos valores se usan para construir la
# cadena de conexion ODBC en get_connection().
# NOTA: las credenciales estan escritas aqui en texto plano unicamente para
# fines de laboratorio/desarrollo local; no se modifica su manejo porque el
# objetivo de este comentario es solo documentar, no alterar la logica.
DB_CONFIG = {
    "driver": "{ODBC Driver 18 for SQL Server}",   # driver ODBC instalado en el sistema
    "server": "localhost,1433",                    # host,puerto del servidor SQL Server
    "database": "LabCadenaSuministro",              # nombre de la base de datos objetivo
    "username": "sa",                               # usuario de conexion
    "password": "password",                    # contrasena del usuario
}


def get_connection():
    """
    Construye la cadena de conexion ODBC a partir de DB_CONFIG y abre una
    conexion a la base de datos SQL Server usando pyodbc.

    La cadena de conexion incluye:
      - DRIVER, SERVER, DATABASE, UID y PWD tomados directamente de
        DB_CONFIG.
      - "Encrypt=no": desactiva el cifrado forzado de la conexion (util en
        entornos locales/de laboratorio sin certificados configurados).
      - "TrustServerCertificate=yes": le indica al cliente que confie en el
        certificado del servidor aunque no pueda validarlo, evitando
        errores de conexion por certificados autofirmados.

    Retorna:
        pyodbc.Connection: objeto de conexion abierto y listo para usarse
        (por ejemplo, para crear cursores y ejecutar consultas SQL).
    """
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


# ======================= PARAMETROS GENERALES =======================
# Parametros globales que rigen la ejecucion temporal de la simulacion.
DIAS_SIMULACION = 2520              # cantidad total de dias que dura la simulacion
FECHA_INICIO = datetime(2019, 1, 1) # fecha calendario en la que arranca la simulacion
SEMILLA = 12345                     # misma semilla => simulacion reproducible
TEMP_AMBIENTE_MAX = 25.0            # techo fisico de temperatura durante una falla

# ============================ ESCENARIO ==============================
# Diccionario central y editable que controla el comportamiento de la
# cadena de suministro simulada. Se organiza por bloques tematicos:
# demanda hospitalaria, reposicion/proveedores, cadena de frio, gestion de
# pedidos y costos operativos. Los valores por defecto aqui representan el
# escenario "normal"/base; pueden sobreescribirse en tiempo de ejecucion
# mediante aplicar_preset() o modificando directamente el diccionario.
ESCENARIO = {
    # --- Demanda hospitalaria ---
    "prob_pedido_diaria": 0.40,        # prob. de que cada hospital pida en un dia
    "max_pedidos_por_dia": 2,          # maximo de pedidos por hospital/dia
    "cantidad_min": 50,                # tamano minimo de un pedido
    "cantidad_max": 300,               # tamano maximo de un pedido
    "multiplicador_demanda": 1.0,      # >1 = mas demanda (empeora la cadena)

    # --- Reposicion / proveedores ---
    "multiplicador_oferta": 0.85,           # <1 = lotes mas chicos (empeora)
    "dias_extra_entre_lotes": 0,            # >0 = reposicion mas lenta (empeora)
    "multiplicador_retraso_proveedor": 1.0, # >1 = proveedores mas irregulares (empeora)

    # --- Cadena de frio ---
    "prob_falla_diaria": 0.0002,       # prob. de falla por camara/dia (empeora si sube)
    "duracion_falla_min": 30,          # minutos
    "duracion_falla_max": 240,         # minutos
    "multiplicador_severidad": 1.0,    # >1 = fallas mas agresivas (empeora)
    "margen_termico": 0.0,             # °C restados a temp_max de cada vacuna (empeora si sube)
    "intervalo_min": 30,               # frecuencia de lecturas del sensor
    "presupuesto_excursion_mult": 1.0, # <1 = calidad mas estricta, mas rechazos (empeora)

    # --- Gestion de pedidos ---
    "max_dias_espera": 12,             # dias extra tras la fecha requerida antes de cancelar

    # --- Costos operativos ---
    "costos_operativos_mult": 1.0,   # >1 = operacion mas cara (empeora el resultado)
}

# Presets listos para usar: normal (base), estres y critico.
# Cada preset es un diccionario parcial que, al aplicarse, sobreescribe
# unicamente las claves indicadas dentro de ESCENARIO, dejando el resto de
# los parametros en su valor actual (ver aplicar_preset()).
PRESETS = {
    # "normal" no sobreescribe nada: representa el escenario base definido
    # arriba en ESCENARIO.
    "normal": {

    },
    # "estres" endurece moderadamente la cadena de suministro: mas demanda,
    # menos oferta, reposicion mas lenta, mas fallas y mayor severidad, y
    # un control de calidad mas estricto (menor presupuesto de excursion).
    "estres": {
        "multiplicador_demanda": 1.5,
        "multiplicador_oferta": 0.8,
        "dias_extra_entre_lotes": 4,
        "prob_falla_diaria": 0.02,
        "multiplicador_severidad": 1.5,
        "max_dias_espera": 8,
        "presupuesto_excursion_mult": 0.7,
    },
    # "critico" lleva el escenario al extremo: demanda muy alta, oferta muy
    # reducida, proveedores mas irregulares y retrasados, fallas frecuentes
    # y de mayor duracion/severidad, menor margen termico permitido y un
    # presupuesto de excursion termica mucho mas restrictivo.
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
    """
    Aplica un preset predefinido de PRESETS sobre el diccionario global
    ESCENARIO, sobreescribiendo (via dict.update) unicamente las claves que
    el preset define y dejando el resto de los parametros sin cambios.

    Parametros:
        nombre (str): clave del preset a aplicar. Debe existir en PRESETS
        (por ejemplo, "normal", "estres" o "critico").

    Excepciones:
        ValueError: si "nombre" no corresponde a ningun preset definido en
        PRESETS, indicando en el mensaje cuales nombres son validos.
    """
    if nombre not in PRESETS:
        raise ValueError(f"Preset desconocido: {nombre!r}. Validos: {', '.join(PRESETS)}")
    ESCENARIO.update(PRESETS[nombre])