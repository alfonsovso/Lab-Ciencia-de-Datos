"""
frio.py — Simulacion diaria de la cadena de frio con gestion realista de
excursiones termicas.

Protocolo (como en la vida real, segun GDP/OMS):
  1. Si la temperatura supera el limite de la vacuna, el lote NO se
     destruye: pasa a 'Cuarentena' y deja de ser despachable.
  2. Mientras dura la falla se acumula su exposicion: grados-hora por
     encima de su limite.
  3. Al terminar la falla, "calidad" compara esa exposicion con el
     presupuesto de excursion de la vacuna (catalogo.PRESUPUESTO_EXCURSION):
       - exposicion <= 50% del presupuesto -> liberado (Disponible)
       - 50% < exposicion <= presupuesto   -> rechazo parcial proporcional
       - exposicion > presupuesto          -> rechazo total (Perdido)

Author: Ing. G. Alfonso Vargas Solís
Email:  alfonso.vargas.solis@gmail.com
GitHub: alfonsovso
"""
from datetime import timedelta

from catalogo import PRESUPUESTO_EXCURSION, SEVERIDAD_FALLA, UBICACIONES
from config import TEMP_AMBIENTE_MAX

# Fraccion del presupuesto por debajo de la cual calidad libera sin merma.
# Es decir, si la exposicion acumulada de un lote no supera esta fraccion
# de su presupuesto de excursion, se considera que no hubo dano relevante
# y el lote se libera completo (sin merma) al finalizar la falla.
ZONA_LIBERACION = 0.5


def cargar_sensores(cursor):
    """
    Devuelve {sensor_id: {"ubicacion": ..., "temp_normal": (min, max)}}.

    Consulta todos los sensores registrados en la base de datos y, para
    cada uno, busca en el catalogo (UBICACIONES) los datos de la camara
    fisica donde esta instalado: su rango de temperatura normal de
    operacion. Los sensores cuya ubicacion no exista en el catalogo se
    omiten (se ignoran silenciosamente), ya que no habria informacion de
    referencia con la cual simular su comportamiento.
    """
    cursor.execute("SELECT id, ubicacion FROM Sensor")
    sensores = {}
    for sid, ubicacion in cursor.fetchall():
        datos = UBICACIONES.get(ubicacion)
        if datos is None:
            # Ubicacion desconocida en el catalogo: se descarta este sensor.
            continue
        sensores[sid] = {"ubicacion": ubicacion, "temp_normal": datos["temp_normal"]}
    return sensores


def obtener_lotes_en_camara(cursor, sensor_id, momento):
    """
    Solo lotes que YA estan fisicamente en la camara en ese instante.

    Recupera los lotes asociados al sensor indicado que se encuentran en
    estado 'Disponible', con cantidad_actual positiva y cuya fecha de
    ingreso sea anterior o igual al "momento" evaluado (es decir, lotes
    que ya habian llegado fisicamente a esa camara para ese instante de la
    simulacion). Se incluye tambien la temperatura maxima permitida
    (temp_max) de la vacuna de cada lote, necesaria para detectar
    excursiones termicas.

    Retorna una lista de diccionarios con las claves: "id", "cantidad",
    "vacuna" y "tmax" (temperatura maxima permitida, como float).
    """
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
    """
    El lote queda retenido: no puede despacharse hasta la decision de calidad.

    Cambia el estado del lote a 'Cuarentena' en la base de datos y registra
    un movimiento de inventario de tipo 'Ajuste' (cantidad 0 de variacion
    real de stock, ya que solo cambia el estado, no la cantidad) con una
    referencia que indica que la cuarentena fue preventiva y a que evento
    de falla esta asociada.
    """
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
    """
    Evalua la exposicion acumulada contra el presupuesto de la vacuna.

    Al finalizar una falla, esta funcion decide el destino final de cada
    lote que estuvo en cuarentena durante el evento, comparando la
    exposicion termica acumulada ("exceso", en grados-hora por encima del
    limite) contra el presupuesto de excursion de su vacuna:

      - Si el presupuesto es 0 (o negativo) o la exposicion supera el
        presupuesto completo -> se rechaza el 100% del lote.
      - Si la exposicion esta dentro de la ZONA_LIBERACION (<= 50% del
        presupuesto) -> no hay rechazo, el lote se libera completo.
      - En el tramo intermedio (entre 50% y 100% del presupuesto) -> se
        calcula una fraccion de rechazo proporcional al punto donde cae la
        exposicion dentro de ese tramo.

    Segun la fraccion de rechazo resultante, la funcion:
      - Si no hay rechazo: actualiza el lote a 'Disponible' y registra un
        movimiento de 'Ajuste' indicando que fue liberado tras cuarentena.
      - Si hay rechazo (parcial o total): calcula las unidades rechazadas
        (redondeando y acotando entre 1 y la cantidad total del lote),
        inserta un registro en PerdidaLote con el motivo y la temperatura
        maxima alcanzada, y luego:
          * Si el rechazo es total: marca el lote como 'Perdido', pone su
            cantidad_actual en 0, registra la fecha_salida y agrega un
            movimiento de inventario de tipo 'Perdida' por toda la
            cantidad del lote.
          * Si el rechazo es parcial: descuenta las unidades rechazadas de
            la cantidad_actual del lote (que vuelve a 'Disponible' con el
            remanente), y registra dos movimientos de inventario: uno de
            'Perdida' por las unidades rechazadas y otro de 'Ajuste' por
            las unidades restantes liberadas con merma.

    Finalmente, actualiza el diccionario "stats" con los contadores
    correspondientes (lotes_liberados, lotes_perdidos,
    lotes_rechazo_parcial y unidades_perdidas), usado para reportar el
    resultado agregado de la simulacion del dia.
    """
    lote = reg["lote"]
    presupuesto = reg["presupuesto"]
    exposicion = reg["exceso"]

    if presupuesto <= 0 or exposicion > presupuesto:
        # Sin presupuesto valido, o exposicion que excede el presupuesto
        # completo: se rechaza el lote en su totalidad.
        fraccion_rechazo = 1.0
    elif exposicion <= presupuesto * ZONA_LIBERACION:
        # Exposicion dentro de la zona tolerada sin merma: se libera todo.
        fraccion_rechazo = 0.0
    else:
        # Exposicion en el tramo intermedio: se calcula la fraccion de
        # rechazo de forma proporcional a que tan avanzada esta la
        # exposicion dentro de ese tramo (entre ZONA_LIBERACION y 100%).
        tramo = presupuesto * (1.0 - ZONA_LIBERACION)
        fraccion_rechazo = (exposicion - presupuesto * ZONA_LIBERACION) / tramo

    if fraccion_rechazo <= 0.0:
        # Dentro de lo tolerado: el lote vuelve a estar disponible.
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

    # Cantidad de unidades a rechazar segun la fraccion calculada,
    # redondeada al entero mas cercano y acotada entre 1 (siempre se
    # rechaza al menos una unidad si hubo rechazo) y la cantidad total
    # del lote (no se puede rechazar mas de lo que existe).
    rechazadas = int(round(lote["cantidad"] * fraccion_rechazo))
    rechazadas = max(1, min(rechazadas, lote["cantidad"]))
    total = rechazadas >= lote["cantidad"]
    motivo = "Rechazo total tras cuarentena" if total else "Rechazo parcial tras cuarentena"

    # Se registra la perdida (parcial o total) con su motivo y la
    # temperatura maxima que alcanzo el lote durante la excursion.
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
        # Rechazo total: el lote queda perdido por completo, sin stock
        # restante, y se registra su fecha de salida del sistema.
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
        # Rechazo parcial: se desecha la fraccion danada y se libera el
        # resto del lote, que vuelve a estar disponible para despacho.
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
    """
    Simula, minuto a minuto (en pasos de intervalo_min), una falla completa
    de la cadena de frio en un sensor/camara especifico: desde su inicio
    hasta su fin, registrando lecturas de temperatura, poniendo en
    cuarentena los lotes afectados y, al final, decidiendo su destino de
    calidad.

    Parametros:
        cursor: cursor de base de datos para las operaciones de lectura y
            escritura.
        sensor_id: identificador del sensor/camara donde ocurre la falla.
        temp_normal: tupla (min, max) de temperatura normal de la camara,
            usada como punto de partida antes de que empiece a subir por
            la falla.
        inicio: datetime en que inicia la falla.
        duracion: duracion de la falla en minutos.
        esc: diccionario de parametros del escenario activo (ESCENARIO),
            usado para ajustar severidad, margen termico, presupuesto de
            excursion e intervalo de lectura.
        rng: generador de numeros aleatorios (con semilla fija para
            reproducibilidad) usado para elegir el tipo de falla, su
            incremento de temperatura y la temperatura inicial.
        lecturas: lista acumuladora (mutable) donde se agregan las
            lecturas de temperatura generadas durante la falla, para
            insertarlas mas tarde en bloque.
        stats: diccionario acumulador de estadisticas del dia, que esta
            funcion actualiza con los contadores de fallas y lotes
            afectados.
    """
    fin = inicio + timedelta(minutes=duracion)
    # Se elige aleatoriamente el tipo de falla (entre las claves ordenadas
    # de SEVERIDAD_FALLA, para reproducibilidad determinista dada la
    # semilla) y se calcula cuanto sube la temperatura por cada intervalo,
    # ajustado por el multiplicador de severidad del escenario.
    tipo = rng.choice(sorted(SEVERIDAD_FALLA))
    incremento = rng.uniform(*SEVERIDAD_FALLA[tipo]) * esc["multiplicador_severidad"]

    # Se registra el evento de falla en la base de datos y se recupera el
    # id generado (OUTPUT INSERTED.id) para asociarlo a los movimientos y
    # perdidas que se generen durante su procesamiento.
    cursor.execute(
        """
        INSERT INTO EventoFalla (sensor_id, tipo_falla, fecha_inicio, fecha_fin, causa)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?)
        """,
        sensor_id, tipo, inicio, fin, f"Falla simulada: {tipo} en sensor {sensor_id}",
    )
    evento_id = cursor.fetchone()[0]

    # Lotes que ya estaban fisicamente en la camara al momento de iniciar
    # la falla; son los unicos que pueden verse afectados por ella.
    lotes = obtener_lotes_en_camara(cursor, sensor_id, inicio)
    paso = timedelta(minutes=esc["intervalo_min"])
    horas_por_paso = esc["intervalo_min"] / 60.0
    afectados = {}   # lote_id -> registro de exposicion acumulada
    # Temperatura inicial aleatoria dentro del rango normal de la camara,
    # que luego ira subiendo por el "incremento" en cada paso de tiempo.
    temp_actual = rng.uniform(*temp_normal)
    t = inicio
    while t <= fin:
        # Tope fisico: ninguna camara supera la temperatura ambiente.
        temp_actual = min(temp_actual + incremento, TEMP_AMBIENTE_MAX)
        lecturas.append((sensor_id, t, round(temp_actual, 2)))
        for lote in lotes:
            if lote["cantidad"] <= 0:
                continue
            # Limite efectivo de temperatura para este lote, restando el
            # margen termico definido en el escenario (que puede hacer el
            # criterio de excursion mas estricto).
            limite = lote["tmax"] - esc["margen_termico"]
            if temp_actual <= limite:
                # Este lote aun no esta en excursion en este paso.
                continue
            reg = afectados.get(lote["id"])
            if reg is None:
                # Primera vez que este lote entra en excursion durante la
                # falla: se inicializa su registro de exposicion y se pone
                # el lote en cuarentena preventivamente.
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
            # Se acumula la exposicion de este paso: grados por encima del
            # limite, multiplicados por la fraccion de hora que dura el
            # paso (intervalo_min convertido a horas).
            reg["exceso"] += (temp_actual - limite) * horas_por_paso
            reg["temp_max"] = max(reg["temp_max"], temp_actual)
        t += paso

    # Al terminar la excursion, calidad decide el destino de cada lote afectado.
    for reg in afectados.values():
        _decidir_calidad(cursor, reg, evento_id, fin, stats)
    stats["fallas"] += 1


def simular_dia(cursor, sensores, esc, rng, fecha_dia):
    """
    Genera lecturas normales y fallas de un dia para todas las camaras.

    Para cada sensor (camara) registrado, simula el comportamiento de la
    temperatura a lo largo de un dia completo (desde "fecha_dia" hasta el
    inicio del dia siguiente), en pasos de "intervalo_min" minutos:

      1. Con probabilidad "prob_falla_diaria" (definida en el escenario),
         decide si ese sensor sufre una falla ese dia. Si ocurre, se
         calcula aleatoriamente su duracion (entre duracion_falla_min y
         duracion_falla_max, acotada a un maximo de 1439 minutos para no
         exceder el dia) y el minuto de inicio dentro del dia, de forma
         que la falla completa quepa dentro del mismo dia.
      2. Recorre cada paso de tiempo del dia: si el paso cae fuera del
         intervalo de la falla (o no hubo falla), se genera una lectura de
         temperatura "normal", aleatoria dentro del rango temp_normal de
         la camara. Los pasos que caen dentro de la ventana de la falla no
         generan aqui una lectura normal, porque seran generados por
         _procesar_falla con la dinamica propia de la falla (temperatura
         subiendo progresivamente).
      3. Si hubo falla, se invoca _procesar_falla para simular en detalle
         la subida de temperatura, la puesta en cuarentena de los lotes
         afectados y la decision de calidad al finalizar.

    Al terminar de procesar todos los sensores, si se generaron lecturas,
    estas se insertan en bloque (bulk insert) en la tabla
    LecturaTemperatura usando executemany con fast_executemany activado
    para mejorar el rendimiento de la insercion masiva.

    Parametros:
        cursor: cursor de base de datos para las operaciones de lectura y
            escritura.
        sensores: diccionario {sensor_id: {"temp_normal": (min, max), ...}}
            tal como lo retorna cargar_sensores().
        esc: diccionario de parametros del escenario activo (ESCENARIO).
        rng: generador de numeros aleatorios con semilla fija, usado para
            todas las decisiones aleatorias del dia (ocurrencia de falla,
            duracion, momento de inicio, lecturas normales, etc.).
        fecha_dia: datetime que marca el inicio del dia a simular
            (medianoche de ese dia).

    Retorna:
        dict: diccionario "stats" con los contadores acumulados del dia:
            "fallas", "lotes_en_cuarentena", "lotes_liberados",
            "lotes_rechazo_parcial", "lotes_perdidos", "unidades_perdidas"
            y "lecturas" (cantidad total de lecturas de temperatura
            generadas e insertadas ese dia).
    """
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
            # Se sortea que este sensor sufra una falla hoy: se calcula su
            # duracion (acotada para no sobrepasar el dia) y el minuto de
            # inicio, de modo que la falla completa quepa dentro del dia.
            hi = min(esc["duracion_falla_max"], 1439)
            lo = min(esc["duracion_falla_min"], hi)
            duracion = rng.randint(lo, hi)
            minuto_inicio = rng.randint(0, 1440 - duracion - 1)
            inicio_falla = fecha_dia + timedelta(minutes=minuto_inicio)
            fin_falla = inicio_falla + timedelta(minutes=duracion)

        # Genera lecturas de temperatura "normales" para todos los pasos
        # del dia que no caen dentro de la ventana de la falla (si la hay).
        t = fecha_dia
        while t < fin_dia:
            dentro_falla = inicio_falla is not None and inicio_falla <= t < fin_falla
            if not dentro_falla:
                lecturas.append((sensor_id, t, round(rng.uniform(*temp_normal), 2)))
            t += paso

        # Si hubo falla, se procesa en detalle: lecturas propias de la
        # falla, cuarentena de lotes afectados y decision de calidad.
        if inicio_falla is not None:
            _procesar_falla(cursor, sensor_id, temp_normal, inicio_falla, duracion,
                            esc, rng, lecturas, stats)

    # Insercion masiva (bulk insert) de todas las lecturas del dia, con
    # fast_executemany activado temporalmente para mejorar el rendimiento.
    if lecturas:
        cursor.fast_executemany = True
        cursor.executemany(
            "INSERT INTO LecturaTemperatura (sensor_id, timestamp, temperatura) VALUES (?, ?, ?)",
            lecturas,
        )
        cursor.fast_executemany = False
    stats["lecturas"] = len(lecturas)
    return stats