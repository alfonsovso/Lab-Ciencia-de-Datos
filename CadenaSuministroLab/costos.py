from catalogo import COSTOS_OPERATIVOS, VACUNA_UBICACION


def acumular_almacenamiento(cursor, fecha):
    cursor.execute(
        """
        SELECT V.nombre, SUM(L.cantidad_actual)
        FROM Lote L JOIN Vacuna V ON V.id = L.vacuna_id
        WHERE L.estado IN ('Disponible','Cuarentena') AND L.cantidad_actual > 0
          AND L.fecha_ingreso <= ?
        GROUP BY V.nombre
        """,
        fecha,
    )
    for nombre, unidades in cursor.fetchall():
        camara = VACUNA_UBICACION.get(nombre)
        tasa = COSTOS_OPERATIVOS["almacenamiento_por_dosis_dia"].get(camara, 0.0)
        monto = float(unidades) * tasa
        if monto > 0:
            cursor.execute(
                "INSERT INTO CostoOperativo (fecha, categoria, cantidad_base, monto, descripcion) "
                "VALUES (?, 'Almacenamiento', ?, ?, ?)",
                fecha, unidades, round(monto, 2), f"Almacenamiento diario {nombre}",
            )