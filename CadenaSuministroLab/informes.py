from decimal import Decimal

from config import ESCENARIO
from catalogo import COSTOS_OPERATIVOS


def _uno(cursor, sql):
    cursor.execute(sql)
    valor = cursor.fetchone()[0]
    return float(valor) if isinstance(valor, Decimal) else valor


def _filas(cursor, sql):
    cursor.execute(sql)
    return cursor.fetchall()


def _pct(parte, total):
    return (parte / total * 100.0) if total else 0.0


def _fmt(label, valor, width=46):
    puntos = "." * max(2, width - len(label))
    return f"    {label} {puntos} {valor}"


def _usd(x):
    return f"${x:,.2f}"


def _li(label, valor, ancho=54):
    return f"    {label} {'.' * max(2, ancho - len(label))} {valor}"


def generar(cursor, modo, dias):
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

    cuarentenas = _uno(cursor, "SELECT COUNT(DISTINCT lote_id) FROM MovimientoInventario "
                               "WHERE tipo='Ajuste' AND referencia LIKE 'Cuarentena preventiva%'")
    liberados = _uno(cursor, "SELECT COUNT(*) FROM MovimientoInventario "
                             "WHERE tipo='Ajuste' AND referencia LIKE 'Liberado%'")
    rechazos_parciales = _uno(cursor, "SELECT COUNT(*) FROM PerdidaLote WHERE motivo LIKE 'Rechazo parcial%'")
    rechazos_totales = _uno(cursor, "SELECT COUNT(*) FROM PerdidaLote WHERE motivo LIKE 'Rechazo total%'")

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

    print("\n[1] BALANCE DE MASAS — cada unidad recibida termina en un solo sitio")
    print(_fmt("Unidades recibidas (100%)", f"{recibidas:,}"))
    print(_fmt("  -> Entregadas a hospitales", f"{atendidas:,}  ({_pct(atendidas, recibidas):.1f}%)"))
    print(_fmt("  -> Stock final disponible", f"{stock_final:,}  ({_pct(stock_final, recibidas):.1f}%)"))
    print(_fmt("  -> En cuarentena sin resolver al cierre", f"{stock_cuarentena:,}  ({_pct(stock_cuarentena, recibidas):.1f}%)"))
    print(_fmt("  -> Perdidas por frio", f"{perd_frio:,}  ({_pct(perd_frio, recibidas):.1f}%)"))
    print(_fmt("  -> Perdidas por vencimiento", f"{perd_venc:,}  ({_pct(perd_venc, recibidas):.1f}%)"))
    print(_fmt("  Cuadre (debe ser 0)", f"{cuadre:,}"))

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

    print("\n[4] DEMANDA POR VACUNA")
    print(f"    {'Vacuna':26s} {'Solicitado':>12s} {'Atendido':>12s} {'Falto':>10s} {'Fill':>8s}")
    for nombre, sol, ate in _filas(cursor,
            """SELECT V.nombre, ISNULL(SUM(DP.cantidad_solicitada),0), ISNULL(SUM(DP.cantidad_atendida),0)
               FROM DetallePedido DP JOIN Vacuna V ON V.id=DP.vacuna_id
               GROUP BY V.nombre ORDER BY V.nombre"""):
        print(f"    {nombre:26s} {sol:>12,} {ate:>12,} {sol-ate:>10,} {_pct(ate, sol):>7.1f}%")

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

    print("\n[6] CALIDAD Y CUARENTENA — que hizo calidad con lo afectado")
    if cuarentenas or liberados or rechazos_parciales or rechazos_totales:
        print(_fmt("Lotes puestos en cuarentena", f"{cuarentenas:,}"))
        print(_fmt("Liberados por calidad", f"{liberados:,}"))
        print(_fmt("Rechazos parciales", f"{rechazos_parciales:,}"))
        print(_fmt("Rechazos totales", f"{rechazos_totales:,}"))
    else:
        print("    Cuarentena NO activa: cada falla de frio destruye el lote COMPLETO.")
        print("    (Para activarla, aplica el protocolo de cuarentena en frio.py.)")

    print("\n[7] LOGISTICA Y ENTREGAS — rapidez y puntualidad")
    print(_fmt("Entregas realizadas", f"{entregas:,}"))
    print(_fmt("Entregas puntuales o adelantadas", f"{entregas - retrasadas:,}  ({pct_puntuales:.1f}%)"))
    print(_fmt("Entregas con retraso", f"{retrasadas:,}"))
    print(_fmt("Retraso medio (solo retrasadas)", f"{retraso_medio:.1f} dias"))

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

    if fill >= 97 and desab == 0:
        estado, msg = "EXCELENTE", "la cadena cubre la demanda sin desabastecimiento."
    elif fill >= 90:
        estado, msg = "BUENA", "servicio aceptable; vigila pérdidas y vencimientos."
    elif fill >= 75:
        estado, msg = "DEGRADADA", "desabastecimiento recurrente; revisar parámetros."
    else:
        estado, msg = "CRITICA", "la cadena no cubre la demanda; intervenir ya."

    print(f"\n  DIAGNOSTICO: {estado} — {msg}")

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