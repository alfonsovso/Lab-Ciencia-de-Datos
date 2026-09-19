from catalogo import HOSPITALES, PROVEEDORES, UBICACIONES, VACUNAS


def ejecutar(cursor):
    cursor.execute("SELECT COUNT(*) FROM Proveedor")
    if cursor.fetchone()[0] == 0:
        for nombre, contacto, media, var in PROVEEDORES:
            cursor.execute(
                "INSERT INTO Proveedor (nombre, contacto, tiempo_entrega_promedio_dias, variabilidad_dias) "
                "VALUES (?, ?, ?, ?)",
                nombre, contacto, media, var,
            )

    cursor.execute("SELECT COUNT(*) FROM Hospital")
    if cursor.fetchone()[0] == 0:
        for nombre, ciudad, capacidad in HOSPITALES:
            cursor.execute(
                "INSERT INTO Hospital (nombre, ciudad, capacidad_almacen) VALUES (?, ?, ?)",
                nombre, ciudad, capacidad,
            )

    cursor.execute("SELECT COUNT(*) FROM Vacuna")
    if cursor.fetchone()[0] == 0:
        for nombre, datos in VACUNAS.items():
            cursor.execute(
                "INSERT INTO Vacuna (nombre, fabricante, temp_min, temp_max, dosis_por_vial, vida_util_dias, costo_unitario, precio_unitario) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                nombre, datos["fabricante"], datos["temp_min"], datos["temp_max"],
                datos["dosis_por_vial"], datos["vida_util_dias"],
            )

    cursor.execute("SELECT COUNT(*) FROM Sensor")
    if cursor.fetchone()[0] == 0:
        for ubicacion, datos in UBICACIONES.items():
            cursor.execute(
                "INSERT INTO Sensor (ubicacion, tipo) VALUES (?, ?)",
                ubicacion, datos["tipo"],
            )