from datetime import timedelta

PRIORIDAD_ORDEN = {"Urgente": 0, "Alta": 1, "Normal": 2, "Baja": 3}


def procesar_vencimientos(cursor, fecha_hoy):
    cursor.execute(
        """
        SELECT id, cantidad_actual
        FROM Lote
        WHERE estado = 'Disponible' AND cantidad_actual > 0 AND fecha_caducidad <= ?
        """,
        fecha_hoy,
    )
    vencidos = cursor.fetchall()
    for lote_id, cantidad in vencidos:
        cursor.execute(
            """
            INSERT INTO PerdidaLote (lote_id, evento_falla_id, fecha_perdida,
                                     cantidad_perdida, motivo, temp_maxima)
            VALUES (?, NULL, ?, ?, 'Vencimiento: caducidad alcanzada sin uso', NULL)
            """,
            lote_id, fecha_hoy, cantidad,
        )
        cursor.execute(
            "UPDATE Lote SET estado = 'Vencido', cantidad_actual = 0, fecha_salida = ? WHERE id = ?",
            fecha_hoy, lote_id,
        )
        cursor.execute(
            "INSERT INTO MovimientoInventario (lote_id, tipo, cantidad, fecha, referencia) "
            "VALUES (?, 'Perdida', ?, ?, ?)",
            lote_id, cantidad, fecha_hoy, f"Vencimiento lote {lote_id}",
        )
    return len(vencidos)


def crear_pedidos(cursor, hospitales, vacuna_ids, esc, rng, fecha, pendientes):
    nuevos = 0
    for hid in hospitales:
        if rng.random() >= esc["prob_pedido_diaria"]:
            continue
        for _ in range(rng.randint(1, esc["max_pedidos_por_dia"])):
            vacuna_id = rng.choice(vacuna_ids)
            cantidad = max(
                1,
                int(rng.randint(esc["cantidad_min"], esc["cantidad_max"])
                    * esc["multiplicador_demanda"]),
            )
            fecha_requerida = fecha + timedelta(days=rng.randint(5, 10))
            prioridad = rng.choices(
                ["Baja", "Normal", "Alta", "Urgente"], weights=[2, 5, 2, 1]
            )[0]
            cursor.execute(
                """
                INSERT INTO Pedido (hospital_id, fecha_pedido, fecha_requerida, estado, prioridad)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, 'Pendiente', ?)
                """,
                hid, fecha, fecha_requerida, prioridad,
            )
            pedido_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO DetallePedido (pedido_id, vacuna_id, cantidad_solicitada, cantidad_atendida)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, 0)
                """,
                pedido_id, vacuna_id, cantidad,
            )
            detalle_id = cursor.fetchone()[0]
            pendientes.append({
                "pedido_id": pedido_id,
                "detalle_id": detalle_id,
                "hospital_id": hid,
                "vacuna_id": vacuna_id,
                "cantidad": cantidad,
                "atendida": 0,
                "fecha_requerida": fecha_requerida,
                "prioridad": prioridad,
            })
            nuevos += 1
    return nuevos


def obtener_lotes_disponibles(cursor, vacuna_id, fecha_hoy):
    cursor.execute(
        """
        SELECT id, cantidad_actual
        FROM Lote
        WHERE vacuna_id = ? AND estado = 'Disponible' AND cantidad_actual > 0
          AND fecha_caducidad > ? AND fecha_ingreso <= ?
        ORDER BY fecha_caducidad ASC
        """,
        vacuna_id, fecha_hoy, fecha_hoy,
    )
    return [{"id": lid, "cantidad": cant} for lid, cant in cursor.fetchall()]


def intentar_cumplir(cursor, p, fecha_hoy):
    faltante = p["cantidad"] - p["atendida"]
    if faltante <= 0:
        return 0
    entregado = 0
    for lote in obtener_lotes_disponibles(cursor, p["vacuna_id"], fecha_hoy):
        if faltante <= 0:
            break
        tomar = min(faltante, lote["cantidad"])
        cursor.execute(
            """
            INSERT INTO Entrega (detalle_pedido_id, lote_id, cantidad_entregada,
                                 fecha_prometida, fecha_real)
            VALUES (?, ?, ?, ?, ?)
            """,
            p["detalle_id"], lote["id"], tomar, p["fecha_requerida"], fecha_hoy,
        )
        cursor.execute(
            "UPDATE Lote SET cantidad_actual = cantidad_actual - ? WHERE id = ?",
            tomar, lote["id"],
        )
        cursor.execute(
            "UPDATE Lote SET estado = 'Agotado', fecha_salida = ? "
            "WHERE id = ? AND cantidad_actual = 0 AND estado = 'Disponible'",
            fecha_hoy, lote["id"],
        )
        cursor.execute(
            "INSERT INTO MovimientoInventario (lote_id, tipo, cantidad, fecha, referencia) "
            "VALUES (?, 'Salida', ?, ?, ?)",
            lote["id"], tomar, fecha_hoy, f"Entrega pedido {p['pedido_id']}",
        )
        faltante -= tomar
        entregado += tomar

    if entregado > 0:
        p["atendida"] += entregado
        cursor.execute(
            "UPDATE DetallePedido SET cantidad_atendida = ? WHERE id = ?",
            p["atendida"], p["detalle_id"],
        )
        cursor.execute(
            "UPDATE Pedido SET estado = ? WHERE id = ?",
            "Atendido" if p["atendida"] >= p["cantidad"] else "Parcial",
            p["pedido_id"],
        )
    return entregado


def depurar(cursor, pendientes, fecha_hoy, esc):
    siguen = []
    limite = timedelta(days=esc["max_dias_espera"])
    for p in pendientes:
        if p["atendida"] >= p["cantidad"]:
            continue
        if fecha_hoy > p["fecha_requerida"] + limite:
            faltante = p["cantidad"] - p["atendida"]
            cursor.execute(
                """
                INSERT INTO Desabastecimiento (hospital_id, vacuna_id, pedido_id,
                                               fecha_inicio, fecha_fin,
                                               cantidad_faltante, causa)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                p["hospital_id"], p["vacuna_id"], p["pedido_id"],
                p["fecha_requerida"], fecha_hoy, faltante,
                "Sin stock disponible tras espera maxima",
            )
            cursor.execute(
                "UPDATE Pedido SET estado = 'Cancelado' WHERE id = ?",
                p["pedido_id"],
            )
            continue
        siguen.append(p)
    return siguen