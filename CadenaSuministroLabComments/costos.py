"""
costos.py — Acumulacion del costo de ALMACENAMIENTO (dosis-dia).
Es el unico costo operativo dependiente del tiempo: se suma cada dia en
la tabla CostoOperativo. Transporte, distribucion, disposicion y
cuarentena se calculan en informes.py a partir de eventos ya registrados.

Author: Ing. G. Alfonso Vargas Solís
Email:  alfonso.vargas.solis@gmail.com
GitHub: alfonsovso
"""
from catalogo import COSTOS_OPERATIVOS, VACUNA_UBICACION


def acumular_almacenamiento(cursor, fecha):
    """
    Costa de mantener el stock (Disponible o Cuarentena) durante un dia.

    Calcula y registra en la base de datos el costo de almacenamiento
    correspondiente a un dia especifico ("fecha"), para cada vacuna que
    tenga stock activo en ese momento.

    Flujo de la funcion:
      1. Consulta en la tabla Lote (unida con Vacuna) la suma de
         "cantidad_actual" agrupada por nombre de vacuna, considerando
         unicamente lotes en estado 'Disponible' o 'Cuarentena', con
         cantidad_actual positiva y cuya fecha_ingreso sea menor o igual a
         la fecha evaluada (es decir, lotes que ya estaban en existencia
         ese dia).
      2. Para cada vacuna con unidades en stock, determina la camara donde
         se almacena (VACUNA_UBICACION) y la tasa de costo por dosis-dia
         correspondiente a esa camara (COSTOS_OPERATIVOS
         ["almacenamiento_por_dosis_dia"]). Si la camara no tiene una tasa
         definida, se usa 0.0 como valor por defecto.
      3. Calcula el monto total del dia como unidades * tasa.
      4. Si el monto es mayor que cero, inserta un registro en la tabla
         CostoOperativo con la categoria 'Almacenamiento', la cantidad base
         (unidades almacenadas), el monto redondeado a 2 decimales y una
         descripcion legible que indica el nombre de la vacuna.

    Parametros:
        cursor: cursor de base de datos (pyodbc) ya abierto, usado tanto
            para consultar el stock vigente como para insertar el costo
            calculado.
        fecha: fecha (datetime/date) del dia que se esta procesando; se usa
            como filtro de la consulta de stock y como valor del campo
            "fecha" en el registro de costo insertado.

    No retorna ningun valor; su efecto es la insercion de filas en la
    tabla CostoOperativo (una fila por cada vacuna con costo de
    almacenamiento mayor a cero en la fecha indicada).
    """
    # Suma, por vacuna, las unidades actualmente almacenadas (Disponible o
    # Cuarentena) en lotes que ya habian ingresado a mas tardar en "fecha".
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
    # Recorre el resultado (nombre de vacuna, total de unidades en stock) y
    # calcula el costo de almacenamiento diario correspondiente a cada una.
    for nombre, unidades in cursor.fetchall():
        # Camara fisica donde se almacena esta vacuna, segun el catalogo.
        camara = VACUNA_UBICACION.get(nombre)
        # Tasa de costo (USD por dosis por dia) asociada a esa camara;
        # 0.0 si la camara no esta definida en COSTOS_OPERATIVOS.
        tasa = COSTOS_OPERATIVOS["almacenamiento_por_dosis_dia"].get(camara, 0.0)
        # Costo total del dia para esta vacuna: unidades en stock * tasa.
        monto = float(unidades) * tasa
        # Solo se registra el costo si es mayor a cero (evita insertar
        # filas irrelevantes cuando la tasa es 0.0 o no hay unidades).
        if monto > 0:
            cursor.execute(
                "INSERT INTO CostoOperativo (fecha, categoria, cantidad_base, monto, descripcion) "
                "VALUES (?, 'Almacenamiento', ?, ?, ?)",
                fecha, unidades, round(monto, 2), f"Almacenamiento diario {nombre}",
            )