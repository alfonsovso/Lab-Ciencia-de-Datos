"""
pedidos.py — Demanda hospitalaria, despacho FEFO, vencimientos y
desabastecimiento. Corre dia a dia dentro del motor, no como script aparte.

Author: Ing. G. Alfonso Vargas Solís
Email:  alfonso.vargas.solis@gmail.com
GitHub: alfonsovso
"""
from datetime import timedelta

# Orden de prioridad de los pedidos, de mas urgente (0) a menos urgente
# (3). Definido aqui para uso futuro/externo, aunque el despacho actual
# (obtener_lotes_disponibles / intentar_cumplir) no lo aplica directamente
# para ordenar la atencion de pedidos: el criterio de despacho es FEFO
# (First Expired, First Out) sobre los lotes, no por prioridad del pedido.
PRIORIDAD_ORDEN = {"Urgente": 0, "Alta": 1, "Normal": 2, "Baja": 3}


def procesar_vencimientos(cursor, fecha_hoy):
    """
    Marca como Vencido lo que caduco sin usarse y lo registra como perdida.

    Busca todos los lotes en estado 'Disponible', con cantidad_actual
    positiva, cuya fecha_caducidad ya se alcanzo o paso respecto a
    "fecha_hoy". Para cada uno de esos lotes:
      - Inserta un registro en PerdidaLote con evento_falla_id NULL (para
        distinguir que la perdida es por vencimiento y no por una falla de
        la cadena de frio) y motivo 'Vencimiento: caducidad alcanzada sin
        uso'.
      - Actualiza el lote a estado 'Vencido', pone su cantidad_actual en 0
        y registra la fecha_salida.
      - Inserta un movimiento de inventario de tipo 'Perdida' por la
        cantidad total del lote.

    Parametros:
        cursor: cursor de base de datos usado para las consultas y
            actualizaciones.
        fecha_hoy: fecha (datetime/date) del dia en curso de la
            simulacion, usada como corte para determinar que lotes ya
            caducaron.

    Retorna:
        int: cantidad de lotes que se marcaron como vencidos en esta
        llamada.
    """
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
    """
    Genera de forma aleatoria los pedidos que hacen los hospitales en el
    dia actual de la simulacion, segun los parametros del escenario.

    Para cada hospital de la lista "hospitales":
      - Con probabilidad "prob_pedido_diaria" (del escenario), decide si
        ese hospital hace algun pedido hoy. Si no, se salta al siguiente
        hospital.
      - Si hace pedido, genera entre 1 y "max_pedidos_por_dia" pedidos
        individuales para ese hospital, cada uno para una vacuna elegida
        al azar entre "vacuna_ids".
      - Cada pedido tiene una cantidad solicitada aleatoria dentro del
        rango [cantidad_min, cantidad_max] del escenario, ajustada por el
        "multiplicador_demanda"; una fecha requerida entre 5 y 10 dias
        despues de hoy; y una prioridad elegida al azar con pesos
        ("Baja"=2, "Normal"=5, "Alta"=2, "Urgente"=1), es decir, "Normal"
        es la mas probable.
      - Inserta el encabezado del pedido en la tabla Pedido (estado
        inicial 'Pendiente') y su unico detalle en DetallePedido
        (cantidad_atendida inicial 0), recuperando ambos ids generados.
      - Agrega un diccionario con toda la informacion del pedido a la
        lista "pendientes" (que el motor de simulacion mantiene entre
        dias, para intentar cumplirlos en los dias siguientes).

    Parametros:
        cursor: cursor de base de datos usado para las inserciones.
        hospitales: lista de ids de hospitales a evaluar para generar
            pedidos este dia.
        vacuna_ids: lista de ids de vacunas disponibles, de la cual se
            elige aleatoriamente la vacuna de cada pedido.
        esc: diccionario de parametros del escenario activo (ESCENARIO).
        rng: generador de numeros aleatorios (con semilla fija) usado
            para todas las decisiones aleatorias de esta funcion.
        fecha: fecha (datetime) del dia en curso, usada como
            fecha_pedido y como base para calcular la fecha_requerida.
        pendientes: lista (mutable) de pedidos aun no completamente
            atendidos, mantenida por el motor de simulacion; esta funcion
            le agrega (append) cada nuevo pedido generado.

    Retorna:
        int: cantidad de pedidos individuales creados en esta llamada.
    """
    nuevos = 0
    for hid in hospitales:
        if rng.random() >= esc["prob_pedido_diaria"]:
            # Este hospital no genera ningun pedido hoy.
            continue
        for _ in range(rng.randint(1, esc["max_pedidos_por_dia"])):
            vacuna_id = rng.choice(vacuna_ids)
            # Cantidad solicitada: aleatoria dentro del rango del
            # escenario, ajustada por el multiplicador de demanda, con un
            # minimo de 1 unidad.
            cantidad = max(
                1,
                int(rng.randint(esc["cantidad_min"], esc["cantidad_max"])
                    * esc["multiplicador_demanda"]),
            )
            fecha_requerida = fecha + timedelta(days=rng.randint(5, 10))
            # Prioridad aleatoria, con "Normal" como la opcion mas
            # probable (peso 5 frente a 2/2/1 de las demas).
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
            # Se agrega el pedido a la lista de pendientes que el motor
            # de simulacion ira intentando cumplir dia a dia.
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
    """
    FEFO: primero los que caducan antes. Solo lotes que YA llegaron
    (fecha_ingreso <= hoy): el bug viejo dejaba vender lotes futuros.

    Busca los lotes de una vacuna especifica que estan en condiciones de
    ser despachados hoy: en estado 'Disponible', con cantidad_actual
    positiva, que aun no hayan caducado (fecha_caducidad > fecha_hoy) y
    que ya hayan ingresado fisicamente a la camara (fecha_ingreso <=
    fecha_hoy). El resultado se ordena por fecha_caducidad ascendente,
    implementando la politica FEFO (First Expired, First Out): se
    despachan primero los lotes que estan mas cerca de caducar, para
    minimizar las perdidas por vencimiento.

    Parametros:
        cursor: cursor de base de datos usado para la consulta.
        vacuna_id: id de la vacuna cuyos lotes disponibles se buscan.
        fecha_hoy: fecha (datetime/date) del dia en curso, usada como
            filtro tanto de caducidad como de ingreso.

    Retorna:
        list[dict]: lista de lotes candidatos, cada uno con las claves
        "id" y "cantidad" (cantidad_actual disponible), ordenada por
        fecha de caducidad ascendente.
    """
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
    """
    Intenta despachar, en el dia de hoy, la cantidad faltante de un
    pedido pendiente ("p"), usando los lotes disponibles de su vacuna en
    orden FEFO.

    Calcula primero cuanto falta por entregar (cantidad total solicitada
    menos lo ya atendido en dias anteriores). Si ya no falta nada, no hace
    nada y retorna 0. En caso contrario, recorre los lotes disponibles
    (obtener_lotes_disponibles, ya ordenados por caducidad ascendente) y,
    para cada uno, toma el minimo entre lo que aun falta y lo que ese lote
    tiene disponible:
      - Inserta un registro de Entrega con la cantidad tomada, la fecha
        prometida (fecha_requerida del pedido) y la fecha real de hoy.
      - Descuenta esa cantidad de cantidad_actual del lote.
      - Si, tras el descuento, el lote quedo en cantidad_actual = 0 y
        seguia en estado 'Disponible', lo marca como 'Agotado' y registra
        su fecha_salida (en un UPDATE separado del anterior a proposito,
        para no depender del orden de evaluacion de asignaciones sobre la
        misma columna, evitando un bug que tenia una version previa del
        codigo).
      - Registra un movimiento de inventario de tipo 'Salida' por la
        cantidad tomada de ese lote.
      - Descuenta lo tomado de "faltante" y lo suma a "entregado", y
        continua con el siguiente lote si aun falta algo y hay mas lotes
        disponibles.

    Si se logro entregar algo (entregado > 0):
      - Actualiza la cantidad atendida acumulada del pedido en memoria
        (p["atendida"]) y en la base de datos (DetallePedido).
      - Actualiza el estado del Pedido a 'Atendido' si ya se cubrio toda
        la cantidad solicitada, o a 'Parcial' si aun falta una parte.

    Parametros:
        cursor: cursor de base de datos usado para las consultas y
            actualizaciones.
        p: diccionario del pedido pendiente (tal como lo agrega
            crear_pedidos a la lista "pendientes"), que esta funcion
            tambien actualiza en memoria (p["atendida"]).
        fecha_hoy: fecha (datetime/date) del dia en curso, usada como
            fecha real de la entrega y como filtro de lotes disponibles.

    Retorna:
        int: cantidad total de unidades efectivamente entregadas en esta
        llamada (puede ser 0 si no habia stock disponible).
    """
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
        # Segundo UPDATE separado: asi no depende del orden de evaluacion
        # de asignaciones sobre la misma columna (bug del codigo viejo).
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
        # Se actualiza tanto el estado en memoria del pedido (para que el
        # resto del motor de simulacion lo vea al instante) como su
        # persistencia en la base de datos.
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
    """
    Quita pedidos ya atendidos y cancela los que superaron la espera maxima.

    Recorre la lista de pedidos pendientes y construye una nueva lista
    ("siguen") solo con los que deben seguir intentandose en los proximos
    dias, aplicando dos reglas de depuracion:

      1. Si un pedido ya fue atendido por completo (p["atendida"] >=
         p["cantidad"]), se descarta de la lista (ya no necesita mas
         seguimiento; su estado en BD ya quedo como 'Atendido' desde
         intentar_cumplir).
      2. Si un pedido aun no se completo y ya paso la fecha_requerida mas
         el margen de espera maxima configurado en el escenario
         ("max_dias_espera"), se considera desabastecimiento: se calcula
         la cantidad que quedo sin servir, se inserta un registro en la
         tabla Desabastecimiento (con la fecha de inicio igual a la fecha
         requerida original y la fecha de fin igual a hoy), se actualiza
         el estado del Pedido a 'Cancelado', y el pedido se descarta de la
         lista de pendientes (ya no se seguira intentando cumplir).
      3. Cualquier otro pedido (aun no atendido y todavia dentro del plazo
         de espera) se conserva en la lista "siguen" para reintentarlo en
         dias posteriores.

    Parametros:
        cursor: cursor de base de datos usado para las inserciones y
            actualizaciones.
        pendientes: lista de pedidos aun no completados, tal como la
            mantiene el motor de simulacion entre dias.
        fecha_hoy: fecha (datetime/date) del dia en curso, usada para
            evaluar si ya se supero el plazo maximo de espera.
        esc: diccionario de parametros del escenario activo (ESCENARIO),
            del cual se usa "max_dias_espera".

    Retorna:
        list[dict]: la nueva lista de pedidos que deben seguir
        intentandose en los proximos dias (subconjunto de "pendientes",
        sin los ya atendidos ni los recien cancelados).
    """
    siguen = []
    limite = timedelta(days=esc["max_dias_espera"])
    for p in pendientes:
        if p["atendida"] >= p["cantidad"]:
            # Pedido ya completado: se descarta de la lista de pendientes.
            continue
        if fecha_hoy > p["fecha_requerida"] + limite:
            # Se supero el plazo maximo de espera sin completar el
            # pedido: se registra como desabastecimiento y se cancela.
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
        # Pedido aun dentro del plazo y sin completar: sigue pendiente.
        siguen.append(p)
    return siguen