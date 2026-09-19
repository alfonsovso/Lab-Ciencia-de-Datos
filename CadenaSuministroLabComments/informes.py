"""
informes.py — Reporte final de indicadores (KPI) y diagnóstico de la cadena.

Genera un informe detallado y autoexplicativo. Cada sección agrupa métricas
relacionadas, y al final hay un diagnóstico con alertas concretas y qué
parámetro del ESCENARIO tocar para corregirlas.

NOTA: SQL Server devuelve las columnas DECIMAL como decimal.Decimal, que no
se puede operar con float. Por eso _uno() convierte Decimal -> float.

Author: Ing. G. Alfonso Vargas Solís
Email:  alfonso.vargas.solis@gmail.com
GitHub: alfonsovso
"""
from decimal import Decimal

from config import ESCENARIO
from catalogo import COSTOS_OPERATIVOS


def _uno(cursor, sql):
    """
    Ejecuta una consulta SQL que retorna un unico valor escalar (por
    ejemplo, un COUNT, SUM o AVG) y lo devuelve ya normalizado a un tipo
    de Python operable.

    Si el valor recuperado es un decimal.Decimal (tipico de columnas
    DECIMAL de SQL Server, como costos, precios o montos), se convierte a
    float para poder operarlo aritmeticamente junto con otros numeros. Los
    valores enteros (por ejemplo, resultados de COUNT) llegan como int y
    se devuelven sin modificacion.
    """
    cursor.execute(sql)
    valor = cursor.fetchone()[0]
    # Los agregados sobre columnas DECIMAL (costos/precios/monto) llegan como
    # decimal.Decimal, que no opera con float. Los pasamos a float; los
    # conteos (INT) llegan como int y no se tocan.
    return float(valor) if isinstance(valor, Decimal) else valor


def _filas(cursor, sql):
    """
    Ejecuta una consulta SQL que retorna multiples filas y devuelve el
    resultado completo como una lista de tuplas (tal como lo entrega
    cursor.fetchall()). Se usa para las tablas de detalle del informe
    (por vacuna, por hospital, por camara, etc.).
    """
    cursor.execute(sql)
    return cursor.fetchall()


def _pct(parte, total):
    """
    Calcula que porcentaje representa "parte" sobre "total", expresado en
    una escala de 0 a 100. Si "total" es cero (o falsy), retorna 0.0 en
    lugar de generar una division por cero, ya que en ese caso el
    porcentaje no tiene sentido definido.
    """
    return (parte / total * 100.0) if total else 0.0


def _fmt(label, valor, width=46):
    """
    Da formato a una linea de "etiqueta ........... valor" para las
    secciones del informe, rellenando el espacio entre el label y el
    valor con puntos hasta alcanzar el ancho indicado (minimo 2 puntos),
    de modo que los valores queden visualmente alineados en columnas.
    """
    puntos = "." * max(2, width - len(label))
    return f"    {label} {puntos} {valor}"


def _usd(x):
    """
    Da formato a un numero como monto en dolares (USD), con separador de
    miles y dos decimales, por ejemplo: 1234.5 -> "$1,234.50".
    """
    return f"${x:,.2f}"


def _li(label, valor, ancho=54):
    """
    Variante de _fmt() con un ancho de columna distinto (54 en lugar de
    46), usada en las secciones financieras del informe (valoracion de
    inventario, costos operativos y resultado economico) para mantener
    una alineacion consistente entre etiquetas y valores mas largos.
    """
    return f"    {label} {'.' * max(2, ancho - len(label))} {valor}"


def generar(cursor, modo, dias):
    """
    Genera e imprime en consola el informe final de la simulacion,
    compuesto por 11 secciones numeradas mas un bloque de diagnostico con
    alertas automaticas.

    Parametros:
        cursor: cursor de base de datos (pyodbc) usado para todas las
            consultas de agregacion sobre las tablas de la simulacion
            (Lote, Pedido, DetallePedido, PerdidaLote, EventoFalla,
            LecturaTemperatura, Desabastecimiento, Entrega,
            MovimientoInventario, CostoOperativo, Vacuna, Hospital,
            Sensor).
        modo: nombre del escenario/preset con el que corrio la
            simulacion (por ejemplo, "normal", "estres" o "critico"),
            usado unicamente para mostrarlo en el encabezado del informe.
        dias: cantidad de dias que duro la simulacion, usada para
            calcular la demanda media diaria.

    La funcion no retorna ningun valor: su efecto es enteramente la
    impresion por consola (print) del informe completo.

    Estructura general del informe:
        [1]  Balance de masas: verifica que cada unidad recibida termine
             contabilizada en exactamente un destino (entregada, en
             stock, en cuarentena o perdida), calculando un "cuadre" que
             deberia dar 0 si la contabilidad esta completa.
        [2]  Inventario: lotes recibidos, stock final, cobertura en dias
             y desglose de perdidas, mas un detalle de lotes por estado.
        [3]  Demanda y nivel de servicio: pedidos, unidades solicitadas
             vs. atendidas, fill rate y demanda media diaria.
        [4]  Demanda por vacuna: mismo analisis de servicio pero
             desglosado por cada tipo de vacuna.
        [5]  Cadena de frio: lecturas de temperatura, fallas registradas,
             su duracion media, temperaturas extremas, fallas por tipo y
             temperatura maxima alcanzada por camara.
        [6]  Calidad y cuarentena: cuantos lotes pasaron por cuarentena y
             como fueron resueltos (liberados, rechazo parcial o total).
        [7]  Logistica y entregas: cantidad de entregas, puntualidad y
             retraso medio.
        [8]  Desabastecimiento: eventos y unidades faltantes, con detalle
             por hospital y por vacuna cuando hay desabastecimiento.
        [9]  Valoracion de inventario en USD: inversion total, costo de
             lo entregado, perdidas valorizadas y valor del stock final.
        [10] Costos operativos en USD: almacenamiento, transporte,
             distribucion, disposicion de mermas y cuarentena/calidad.
        [11] Resultado economico en USD: ingresos, margen bruto,
             resultado operativo y resultado final, encadenando las
             cifras de las secciones [9] y [10].
        Diagnostico final: clasifica el desempeno general de la cadena
             (EXCELENTE/BUENA/DEGRADADA/CRITICA) segun el fill rate y el
             desabastecimiento, y genera una lista de alertas concretas
             (con el parametro del ESCENARIO sugerido para corregir cada
             problema) cuando se detectan condiciones fuera de rango.
    """
    # ================= DATOS BASE =================
    # Conteos y sumas fundamentales que alimentan el resto de secciones
    # del informe: cuantos lotes hay, cuanto se recibio, cuanto queda en
    # stock (disponible o en cuarentena), cuanto se solicito/atendio,
    # cuanto se perdio (por frio o por vencimiento), estadisticas de
    # fallas y lecturas de temperatura, desabastecimiento, entregas y
    # movimientos de cuarentena/liberacion/rechazo.
    lotes = _uno(cursor, "SELECT COUNT(*) FROM Lote")
    recibidas = _uno(cursor, "SELECT ISNULL(SUM(cantidad_inicial),0) FROM Lote")
    stock_final = _uno(cursor, "SELECT ISNULL(SUM(cantidad_actual),0) FROM Lote WHERE estado='Disponible'")
    stock_cuarentena = _uno(cursor, "SELECT ISNULL(SUM(cantidad_actual),0) FROM Lote WHERE estado='Cuarentena'")

    solicitadas = _uno(cursor, "SELECT ISNULL(SUM(cantidad_solicitada),0) FROM DetallePedido")
    atendidas = _uno(cursor, "SELECT ISNULL(SUM(cantidad_atendida),0) FROM DetallePedido")
    no_atendidas = solicitadas - atendidas
    total_pedidos = _uno(cursor, "SELECT COUNT(*) FROM Pedido")
    abiertos = _uno(cursor, "SELECT COUNT(*) FROM Pedido WHERE estado IN ('Pendiente','Parcial')")
    por_estado_pedido = dict(_filas(cursor, "SELECT estado, COUNT(*) FROM Pedido GROUP BY estado"))

    perd_frio = _uno(cursor, "SELECT ISNULL(SUM(cantidad_perdida),0) FROM PerdidaLote WHERE evento_falla_id IS NOT NULL")
    perd_venc = _uno(cursor, "SELECT ISNULL(SUM(cantidad_perdida),0) FROM PerdidaLote WHERE evento_falla_id IS NULL")
    perdidas_total = perd_frio + perd_venc

    fallas = _uno(cursor, "SELECT COUNT(*) FROM EventoFalla")
    dur_media_falla = _uno(cursor, "SELECT ISNULL(AVG(CAST(duracion_minutos AS FLOAT)),0) FROM EventoFalla WHERE fecha_fin IS NOT NULL")
    lecturas = _uno(cursor, "SELECT COUNT(*) FROM LecturaTemperatura")
    temp_max = _uno(cursor, "SELECT ISNULL(MAX(temperatura),0) FROM LecturaTemperatura")
    temp_min = _uno(cursor, "SELECT ISNULL(MIN(temperatura),0) FROM LecturaTemperatura")

    desab = _uno(cursor, "SELECT COUNT(*) FROM Desabastecimiento")
    faltantes = _uno(cursor, "SELECT ISNULL(SUM(cantidad_faltante),0) FROM Desabastecimiento")

    entregas = _uno(cursor, "SELECT COUNT(*) FROM Entrega")
    retrasadas = _uno(cursor, "SELECT COUNT(*) FROM Entrega WHERE retraso_dias > 0")
    retraso_medio = _uno(cursor, "SELECT ISNULL(AVG(CAST(retraso_dias AS FLOAT)),0) FROM Entrega WHERE retraso_dias > 0")

    # Lotes que pasaron por cuarentena preventiva y como fueron resueltos
    # despues, segun el registro dejado por frio.py en MovimientoInventario
    # y PerdidaLote (ver _a_cuarentena y _decidir_calidad en frio.py).
    cuarentenas = _uno(cursor, "SELECT COUNT(DISTINCT lote_id) FROM MovimientoInventario "
                               "WHERE tipo='Ajuste' AND referencia LIKE 'Cuarentena preventiva%'")
    liberados = _uno(cursor, "SELECT COUNT(*) FROM MovimientoInventario "
                             "WHERE tipo='Ajuste' AND referencia LIKE 'Liberado%'")
    rechazos_parciales = _uno(cursor, "SELECT COUNT(*) FROM PerdidaLote WHERE motivo LIKE 'Rechazo parcial%'")
    rechazos_totales = _uno(cursor, "SELECT COUNT(*) FROM PerdidaLote WHERE motivo LIKE 'Rechazo total%'")

    # ================= DERIVADOS =================
    # Indicadores calculados a partir de los datos base: nivel de
    # servicio (fill rate), porcentaje de perdida sobre lo recibido,
    # porcentaje de entregas puntuales, demanda media diaria, dias de
    # cobertura del stock final, y el "cuadre" de balance de masas (debe
    # dar 0 si toda unidad recibida quedo contabilizada en algun destino).
    fill = _pct(atendidas, solicitadas)
    pct_perdida = _pct(perdidas_total, recibidas)
    pct_puntuales = _pct(entregas - retrasadas, entregas)
    tasa_demanda = (solicitadas / dias) if dias else 0.0
    cobertura = (stock_final / tasa_demanda) if tasa_demanda else 0.0
    cuadre = recibidas - (atendidas + stock_final + stock_cuarentena + perd_frio + perd_venc)

    linea = "=" * 70
    print()
    print(linea)
    print(f"  RESULTADOS DE LA SIMULACION   |   modo: {modo}   |   {dias} dias")
    print(linea)

    # ---------------- [1] BALANCE DE MASAS ----------------
    # Verifica, en terminos de unidades, que todo lo recibido (100%) se
    # reparta exactamente entre: entregado, stock disponible, stock en
    # cuarentena sin resolver, perdidas por frio y perdidas por
    # vencimiento. El "cuadre" final deberia ser 0; cualquier desviacion
    # indicaria una inconsistencia en el registro de movimientos.
    print("\n[1] BALANCE DE MASAS — cada unidad recibida termina en un solo sitio")
    print(_fmt("Unidades recibidas (100%)", f"{recibidas:,}"))
    print(_fmt("  -> Entregadas a hospitales", f"{atendidas:,}  ({_pct(atendidas, recibidas):.1f}%)"))
    print(_fmt("  -> Stock final disponible", f"{stock_final:,}  ({_pct(stock_final, recibidas):.1f}%)"))
    print(_fmt("  -> En cuarentena sin resolver al cierre", f"{stock_cuarentena:,}  ({_pct(stock_cuarentena, recibidas):.1f}%)"))
    print(_fmt("  -> Perdidas por frio", f"{perd_frio:,}  ({_pct(perd_frio, recibidas):.1f}%)"))
    print(_fmt("  -> Perdidas por vencimiento", f"{perd_venc:,}  ({_pct(perd_venc, recibidas):.1f}%)"))
    print(_fmt("  Cuadre (debe ser 0)", f"{cuadre:,}"))

    # ---------------- [2] INVENTARIO ----------------
    # Resumen del inventario: cuantos lotes entraron, cuanto stock queda
    # disponible, a cuantos dias de demanda equivale ese stock (cobertura)
    # y cuanto se perdio por cada causa. Se complementa con un desglose
    # de lotes agrupados por su estado actual (Disponible, Cuarentena,
    # Perdido, etc.).
    print("\n[2] INVENTARIO — que entro, que queda y que se perdio")
    print(_fmt("Lotes recibidos", f"{lotes:,}"))
    print(_fmt("Lotes que pasaron por cuarentena", f"{cuarentenas:,}"))
    print(_fmt("Unidades recibidas", f"{recibidas:,}"))
    print(_fmt("Stock final disponible", f"{stock_final:,}"))
    print(_fmt("Dias de cobertura del stock final", f"{cobertura:.1f} dias"))
    print(_fmt("Perdidas por frio", f"{perd_frio:,}"))
    print(_fmt("Perdidas por vencimiento", f"{perd_venc:,}"))
    print(_fmt("Perdida total (% de lo recibido)", f"{pct_perdida:.1f}%"))
    print("\n    Lotes por estado:")
    print(f"      {'Estado':<14}{'Lotes':>8}{'Unidades':>14}")
    for estado, n, uds in _filas(cursor,
            "SELECT estado, COUNT(*), ISNULL(SUM(cantidad_actual),0) FROM Lote GROUP BY estado ORDER BY estado"):
        print(f"      {estado:<14}{n:>8,}{uds:>14,}")

    # ---------------- [3] DEMANDA Y SERVICIO ----------------
    # Vision general de cuanto demandaron los hospitales (pedidos y
    # unidades solicitadas) frente a cuanto se les pudo atender, resumido
    # en el nivel de servicio (fill rate) y la demanda media diaria. Tambien
    # se muestra el desglose de pedidos por estado y cuantos siguen
    # abiertos (Pendiente o Parcial) al terminar la simulacion.
    print("\n[3] DEMANDA Y NIVEL DE SERVICIO — cuanto pidieron y cuanto se les dio")
    print(_fmt("Pedidos creados", f"{total_pedidos:,}"))
    print(_fmt("Unidades solicitadas", f"{solicitadas:,}"))
    print(_fmt("Unidades atendidas", f"{atendidas:,}"))
    print(_fmt("Unidades NO atendidas", f"{no_atendidas:,}"))
    print(_fmt("Nivel de servicio (fill rate)", f"{fill:.1f}%"))
    print(_fmt("Demanda media diaria", f"{tasa_demanda:,.0f} uds/dia"))
    print("    Pedidos por estado: " + ", ".join(f"{k}={v}" for k, v in sorted(por_estado_pedido.items())))
    if abiertos:
        print(f"    (quedan {abiertos} pedidos sin cerrar al fin de la simulacion)")

    # ---------------- [4] DEMANDA POR VACUNA ----------------
    # Mismo analisis de solicitado vs. atendido que la seccion [3], pero
    # desglosado por cada tipo de vacuna, para identificar si algun
    # producto en particular tiene un nivel de servicio mas bajo que el
    # promedio general.
    print("\n[4] DEMANDA POR VACUNA")
    print(f"    {'Vacuna':26s} {'Solicitado':>12s} {'Atendido':>12s} {'Falto':>10s} {'Fill':>8s}")
    for nombre, sol, ate in _filas(cursor,
            """SELECT V.nombre, ISNULL(SUM(DP.cantidad_solicitada),0), ISNULL(SUM(DP.cantidad_atendida),0)
               FROM DetallePedido DP JOIN Vacuna V ON V.id=DP.vacuna_id
               GROUP BY V.nombre ORDER BY V.nombre"""):
        print(f"    {nombre:26s} {sol:>12,} {ate:>12,} {sol-ate:>10,} {_pct(ate, sol):>7.1f}%")

    # ---------------- [5] CADENA DE FRIO ----------------
    # Estadisticas del comportamiento termico de la cadena: cuantas
    # lecturas de sensor se generaron, cuantas fallas ocurrieron y su
    # duracion media, los extremos de temperatura registrados, un
    # desglose de las fallas por tipo (con las unidades que cada tipo
    # llego a destruir) y la temperatura maxima alcanzada en cada camara.
    print("\n[5] CADENA DE FRIO — lecturas y fallas de temperatura")
    print(_fmt("Lecturas de temperatura", f"{lecturas:,}"))
    print(_fmt("Eventos de falla", f"{fallas:,}"))
    print(_fmt("Duracion media de una falla", f"{dur_media_falla:.0f} min"))
    print(_fmt("Temperatura maxima registrada", f"{temp_max:.1f} °C"))
    print(_fmt("Temperatura minima registrada", f"{temp_min:.1f} °C"))
    print("\n    Fallas por tipo y unidades que destruyeron:")
    print(f"      {'Tipo de falla':<20}{'Eventos':>9}{'Uds perdidas':>15}")
    for tipo, n, uds in _filas(cursor,
            """SELECT EF.tipo_falla, COUNT(PL.id), ISNULL(SUM(PL.cantidad_perdida),0)
               FROM PerdidaLote PL JOIN EventoFalla EF ON EF.id=PL.evento_falla_id
               GROUP BY EF.tipo_falla ORDER BY SUM(PL.cantidad_perdida) DESC"""):
        print(f"      {tipo:<20}{n:>9,}{uds:>15,}")
    print("\n    Temperatura maxima alcanzada por camara:")
    print(f"      {'Camara':<28}{'Lecturas':>12}{'Temp max':>10}")
    for ubi, n, tmax in _filas(cursor,
            """SELECT S.ubicacion, COUNT(L.id), MAX(L.temperatura)
               FROM LecturaTemperatura L JOIN Sensor S ON S.id=L.sensor_id
               GROUP BY S.ubicacion ORDER BY MAX(L.temperatura) DESC"""):
        print(f"      {ubi:<28}{n:>12,}{tmax:>9.1f}°")

    # ---------------- [6] CALIDAD / CUARENTENA ----------------
    # Muestra que hizo el proceso de calidad con los lotes que pasaron
    # por cuarentena: cuantos fueron liberados sin merma, cuantos
    # sufrieron un rechazo parcial y cuantos un rechazo total. Si no hay
    # ningun movimiento de cuarentena registrado, se asume que el
    # protocolo de cuarentena de frio.py no esta activo en esta corrida y
    # se informa que las fallas destruyen el lote completo.
    print("\n[6] CALIDAD Y CUARENTENA — que hizo calidad con lo afectado")
    if cuarentenas or liberados or rechazos_parciales or rechazos_totales:
        print(_fmt("Lotes puestos en cuarentena", f"{cuarentenas:,}"))
        print(_fmt("Liberados por calidad", f"{liberados:,}"))
        print(_fmt("Rechazos parciales", f"{rechazos_parciales:,}"))
        print(_fmt("Rechazos totales", f"{rechazos_totales:,}"))
    else:
        print("    Cuarentena NO activa: cada falla de frio destruye el lote COMPLETO.")
        print("    (Para activarla, aplica el protocolo de cuarentena en frio.py.)")

    # ---------------- [7] LOGISTICA ----------------
    # Indicadores de desempeno logistico: cuantas entregas se realizaron,
    # que porcentaje fueron puntuales o adelantadas, cuantas llegaron con
    # retraso y cual fue el retraso promedio (calculado solo sobre las
    # entregas que efectivamente se retrasaron).
    print("\n[7] LOGISTICA Y ENTREGAS — rapidez y puntualidad")
    print(_fmt("Entregas realizadas", f"{entregas:,}"))
    print(_fmt("Entregas puntuales o adelantadas", f"{entregas - retrasadas:,}  ({pct_puntuales:.1f}%)"))
    print(_fmt("Entregas con retraso", f"{retrasadas:,}"))
    print(_fmt("Retraso medio (solo retrasadas)", f"{retraso_medio:.1f} dias"))

    # ---------------- [8] DESABASTECIMIENTO ----------------
    # Reporta los eventos en los que un hospital no pudo recibir toda la
    # cantidad solicitada (o la recibio con demora fuera de tolerancia) y
    # el total de unidades que quedaron sin servir. Si hubo
    # desabastecimiento, se agrega el detalle de los hospitales mas
    # afectados y las vacunas con mayor faltante, para facilitar el
    # diagnostico de donde esta el cuello de botella.
    print("\n[8] DESABASTECIMIENTO — demanda que no se pudo servir")
    print(_fmt("Eventos de desabastecimiento", f"{desab:,}"))
    print(_fmt("Unidades faltantes", f"{faltantes:,}"))
    if desab:
        print("\n    Hospitales mas afectados:")
        print(f"      {'Hospital':<30}{'Eventos':>9}{'Uds faltantes':>15}")
        for h, n, u in _filas(cursor,
                """SELECT H.nombre, COUNT(D.id), ISNULL(SUM(D.cantidad_faltante),0)
                   FROM Desabastecimiento D JOIN Hospital H ON H.id=D.hospital_id
                   GROUP BY H.nombre ORDER BY SUM(D.cantidad_faltante) DESC"""):
            print(f"      {h:<30}{n:>9,}{u:>15,}")
        print("\n    Vacunas con mas faltante:")
        print(f"      {'Vacuna':<28}{'Eventos':>9}{'Uds faltantes':>15}")
        for v, n, u in _filas(cursor,
                """SELECT V.nombre, COUNT(D.id), ISNULL(SUM(D.cantidad_faltante),0)
                   FROM Desabastecimiento D JOIN Vacuna V ON V.id=D.vacuna_id
                   GROUP BY V.nombre ORDER BY SUM(D.cantidad_faltante) DESC"""):
            print(f"      {v:<28}{n:>9,}{u:>15,}")

    # ---------------- [9] VALORACION DE INVENTARIO (USD) ----------------
    # Traduce las cantidades fisicas de inventario a valor monetario,
    # usando el costo_unitario (para inversion/perdidas/stock) y el
    # precio_unitario (para lo efectivamente entregado a hospitales) de
    # cada vacuna, definidos en catalogo.VACUNAS:
    #   - inv_costo: valor total invertido en comprar todos los lotes
    #     recibidos (cantidad_inicial * costo_unitario).
    #   - serv_costo / serv_precio: costo y precio de venta de lo que
    #     realmente se entrego a los hospitales (Entrega.cantidad_entregada).
    #   - frio_usd / venc_usd: valor (a costo) de las unidades perdidas
    #     por fallas de frio y por vencimiento, respectivamente.
    #   - stock_usd: valor (a costo) del stock que quedo disponible al
    #     cierre de la simulacion.
    #   - margen_bruto: diferencia entre lo facturado (precio) y su costo
    #     por las unidades efectivamente entregadas.
    inv_costo = _uno(cursor, "SELECT ISNULL(SUM(L.cantidad_inicial * V.costo_unitario),0) FROM Lote L JOIN Vacuna V ON V.id=L.vacuna_id")
    serv_costo = _uno(cursor, "SELECT ISNULL(SUM(E.cantidad_entregada * V.costo_unitario),0) FROM Entrega E JOIN Lote L ON L.id=E.lote_id JOIN Vacuna V ON V.id=L.vacuna_id")
    serv_precio = _uno(cursor, "SELECT ISNULL(SUM(E.cantidad_entregada * V.precio_unitario),0) FROM Entrega E JOIN Lote L ON L.id=E.lote_id JOIN Vacuna V ON V.id=L.vacuna_id")
    frio_usd = _uno(cursor, "SELECT ISNULL(SUM(PL.cantidad_perdida * V.costo_unitario),0) FROM PerdidaLote PL JOIN Lote L ON L.id=PL.lote_id JOIN Vacuna V ON V.id=L.vacuna_id WHERE PL.evento_falla_id IS NOT NULL")
    venc_usd = _uno(cursor, "SELECT ISNULL(SUM(PL.cantidad_perdida * V.costo_unitario),0) FROM PerdidaLote PL JOIN Lote L ON L.id=PL.lote_id JOIN Vacuna V ON V.id=L.vacuna_id WHERE PL.evento_falla_id IS NULL")
    stock_usd = _uno(cursor, "SELECT ISNULL(SUM(L.cantidad_actual * V.costo_unitario),0) FROM Lote L JOIN Vacuna V ON V.id=L.vacuna_id WHERE L.estado='Disponible'")
    perd_usd = frio_usd + venc_usd
    pct_perd_usd = _pct(perd_usd, inv_costo)
    margen_bruto = serv_precio - serv_costo

    print("\n[9] VALORACION DE INVENTARIO (USD)")
    print(_li("Inversión total (compra de lotes)", _usd(inv_costo)))
    print(_li("Costo de lo entregado", _usd(serv_costo)))
    print(_li("Pérdida por frío (merma)", _usd(frio_usd)))
    print(_li("Pérdida por vencimiento (merma)", _usd(venc_usd)))
    print(_li("Pérdida total en USD", _usd(perd_usd)))
    print(_li("Pérdida total (% de la inversión)", f"{pct_perd_usd:.1f}%"))
    print(_li("Valor del stock final", _usd(stock_usd)))

    # ---------------- [10] COSTOS OPERATIVOS (USD) ----------------
    # Calcula los costos operativos de la cadena (independientes del
    # valor de las vacunas en si), usando las tarifas definidas en
    # catalogo.COSTOS_OPERATIVOS y aplicando el multiplicador de
    # escenario "costos_operativos_mult" (ESCENARIO):
    #   - almac_usd: costo de almacenamiento acumulado dia a dia, ya
    #     calculado previamente por costos.py y guardado en la tabla
    #     CostoOperativo (categoria 'Almacenamiento'); aqui solo se suma y
    #     se aplica el multiplicador del escenario.
    #   - transporte_usd: costo fijo por lote recibido, multiplicado por
    #     la cantidad total de lotes.
    #   - distribucion_usd: costo por cada dosis efectivamente entregada.
    #   - disposicion_usd: costo por cada dosis perdida (frio + vencimiento).
    #   - cuarentena_usd: costo fijo por cada lote que paso por cuarentena.
    #   - costos_op_usd: suma de los cinco conceptos anteriores.
    mult = ESCENARIO.get("costos_operativos_mult", 1.0)
    co = COSTOS_OPERATIVOS
    almac_usd        = _uno(cursor, "SELECT ISNULL(SUM(monto),0) FROM CostoOperativo WHERE categoria='Almacenamiento'") * mult
    transporte_usd   = lotes * co["transporte_por_lote"] * mult
    distribucion_usd = atendidas * co["distribucion_por_dosis"] * mult
    disposicion_usd  = (perd_frio + perd_venc) * co["disposicion_por_dosis"] * mult
    cuarentena_usd   = cuarentenas * co["cuarentena_por_lote"] * mult
    costos_op_usd    = almac_usd + transporte_usd + distribucion_usd + disposicion_usd + cuarentena_usd

    print("\n[10] COSTOS OPERATIVOS (USD)")
    print(_li("Almacenamiento (dosis-día)", _usd(almac_usd)))
    print(_li("Transporte de entrada (por lote)", _usd(transporte_usd)))
    print(_li("Distribución (por dosis entregada)", _usd(distribucion_usd)))
    print(_li("Disposición de mermas", _usd(disposicion_usd)))
    print(_li("Cuarentena / calidad", _usd(cuarentena_usd)))
    print(_li("TOTAL costos operativos", _usd(costos_op_usd)))

    # ---------------- [11] RESULTADO ECONOMICO (USD) ----------------
    # Arma un estado de resultados simplificado, encadenando las cifras
    # calculadas en las secciones [9] y [10]:
    #   ingresos            = valor de venta de lo entregado (a precio)
    #   costo_vendido       = costo de lo entregado (a costo)
    #   margen_bruto        = ingresos - costo_vendido (ya calculado arriba)
    #   resultado_operativo = margen_bruto - costos operativos totales
    #   resultado_final     = resultado_operativo - perdidas por mermas (a costo)
    ingresos            = serv_precio
    costo_vendido       = serv_costo
    resultado_operativo = margen_bruto - costos_op_usd
    resultado_final     = resultado_operativo - perd_usd

    print("\n[11] RESULTADO ECONOMICO (USD)")
    print(_li("Ingresos (entregas a precio)", _usd(ingresos)))
    print(_li("(-) Costo de lo vendido", _usd(costo_vendido)))
    print(_li("= Margen bruto", _usd(margen_bruto)))
    print(_li("(-) Costos operativos", _usd(costos_op_usd)))
    print(_li("= Resultado operativo", _usd(resultado_operativo)))
    print(_li("(-) Pérdida por mermas (a costo)", _usd(perd_usd)))
    print(_li("= RESULTADO FINAL", _usd(resultado_final)))

    # ---------------- DIAGNOSTICO ----------------
    # Clasifica el desempeno general de la cadena en una de cuatro
    # categorias, en funcion del fill rate y de si hubo o no eventos de
    # desabastecimiento:
    #   - EXCELENTE: fill rate >= 97% y cero desabastecimiento.
    #   - BUENA:     fill rate >= 90% (con o sin desabastecimiento leve).
    #   - DEGRADADA: fill rate >= 75%.
    #   - CRITICA:   fill rate por debajo de 75%.
    if fill >= 97 and desab == 0:
        estado, msg = "EXCELENTE", "la cadena cubre la demanda sin desabastecimiento."
    elif fill >= 90:
        estado, msg = "BUENA", "servicio aceptable; vigila pérdidas y vencimientos."
    elif fill >= 75:
        estado, msg = "DEGRADADA", "desabastecimiento recurrente; revisar parámetros."
    else:
        estado, msg = "CRITICA", "la cadena no cubre la demanda; intervenir ya."

    print(f"\n  DIAGNOSTICO: {estado} — {msg}")

    # Genera una lista de alertas concretas, cada una activada por una
    # condicion especifica sobre los indicadores ya calculados, y sugiere
    # que parametro del ESCENARIO ajustar para corregir el problema
    # detectado:
    #   - Vencimientos > 5% de lo recibido: sugiere sobre-oferta.
    #   - Perdidas por frio > 3% de lo recibido: sugiere revisar fallas.
    #   - Cualquier desabastecimiento: sugiere subir la oferta.
    #   - Cobertura de stock > 90 dias: sugiere exceso de stock acumulado.
    #   - Mas del 10% de entregas retrasadas: alerta de puntualidad.
    #   - Resultado final negativo: alerta de perdida economica.
    alertas = []
    if _pct(perd_venc, recibidas) > 5:
        alertas.append(f"Vencimientos altos ({perd_venc:,} uds, {_pct(perd_venc, recibidas):.1f}%): sobre-oferta. "
                       f"Baja 'multiplicador_oferta' o sube 'multiplicador_demanda'.")
    if _pct(perd_frio, recibidas) > 3:
        alertas.append(f"Pérdidas por frío ({perd_frio:,} uds, {_pct(perd_frio, recibidas):.1f}%): "
                       f"baja 'prob_falla_diaria'/'multiplicador_severidad' o activa la cuarentena.")
    if desab > 0:
        alertas.append(f"{desab} eventos de desabastecimiento ({faltantes:,} uds sin servir): "
                       f"falta stock. Sube 'multiplicador_oferta'.")
    if cobertura > 90:
        alertas.append(f"Stock final muy alto ({cobertura:.0f} días de cobertura): se acumula y caducará. "
                       f"Baja 'multiplicador_oferta'.")
    if retrasadas and _pct(retrasadas, entregas) > 10:
        alertas.append(f"{_pct(retrasadas, entregas):.0f}% de entregas con retraso.")
    if resultado_final < 0:
        alertas.append(f"Resultado final negativo ({_usd(resultado_final)}): la operación pierde dinero.")

    if alertas:
        print("  FOCOS DE ATENCION:")
        for a in alertas:
            print(f"    - {a}")
    else:
        print("  Sin alertas destacables.")
    print(linea)