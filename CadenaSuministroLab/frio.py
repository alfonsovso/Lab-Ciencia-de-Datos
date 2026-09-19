from datetime import timedelta

from catalogo import PRESUPUESTO_EXCURSION, SEVERIDAD_FALLA, UBICACIONES
from config import TEMP_AMBIENTE_MAX

ZONA_LIBERACION = 0.5


def cargar_sensores(cursor):
    cursor.execute("SELECT id, ubicacion FROM Sensor")
    sensores = {}
    for sid, ubicacion in cursor.fetchall():
        datos = UBICACIONES.get(ubicacion)
        if datos is None:
            continue
        sensores[sid] = {"ubicacion": ubicacion, "temp_normal": datos["temp_normal"]}
    return sensores


def obtener_lotes_en_camara(cursor, sensor_id, momento):
    cursor.execute(
        """
        SELECT L.id, L.cantidad_actual, V.nombre, V.temp_max
        FROM Lote L
        JOIN Vacuna V ON V.id = L.vacuna_id
        WHERE L.sensor_id = ? AND L.estado = 'Disponible'
          AND L.cantidad_actual > 0 AND L.fecha_ingreso <= ?
        """,
        sensor_id, momento,
    )
    return [{"id": lid, "cantidad": cant, "vacuna": nom, "tmax": float(tmax)}
            for lid, cant, nom, tmax in cursor.fetchall()]


def _a_cuarentena(cursor, lote, evento_id, momento):
    cursor.execute(
        "UPDATE Lote SET estado = 'Cuarentena' WHERE id = ?",
        lote["id"],
    )
    cursor.execute(
        "INSERT INTO MovimientoInventario (lote_id, tipo, cantidad, fecha, referencia) "
        "VALUES (?, 'Ajuste', ?, ?, ?)",
        lote["id"], lote["cantidad"], momento,
        f"Cuarentena preventiva por evento {evento_id}",
    )


def _decidir_calidad(cursor, reg, evento_id, momento, stats):
    lote = reg["lote"]
    presupuesto = reg["presupuesto"]
    exposicion = reg["exceso"]

    if presupuesto <= 0 or exposicion > presupuesto:
        fraccion_rechazo = 1.0
    elif exposicion <= presupuesto * ZONA_LIBERACION:
        fraccion_rechazo = 0.0
    else:
        tramo = presupuesto * (1.0 - ZONA_LIBERACION)
        fraccion_rechazo = (exposicion - presupuesto * ZONA_LIBERACION) / tramo

    if fraccion_rechazo <= 0.0:
        cursor.execute(
            "UPDATE Lote SET estado = 'Disponible' WHERE id = ?",
            lote["id"],
        )
        cursor.execute(
            "INSERT INTO MovimientoInventario (lote_id, tipo, cantidad, fecha, referencia) "
            "VALUES (?, 'Ajuste', 0, ?, ?)",
            lote["id"], momento,
            f"Liberado tras cuarentena (evento {evento_id})",
        )
        stats["lotes_liberados"] += 1
        return

    rechazadas = int(round(lote["cantidad"] * fraccion_rechazo))
    rechazadas = max(1, min(rechazadas, lote["cantidad"]))
    total = rechazadas >= lote["cantidad"]
    motivo = "Rechazo total tras cuarentena" if total else "Rechazo parcial tras cuarentena"

    cursor.execute(
        """
        INSERT INTO PerdidaLote (lote_id, evento_falla_id, fecha_perdida,
                                 cantidad_perdida, motivo, temp_maxima)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        lote["id"], evento_id, momento, rechazadas,
        f"{motivo} (evento {evento_id})", round(reg["temp_max"], 2),
    )

    if total:
        cursor.execute(
            "UPDATE Lote SET estado = 'Perdido', cantidad_actual = 0, fecha_salida = ? WHERE id = ?",
            momento, lote["id"],
        )
        cursor.execute(
            "INSERT INTO MovimientoInventario (lote_id, tipo, cantidad, fecha, referencia) "
            "VALUES (?, 'Perdida', ?, ?, ?)",
            lote["id"], lote["cantidad"], momento, f"Rechazo total evento {evento_id}",
        )
        stats["lotes_perdidos"] += 1
    else:
        restantes = lote["cantidad"] - rechazadas
        cursor.execute(
            "UPDATE Lote SET estado = 'Disponible', cantidad_actual = ? WHERE id = ?",
            restantes, lote["id"],
        )
        cursor.execute(
            "INSERT INTO MovimientoInventario (lote_id, tipo, cantidad, fecha, referencia) "
            "VALUES (?, 'Perdida', ?, ?, ?)",
            lote["id"], rechazadas, momento, f"Rechazo parcial evento {evento_id}",
        )
        cursor.execute(
            "INSERT INTO MovimientoInventario (lote_id, tipo, cantidad, fecha, referencia) "
            "VALUES (?, 'Ajuste', ?, ?, ?)",
            lote["id"], restantes, momento,
            f"Liberado con merma tras cuarentena (evento {evento_id})",
        )
        stats["lotes_rechazo_parcial"] += 1
    stats["unidades_perdidas"] += rechazadas


def _procesar_falla(cursor, sensor_id, temp_normal, inicio, duracion, esc, rng, lecturas, stats):
    fin = inicio + timedelta(minutes=duracion)
    tipo = rng.choice(sorted(SEVERIDAD_FALLA))
    incremento = rng.uniform(*SEVERIDAD_FALLA[tipo]) * esc["multiplicador_severidad"]

    cursor.execute(
        """
        INSERT INTO EventoFalla (sensor_id, tipo_falla, fecha_inicio, fecha_fin, causa)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?)
        """,
        sensor_id, tipo, inicio, fin, f"Falla simulada: {tipo} en sensor {sensor_id}",
    )
    evento_id = cursor.fetchone()[0]

    lotes = obtener_lotes_en_camara(cursor, sensor_id, inicio)
    paso = timedelta(minutes=esc["intervalo_min"])
    horas_por_paso = esc["intervalo_min"] / 60.0
    afectados = {}
    temp_actual = rng.uniform(*temp_normal)
    t = inicio
    while t <= fin:
        temp_actual = min(temp_actual + incremento, TEMP_AMBIENTE_MAX)
        lecturas.append((sensor_id, t, round(temp_actual, 2)))
        for lote in lotes:
            if lote["cantidad"] <= 0:
                continue
            limite = lote["tmax"] - esc["margen_termico"]
            if temp_actual <= limite:
                continue
            reg = afectados.get(lote["id"])
            if reg is None:
                reg = {
                    "lote": lote,
                    "exceso": 0.0,
                    "temp_max": temp_actual,
                    "presupuesto": PRESUPUESTO_EXCURSION.get(lote["vacuna"], 10.0)
                                   * esc["presupuesto_excursion_mult"],
                }
                afectados[lote["id"]] = reg
                _a_cuarentena(cursor, lote, evento_id, t)
                stats["lotes_en_cuarentena"] += 1
            reg["exceso"] += (temp_actual - limite) * horas_por_paso
            reg["temp_max"] = max(reg["temp_max"], temp_actual)
        t += paso

    for reg in afectados.values():
        _decidir_calidad(cursor, reg, evento_id, fin, stats)
    stats["fallas"] += 1


def simular_dia(cursor, sensores, esc, rng, fecha_dia):
    stats = {
        "fallas": 0,
        "lotes_en_cuarentena": 0,
        "lotes_liberados": 0,
        "lotes_rechazo_parcial": 0,
        "lotes_perdidos": 0,
        "unidades_perdidas": 0,
        "lecturas": 0,
    }
    paso = timedelta(minutes=esc["intervalo_min"])
    fin_dia = fecha_dia + timedelta(days=1)
    lecturas = []

    for sensor_id, info in sensores.items():
        temp_normal = info["temp_normal"]
        inicio_falla = fin_falla = None
        duracion = 0
        if rng.random() < esc["prob_falla_diaria"]:
            hi = min(esc["duracion_falla_max"], 1439)
            lo = min(esc["duracion_falla_min"], hi)
            duracion = rng.randint(lo, hi)
            minuto_inicio = rng.randint(0, 1440 - duracion - 1)
            inicio_falla = fecha_dia + timedelta(minutes=minuto_inicio)
            fin_falla = inicio_falla + timedelta(minutes=duracion)

        t = fecha_dia
        while t < fin_dia:
            dentro_falla = inicio_falla is not None and inicio_falla <= t < fin_falla
            if not dentro_falla:
                lecturas.append((sensor_id, t, round(rng.uniform(*temp_normal), 2)))
            t += paso

        if inicio_falla is not None:
            _procesar_falla(cursor, sensor_id, temp_normal, inicio_falla, duracion,
                            esc, rng, lecturas, stats)

    if lecturas:
        cursor.fast_executemany = True
        cursor.executemany(
            "INSERT INTO LecturaTemperatura (sensor_id, timestamp, temperatura) VALUES (?, ?, ?)",
            lecturas,
        )
        cursor.fast_executemany = False
    stats["lecturas"] = len(lecturas)
    return stats