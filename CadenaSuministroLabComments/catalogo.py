"""
catalogo.py — Fuente unica de verdad de la simulacion.

Aqui viven los datos de referencia (vacunas, camaras, proveedores,
hospitales y severidad de fallas). seed_estaticos.py, lotes.py y
frio.py leen de aqui, de modo que nada queda duplicado ni desincronizado.

Author: Ing. G. Alfonso Vargas Solís
Email:  alfonso.vargas.solis@gmail.com
GitHub: alfonsovso
"""

# ---------------------------------------------------------------------------
# UBICACIONES
# ---------------------------------------------------------------------------
# Diccionario que representa cada camara fisica de almacenamiento dentro de
# la cadena de frio. La clave es el nombre de la camara y el valor es otro
# diccionario con:
#   - "tipo": el tipo de sensor instalado en esa camara (para monitoreo de
#     temperatura en tiempo real).
#   - "temp_normal": tupla (temp_min, temp_max) en grados Celsius que define
#     el rango de temperatura considerado "normal" de operacion cuando no
#     existe ninguna falla activa en la camara.
# Estas camaras cubren distintos regimenes termicos: ultracongelacion,
# congelacion, refrigeracion y ambiente controlado (almacen general).
UBICACIONES = {
    "Camara Ultracongelacion A": {"tipo": "Termometro Digital", "temp_normal": (-75.0, -65.0)},
    "Camara Congelacion B":      {"tipo": "Termometro Digital", "temp_normal": (-22.0, -18.0)},
    "Camara Refrigeracion C":    {"tipo": "Termometro Digital", "temp_normal": (3.0, 7.0)},
    "Camara Refrigeracion D":    {"tipo": "Termometro Digital", "temp_normal": (3.0, 7.0)},
    "Almacen General E":         {"tipo": "Termometro Digital", "temp_normal": (18.0, 24.0)},
}

# ---------------------------------------------------------------------------
# VACUNAS
# ---------------------------------------------------------------------------
# Catalogo maestro de vacunas manejadas por el sistema. Cada entrada incluye
# su ficha tecnica basica:
#   - "fabricante": laboratorio productor (debe coincidir con la clave usada
#     en VACUNA_PROVEEDOR y PROVEEDORES).
#   - "temp_min" / "temp_max": rango de temperatura (°C) en el que el
#     producto se considera dentro de especificacion durante todo su
#     almacenamiento y transporte.
#   - "dosis_por_vial": cantidad de dosis que contiene cada vial fisico.
#   - "vida_util_dias": vida util (shelf life) del producto en dias desde su
#     fabricacion/recepcion.
#   - "costo_unitario" / "precio_unitario": costo de adquisicion y precio de
#     venta por dosis (USD), usados para calculos financieros de la
#     simulacion.
VACUNAS = {
    "COVID-19 mRNA": {
        "fabricante": "Pfizer-BioNTech",
        "temp_min": -80.0, "temp_max": -60.0,
        "dosis_por_vial": 6, "vida_util_dias": 180,
        "costo_unitario": 24.00, "precio_unitario": 30.00,
    },
    "COVID-19 Spikevax": {
        "fabricante": "Moderna Inc.",
        "temp_min": -25.0, "temp_max": -15.0,
        "dosis_por_vial": 10, "vida_util_dias": 240,
        "costo_unitario": 30.00, "precio_unitario": 37.00,
    },
    "Influenza Quadrivalent": {
        "fabricante": "Sinovac Biotech",
        "temp_min": 2.0, "temp_max": 8.0,
        "dosis_por_vial": 1, "vida_util_dias": 365,
        "costo_unitario": 12.00, "precio_unitario": 15.00,
    },
    "Sarampion-Rubeola": {
        "fabricante": "AstraZeneca",
        "temp_min": 2.0, "temp_max": 8.0,
        "dosis_por_vial": 10, "vida_util_dias": 540,
        "costo_unitario": 1.20, "precio_unitario": 2.00,
    },
}

# ---------------------------------------------------------------------------
# VACUNA_UBICACION
# ---------------------------------------------------------------------------
# Mapeo directo entre cada vacuna y la camara donde debe almacenarse al
# llegar. La camara asignada es siempre compatible con el rango
# temp_min/temp_max definido para esa vacuna en VACUNAS, garantizando que la
# cadena de frio se respete desde la recepcion del lote.
VACUNA_UBICACION = {
    "COVID-19 mRNA":          "Camara Ultracongelacion A",
    "COVID-19 Spikevax":      "Camara Congelacion B",
    "Influenza Quadrivalent": "Camara Refrigeracion C",
    "Sarampion-Rubeola":      "Camara Refrigeracion D",
}

# ---------------------------------------------------------------------------
# VACUNA_PROVEEDOR
# ---------------------------------------------------------------------------
# Mapeo entre cada vacuna y el proveedor (laboratorio) que la suministra.
# El nombre usado aqui debe coincidir exactamente con el primer elemento de
# la tupla correspondiente en la lista PROVEEDORES, ya que se usa como clave
# de union entre ambas estructuras.
# "cadencia" (ver PROVEEDORES) funciona como el numero promedio de dias
# entre llegadas de lotes de ese proveedor; "variabilidad" es la desviacion
# tipica del posible retraso respecto a esa cadencia.
VACUNA_PROVEEDOR = {
    "COVID-19 mRNA":          "Pfizer-BioNTech",
    "COVID-19 Spikevax":      "Moderna Inc.",
    "Influenza Quadrivalent": "Sinovac Biotech",
    "Sarampion-Rubeola":      "AstraZeneca",
}

# ---------------------------------------------------------------------------
# PROVEEDORES
# ---------------------------------------------------------------------------
# Lista de proveedores/laboratorios que abastecen al sistema. Cada elemento
# es una tupla con la forma:
#   (nombre, contacto, cadencia_dias, variabilidad_dias)
# donde:
#   - nombre: identificador del proveedor (debe coincidir con el usado en
#     VACUNA_PROVEEDOR y con "fabricante" en VACUNAS).
#   - contacto: correo electronico de referencia para pedidos/ventas.
#   - cadencia_dias: numero promedio de dias entre la llegada de un lote y
#     el siguiente para ese proveedor.
#   - variabilidad_dias: desviacion (en dias) que puede tener el retraso de
#     entrega respecto a la cadencia promedio, usada para introducir
#     aleatoriedad realista en la simulacion.
PROVEEDORES = [
    # (nombre, contacto, cadencia_dias, variabilidad_dias)
    ("Pfizer-BioNTech", "ventas@pfizer.example", 14, 3),
    ("Moderna Inc.",    "ventas@moderna.example", 16, 4),
    ("Sinovac Biotech", "ventas@sinovac.example", 16, 3),
    ("AstraZeneca",     "ventas@az.example",      18, 5),
]

# ---------------------------------------------------------------------------
# HOSPITALES
# ---------------------------------------------------------------------------
# Lista de hospitales/centros de salud que reciben distribucion de vacunas
# desde el sistema. Cada elemento es una tupla con la forma:
#   (nombre, ciudad, capacidad_almacen)
# donde "capacidad_almacen" representa el maximo de dosis que ese hospital
# puede recibir/almacenar en un momento dado, util para limitar la
# distribucion simulada y evitar sobre-stock irreal.
HOSPITALES = [
    # (nombre, ciudad, capacidad_almacen)
    ("Hospital General Central",        "Ciudad Capital", 5000),
    ("Hospital Infantil Norte",         "Ciudad Norte",   3000),
    ("Hospital Regional Sur",           "Ciudad Sur",     4000),
    ("Clinica Universitaria Este",      "Ciudad Este",    2500),
    ("Hospital de Emergencias Oeste",   "Ciudad Oeste",   3500),
    ("Instituto Nacional de Salud",     "Ciudad Capital", 6000),
]

# ---------------------------------------------------------------------------
# CANTIDAD_LOTE_MIN / CANTIDAD_LOTE_MAX
# ---------------------------------------------------------------------------
# Rango (en dosis) que define el tamano base de cada lote recibido de un
# proveedor. Se usa como limite inferior/superior al generar aleatoriamente
# la cantidad de dosis de un nuevo lote en la simulacion.
CANTIDAD_LOTE_MIN = 2000
CANTIDAD_LOTE_MAX = 4200

# ---------------------------------------------------------------------------
# SEVERIDAD_FALLA
# ---------------------------------------------------------------------------
# Diccionario que define, para cada tipo de falla de la cadena de frio, un
# rango (min, max) en grados Celsius que indica cuanto puede subir la
# temperatura de una camara por cada intervalo de 30 minutos que dura la
# falla. El incremento es acumulativo: mientras mas se prolongue la falla,
# mas se acumula el aumento de temperatura, en funcion de la severidad
# especifica de cada tipo de incidente (mas leve en "Puerta Abierta", mas
# grave en "Falla Compresor").
SEVERIDAD_FALLA = {
    "Puerta Abierta":  (0.3, 1.2),
    "Falla Electrica": (1.0, 2.5),
    "Apagon":          (1.2, 3.0),
    "Falla Compresor": (1.5, 3.5),
}

# ---------------------------------------------------------------------------
# PRESUPUESTO_EXCURSION
# ---------------------------------------------------------------------------
# Presupuesto de excursion termica por vacuna: representa cuantos
# "grados-hora" por encima de temp_max puede tolerar cada producto antes de
# que el control de calidad lo rechace (deseche por perdida de cadena de
# frio). Este concepto modela los limites de excursion termica declarados
# por los fabricantes en sus estudios de estabilidad.
#
# Ejemplo de calculo: si la vacuna de Influenza (temp_max = 8 °C) se expone
# a 12 °C durante 2 horas, acumula (12 - 8) * 2 = 8 °C-h de excursion.
#
# Los valores son orientativos y estan pensados para poder editarse y
# experimentar con distintos escenarios de tolerancia termica.
PRESUPUESTO_EXCURSION = {
    "COVID-19 mRNA": 6.0,           # mRNA: la mas fragile
    "COVID-19 Spikevax": 12.0,
    "Influenza Quadrivalent": 30.0,
    "Sarampion-Rubeola": 45.0,      # liofilizada: muy termoestable
}

# ---------------------------------------------------------------------------
# COSTOS_OPERATIVOS
# ---------------------------------------------------------------------------
# Estructura con los costos operativos de la cadena de suministro (en USD),
# usados para los calculos financieros de la simulacion:
#   - "almacenamiento_por_dosis_dia": diccionario con el costo de mantener
#     una dosis almacenada durante un dia, diferenciado por camara. El costo
#     depende del regimen termico de cada camara: entre mas fria es la
#     camara (mayor esfuerzo de refrigeracion), mas caro resulta almacenar
#     ahi una dosis por dia.
#   - "transporte_por_lote": costo fijo (USD) asociado a la logistica de
#     entrada de cada lote recibido de un proveedor.
#   - "distribucion_por_dosis": costo (USD) de entregar cada dosis a un
#     hospital.
#   - "disposicion_por_dosis": costo (USD) de desechar cada dosis perdida
#     como merma (por ejemplo, por vencimiento o excursion termica).
#   - "cuarentena_por_lote": costo (USD) de poner un lote en cuarentena para
#     control de calidad.
# Todos los valores son de referencia y pueden ajustarse segun el escenario
# a simular.
COSTOS_OPERATIVOS = {
    "almacenamiento_por_dosis_dia": {
        "Camara Ultracongelacion A": 0.015,
        "Camara Congelacion B":      0.008,
        "Camara Refrigeracion C":    0.003,
        "Camara Refrigeracion D":    0.003,
        "Almacen General E":         0.001,
    },
    "transporte_por_lote": 150.0,     # USD por lote recibido (logistica de entrada)
    "distribucion_por_dosis": 0.10,   # USD por dosis entregada al hospital
    "disposicion_por_dosis": 0.02,    # USD por dosis desechada (merma)
    "cuarentena_por_lote": 40.0,      # USD por lote puesto en cuarentena (control de calidad)
}