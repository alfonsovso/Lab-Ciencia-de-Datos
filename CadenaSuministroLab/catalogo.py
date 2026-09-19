UBICACIONES = {
    "Camara Ultracongelacion A": {"tipo": "Termometro Digital", "temp_normal": (-75.0, -65.0)},
    "Camara Congelacion B":      {"tipo": "Termometro Digital", "temp_normal": (-22.0, -18.0)},
    "Camara Refrigeracion C":    {"tipo": "Termometro Digital", "temp_normal": (3.0, 7.0)},
    "Camara Refrigeracion D":    {"tipo": "Termometro Digital", "temp_normal": (3.0, 7.0)},
    "Almacen General E":         {"tipo": "Termometro Digital", "temp_normal": (18.0, 24.0)},
}

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

VACUNA_UBICACION = {
    "COVID-19 mRNA":          "Camara Ultracongelacion A",
    "COVID-19 Spikevax":      "Camara Congelacion B",
    "Influenza Quadrivalent": "Camara Refrigeracion C",
    "Sarampion-Rubeola":      "Camara Refrigeracion D",
}

VACUNA_PROVEEDOR = {
    "COVID-19 mRNA":          "Pfizer-BioNTech",
    "COVID-19 Spikevax":      "Moderna Inc.",
    "Influenza Quadrivalent": "Sinovac Biotech",
    "Sarampion-Rubeola":      "AstraZeneca",
}

PROVEEDORES = [
    ("Pfizer-BioNTech", "ventas@pfizer.example", 14, 3),
    ("Moderna Inc.",    "ventas@moderna.example", 16, 4),
    ("Sinovac Biotech", "ventas@sinovac.example", 16, 3),
    ("AstraZeneca",     "ventas@az.example",      18, 5),
]

HOSPITALES = [
    ("Hospital General Central",        "Ciudad Capital", 5000),
    ("Hospital Infantil Norte",         "Ciudad Norte",   3000),
    ("Hospital Regional Sur",           "Ciudad Sur",     4000),
    ("Clinica Universitaria Este",      "Ciudad Este",    2500),
    ("Hospital de Emergencias Oeste",   "Ciudad Oeste",   3500),
    ("Instituto Nacional de Salud",     "Ciudad Capital", 6000),
]

CANTIDAD_LOTE_MIN = 2000
CANTIDAD_LOTE_MAX = 4200

SEVERIDAD_FALLA = {
    "Puerta Abierta":  (0.3, 1.2),
    "Falla Electrica": (1.0, 2.5),
    "Apagon":          (1.2, 3.0),
    "Falla Compresor": (1.5, 3.5),
}

PRESUPUESTO_EXCURSION = {
    "COVID-19 mRNA": 6.0,
    "COVID-19 Spikevax": 12.0,
    "Influenza Quadrivalent": 30.0,
    "Sarampion-Rubeola": 45.0,
}

COSTOS_OPERATIVOS = {
    "almacenamiento_por_dosis_dia": {
        "Camara Ultracongelacion A": 0.015,
        "Camara Congelacion B":      0.008,
        "Camara Refrigeracion C":    0.003,
        "Camara Refrigeracion D":    0.003,
        "Almacen General E":         0.001,
    },
    "transporte_por_lote": 150.0,
    "distribucion_por_dosis": 0.10,
    "disposicion_por_dosis": 0.02,
    "cuarentena_por_lote": 40.0,
}