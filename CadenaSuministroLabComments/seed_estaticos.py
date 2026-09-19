"""
seed_estaticos.py — Siembra los datos fijos (proveedores, hospitales,
vacunas y sensores). Es idempotente: solo inserta si la tabla esta vacia.

Author: Ing. G. Alfonso Vargas Solís
Email:  alfonso.vargas.solis@gmail.com
GitHub: alfonsovso
"""
from catalogo import HOSPITALES, PROVEEDORES, UBICACIONES, VACUNAS


def ejecutar(cursor):
    """
    Siembra en la base de datos los datos de referencia (estaticos) del
    catalogo, leidos desde catalogo.py: proveedores, hospitales, vacunas
    y sensores.

    Para cada una de las cuatro tablas de catalogo (Proveedor, Hospital,
    Vacuna, Sensor), la funcion primero cuenta cuantas filas tiene esa
    tabla; solo si esta vacia (COUNT == 0) procede a insertar los datos
    correspondientes. Esto hace que la funcion sea idempotente: puede
    llamarse multiples veces sobre la misma base de datos sin duplicar
    los registros, ya que en corridas posteriores las tablas ya no
    estaran vacias y se omitira la insercion.

    Secciones sembradas:
      - Proveedor: a partir de catalogo.PROVEEDORES (tuplas nombre,
        contacto, cadencia_dias, variabilidad_dias), inserta cada
        proveedor con su tiempo de entrega promedio y su variabilidad.
      - Hospital: a partir de catalogo.HOSPITALES (tuplas nombre, ciudad,
        capacidad_almacen), inserta cada hospital con su capacidad de
        almacenamiento.
      - Vacuna: a partir de catalogo.VACUNAS (diccionario nombre -> ficha
        tecnica), inserta cada vacuna con su fabricante, rango de
        temperatura valido, dosis por vial y vida util en dias.
      - Sensor: a partir de catalogo.UBICACIONES (diccionario ubicacion
        -> datos de la camara), inserta un sensor por cada camara fisica,
        con su ubicacion y el tipo de sensor instalado.

    Parametros:
        cursor: cursor de base de datos usado para las consultas de
            conteo y las inserciones.

    No retorna ningun valor; su efecto es la insercion (condicional) de
    filas en las tablas Proveedor, Hospital, Vacuna y Sensor.
    """
    # --- Proveedores ---
    # Solo se siembra si la tabla Proveedor esta completamente vacia.
    cursor.execute("SELECT COUNT(*) FROM Proveedor")
    if cursor.fetchone()[0] == 0:
        for nombre, contacto, media, var in PROVEEDORES:
            cursor.execute(
                "INSERT INTO Proveedor (nombre, contacto, tiempo_entrega_promedio_dias, variabilidad_dias) "
                "VALUES (?, ?, ?, ?)",
                nombre, contacto, media, var,
            )

    # --- Hospitales ---
    # Solo se siembra si la tabla Hospital esta completamente vacia.
    cursor.execute("SELECT COUNT(*) FROM Hospital")
    if cursor.fetchone()[0] == 0:
        for nombre, ciudad, capacidad in HOSPITALES:
            cursor.execute(
                "INSERT INTO Hospital (nombre, ciudad, capacidad_almacen) VALUES (?, ?, ?)",
                nombre, ciudad, capacidad,
            )

    # --- Vacunas ---
    # Solo se siembra si la tabla Vacuna esta completamente vacia.
    cursor.execute("SELECT COUNT(*) FROM Vacuna")
    if cursor.fetchone()[0] == 0:
        for nombre, datos in VACUNAS.items():
            cursor.execute(
                "INSERT INTO Vacuna (nombre, fabricante, temp_min, temp_max, dosis_por_vial, vida_util_dias, costo_unitario, precio_unitario) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                nombre, datos["fabricante"], datos["temp_min"], datos["temp_max"],
                datos["dosis_por_vial"], datos["vida_util_dias"],
            )

    # --- Sensores ---
    # Solo se siembra si la tabla Sensor esta completamente vacia. Se
    # inserta un sensor por cada camara fisica definida en UBICACIONES.
    cursor.execute("SELECT COUNT(*) FROM Sensor")
    if cursor.fetchone()[0] == 0:
        for ubicacion, datos in UBICACIONES.items():
            cursor.execute(
                "INSERT INTO Sensor (ubicacion, tipo) VALUES (?, ?)",
                ubicacion, datos["tipo"],
            )