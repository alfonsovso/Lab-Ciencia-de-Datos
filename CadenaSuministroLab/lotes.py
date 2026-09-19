from datetime import timedelta

from catalogo import (CANTIDAD_LOTE_MAX, CANTIDAD_LOTE_MIN, PROVEEDORES,
                      VACUNA_PROVEEDOR)


def _proveedores():
    return {nombre: {"media": media, "var": var}
            for nombre, _, media, var in PROVEEDORES}


def planificar(esc, rng, dias_simulacion, fecha_inicio):
    proveedores = _proveedores()
    plan = []
    secuencial = {vacuna: 0 for vacuna in VACUNA_PROVEEDOR}

    for vacuna, prov_nombre in VACUNA_PROVEEDOR.items():
        prov = proveedores[prov_nombre]
        cadencia = max(1, prov["media"] + esc["dias_extra_entre_lotes"])
        dia = rng.randint(0, 2)
        es_primero = True
        while dia < dias_simulacion:
            if es_primero:
                retraso = 0
                es_primero = False
            else:
                sigma = max(1.0, prov["var"] * esc["multiplicador_retraso_proveedor"])
                retraso = max(0, int(rng.gauss(prov["media"] - 5, sigma)))
            dia_ingreso = dia + retraso
            if dia_ingreso < dias_simulacion:
                secuencial[vacuna] += 1
                cantidad = max(
                    1,
                    int(rng.randint(CANTIDAD_LOTE_MIN, CANTIDAD_LOTE_MAX)
                        * esc["multiplicador_oferta"]),
                )
                plan.append({
                    "vacuna": vacuna,
                    "proveedor": prov_nombre,
                    "seq": secuencial[vacuna],
                    "cantidad": cantidad,
                    "dia": dia_ingreso,
                    "fecha_ingreso": fecha_inicio + timedelta(days=dia_ingreso),
                })
            dia += max(1, cadencia + rng.randint(-3, 3))

    plan.sort(key=lambda item: (item["dia"], item["vacuna"]))
    return plan


def registrar_llegadas(cursor, llegadas, ids, rng):
    for lote in llegadas:
        vacuna_id = ids["vacunas"][lote["vacuna"]]
        vida_util = ids["vida_util"][lote["vacuna"]]
        prov_id = ids["proveedores"][lote["proveedor"]]
        sensor_id = ids["sensor_por_vacuna"][lote["vacuna"]]
        fecha_fab = lote["fecha_ingreso"] - timedelta(days=rng.randint(5, 15))
        fecha_cad = fecha_fab + timedelta(days=vida_util)
        codigo = f"LOTE-{vacuna_id}-{lote['seq']:05d}"
        cursor.execute(
            """
            INSERT INTO Lote (codigo_lote, vacuna_id, proveedor_id, sensor_id,
                              fecha_fabricacion, fecha_caducidad, cantidad_inicial,
                              cantidad_actual, fecha_ingreso, estado)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Disponible')
            """,
            codigo, vacuna_id, prov_id, sensor_id, fecha_fab, fecha_cad,
            lote["cantidad"], lote["cantidad"], lote["fecha_ingreso"],
        )
        lote_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO MovimientoInventario (lote_id, tipo, cantidad, fecha, referencia) "
            "VALUES (?, 'Entrada', ?, ?, ?)",
            lote_id, lote["cantidad"], lote["fecha_ingreso"], f"Ingreso {codigo}",
        )