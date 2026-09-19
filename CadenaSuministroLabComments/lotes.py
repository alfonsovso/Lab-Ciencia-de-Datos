"""
lotes.py — Planificacion (en memoria) y registro en BD de la llegada de
lotes. El primer lote de cada vacuna llega al inicio para que la cadena
arranque con stock; los siguientes siguen la cadencia del proveedor.

Author: Ing. G. Alfonso Vargas Solís
Email:  alfonso.vargas.solis@gmail.com
GitHub: alfonsovso
"""
from datetime import timedelta

from catalogo import (CANTIDAD_LOTE_MAX, CANTIDAD_LOTE_MIN, PROVEEDORES,
                      VACUNA_PROVEEDOR)


def _proveedores():
    """
    Convierte la lista PROVEEDORES (tuplas nombre, contacto, cadencia,
    variabilidad) en un diccionario indexado por nombre de proveedor, con
    las claves "media" (cadencia promedio en dias entre lotes) y "var"
    (variabilidad/desviacion del retraso), descartando el contacto ya que
    no se necesita para la planificacion de llegadas.
    """
    return {nombre: {"media": media, "var": var}
            for nombre, _, media, var in PROVEEDORES}


def planificar(esc, rng, dias_simulacion, fecha_inicio):
    """
    Devuelve el calendario de llegadas, ordenado por dia.

    Para cada vacuna (segun VACUNA_PROVEEDOR), genera en memoria la
    secuencia completa de lotes que llegaran durante toda la simulacion,
    simulando el comportamiento de reposicion de su proveedor:

      - El primer lote de cada vacuna llega casi de inmediato (entre el
        dia 0 y el dia 2, elegido al azar), sin retraso adicional, para
        que la cadena arranque con stock disponible desde el principio.
      - Los lotes siguientes llegan con una cadencia base igual a la
        media del proveedor mas los dias extra configurados en el
        escenario ("dias_extra_entre_lotes"), con un pequeno ruido
        aleatorio (+/- 3 dias) en cada ciclo, y ademas cada llegada
        individual puede sufrir un retraso adicional generado con una
        distribucion normal (gauss) centrada en (media - 5) dias y con
        una desviacion tipica ("sigma") igual a la variabilidad del
        proveedor multiplicada por "multiplicador_retraso_proveedor" del
        escenario (con un piso de 1.0 para evitar una sigma nula). El
        retraso nunca es negativo.
      - La cantidad de cada lote se genera aleatoriamente dentro del
        rango [CANTIDAD_LOTE_MIN, CANTIDAD_LOTE_MAX] y se ajusta por el
        multiplicador de oferta del escenario ("multiplicador_oferta"),
        garantizando un minimo de 1 unidad.
      - Solo se agregan al plan los lotes cuyo dia de ingreso calculado
        cae dentro del horizonte de la simulacion (menor que
        "dias_simulacion"); el avance al siguiente ciclo de llegada
        continua igual aunque un lote puntual quede fuera de rango.

    Parametros:
        esc: diccionario de parametros del escenario activo (ESCENARIO),
            usado para ajustar cadencia, retraso y cantidad de los lotes.
        rng: generador de numeros aleatorios (con semilla fija) usado
            para todas las decisiones aleatorias de la planificacion.
        dias_simulacion: duracion total de la simulacion, en dias; limite
            superior (exclusivo) para el dia de ingreso de cualquier lote.
        fecha_inicio: fecha calendario (datetime) correspondiente al dia 0
            de la simulacion, usada para convertir el dia de ingreso
            (entero) en una fecha real.

    Retorna:
        list[dict]: lista de lotes planificados, cada uno con las claves
        "vacuna", "proveedor", "seq" (numero secuencial del lote dentro de
        esa vacuna), "cantidad", "dia" (entero, dias desde el inicio) y
        "fecha_ingreso" (datetime), ordenada por dia de ingreso y, en caso
        de empate, por nombre de vacuna.
    """
    proveedores = _proveedores()
    plan = []
    # Contador secuencial de lotes por vacuna, usado para numerar cada
    # lote dentro de su propia serie (1, 2, 3, ...).
    secuencial = {vacuna: 0 for vacuna in VACUNA_PROVEEDOR}

    for vacuna, prov_nombre in VACUNA_PROVEEDOR.items():
        prov = proveedores[prov_nombre]
        # Cadencia efectiva entre lotes: la media del proveedor mas los
        # dias extra del escenario, con un piso de 1 dia.
        cadencia = max(1, prov["media"] + esc["dias_extra_entre_lotes"])
        dia = rng.randint(0, 2)      # stock inicial: primer lote casi inmediato
        es_primero = True
        while dia < dias_simulacion:
            if es_primero:
                # El primer lote de la vacuna no sufre retraso adicional:
                # llega justo en el dia sorteado al inicio.
                retraso = 0
                es_primero = False
            else:
                # Los lotes siguientes pueden llegar con retraso adicional,
                # modelado con una distribucion normal centrada en
                # (media - 5) dias; la sigma depende de la variabilidad del
                # proveedor y del multiplicador de retraso del escenario.
                # El retraso nunca puede ser negativo.
                sigma = max(1.0, prov["var"] * esc["multiplicador_retraso_proveedor"])
                retraso = max(0, int(rng.gauss(prov["media"] - 5, sigma)))
            dia_ingreso = dia + retraso
            if dia_ingreso < dias_simulacion:
                # Solo se registra el lote si su fecha de ingreso cae
                # dentro del horizonte de la simulacion.
                secuencial[vacuna] += 1
                # Cantidad de dosis del lote: aleatoria dentro del rango
                # base del catalogo, ajustada por el multiplicador de
                # oferta del escenario, con un minimo de 1 unidad.
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
            # Avanza al siguiente ciclo de llegada: cadencia base mas un
            # pequeno ruido aleatorio de +/- 3 dias, con un piso de 1 dia
            # para garantizar que el bucle siempre progrese.
            dia += max(1, cadencia + rng.randint(-3, 3))

    # Se ordena el plan completo (de todas las vacunas mezcladas) por dia
    # de ingreso y, en caso de empate, alfabeticamente por vacuna.
    plan.sort(key=lambda item: (item["dia"], item["vacuna"]))
    return plan


def registrar_llegadas(cursor, llegadas, ids, rng):
    """
    Inserta los lotes cuya fecha de ingreso es el dia en curso.

    Para cada lote planificado que llega en el dia actual de la
    simulacion, inserta el registro correspondiente en la tabla Lote y su
    movimiento de inventario de tipo 'Entrada' asociado:

      - Calcula una fecha de fabricacion aleatoria, entre 5 y 15 dias
        antes de la fecha de ingreso del lote, y a partir de ella la
        fecha de caducidad, sumando la vida util (en dias) de esa vacuna.
      - Genera un codigo de lote legible con el formato
        "LOTE-{vacuna_id}-{seq:05d}" (numero secuencial de 5 digitos con
        ceros a la izquierda).
      - Inserta el lote en la tabla Lote con estado inicial 'Disponible',
        con cantidad_inicial y cantidad_actual iguales a la cantidad
        planificada, y recupera el id autogenerado del lote insertado
        (OUTPUT INSERTED.id).
      - Inserta un movimiento de inventario de tipo 'Entrada' por la
        cantidad total del lote, con una referencia que incluye el
        codigo del lote, dejando trazabilidad del ingreso.

    Parametros:
        cursor: cursor de base de datos usado para las inserciones.
        llegadas: lista de lotes (subconjunto del plan generado por
            planificar()) que deben registrarse en el dia en curso.
        ids: diccionario con los mapeos de nombres a identificadores de
            base de datos necesarios para insertar el lote: "vacunas"
            (nombre de vacuna -> id), "vida_util" (nombre de vacuna ->
            dias de vida util), "proveedores" (nombre de proveedor -> id)
            y "sensor_por_vacuna" (nombre de vacuna -> id del sensor de
            la camara donde se almacena).
        rng: generador de numeros aleatorios (con semilla fija) usado
            para calcular la fecha de fabricacion de cada lote.

    No retorna ningun valor; su efecto es la insercion de una fila en
    Lote y otra en MovimientoInventario por cada lote de "llegadas".
    """
    for lote in llegadas:
        vacuna_id = ids["vacunas"][lote["vacuna"]]
        vida_util = ids["vida_util"][lote["vacuna"]]
        prov_id = ids["proveedores"][lote["proveedor"]]
        sensor_id = ids["sensor_por_vacuna"][lote["vacuna"]]
        # Fecha de fabricacion: entre 5 y 15 dias antes del ingreso, y la
        # fecha de caducidad se deriva sumando la vida util del producto.
        fecha_fab = lote["fecha_ingreso"] - timedelta(days=rng.randint(5, 15))
        fecha_cad = fecha_fab + timedelta(days=vida_util)
        codigo = f"LOTE-{vacuna_id}-{lote['seq']:05d}"
        # Inserta el lote como 'Disponible', con cantidad_inicial y
        # cantidad_actual iguales (aun no se ha despachado ni perdido
        # nada), y recupera el id generado para usarlo en el movimiento
        # de inventario asociado.
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
        # Registra el movimiento de inventario de entrada correspondiente
        # a la llegada de este lote, por su cantidad total.
        cursor.execute(
            "INSERT INTO MovimientoInventario (lote_id, tipo, cantidad, fecha, referencia) "
            "VALUES (?, 'Entrada', ?, ?, ?)",
            lote_id, lote["cantidad"], lote["fecha_ingreso"], f"Ingreso {codigo}",
        )