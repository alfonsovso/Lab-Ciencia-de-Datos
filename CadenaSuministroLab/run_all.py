import argparse
import random
from collections import defaultdict
from datetime import timedelta

import config
import frio
import informes
import lotes
import pedidos
import seed_estaticos
import costos
from catalogo import VACUNA_UBICACION

TABLAS_TRANSACCIONALES = [
    "MovimientoInventario", "PerdidaLote", "Entrega", "EventoFalla",
    "LecturaTemperatura", "Desabastecimiento", "DetallePedido", "Pedido", "Lote",
]
TABLAS_ESTATICAS = ["Sensor", "Vacuna", "Hospital", "Proveedor"]


def hay_datos(cursor):
    cursor.execute("SELECT COUNT(*) FROM Lote")
    return cursor.fetchone()[0] > 0


def limpiar(cursor, total=False):
    for tabla in TABLAS_TRANSACCIONALES:
        cursor.execute(f"DELETE FROM {tabla}")
    if total:
        for tabla in TABLAS_ESTATICAS:
            cursor.execute(f"DELETE FROM {tabla}")


def aplicar_override(pares):
    for kv in pares or []:
        clave, _, valor = kv.partition("=")
        if clave not in config.ESCENARIO:
            validas = ", ".join(sorted(config.ESCENARIO))
            raise SystemExit(f"--set: parametro desconocido '{clave}'. Validos: {validas}")
        actual = config.ESCENARIO[clave]
        try:
            config.ESCENARIO[clave] = type(actual)(valor)
        except ValueError:
            raise SystemExit(
                f"--set: '{valor}' no es valido para '{clave}' "
                f"(se esperaba {type(actual).__name__})"
            )


def cargar_ids(cursor):
    cursor.execute("SELECT id, nombre, vida_util_dias FROM Vacuna")
    filas = cursor.fetchall()
    vacunas = {nombre: vid for vid, nombre, _ in filas}
    vida_util = {nombre: vida for _, nombre, vida in filas}

    cursor.execute("SELECT id, nombre FROM Proveedor")
    proveedores = {nombre: pid for pid, nombre in cursor.fetchall()}

    cursor.execute("SELECT id FROM Hospital WHERE activo = 1")
    hospitales = [f[0] for f in cursor.fetchall()]

    sensores = frio.cargar_sensores(cursor)
    sensor_por_ubicacion = {info["ubicacion"]: sid for sid, info in sensores.items()}
    sensor_por_vacuna = {v: sensor_por_ubicacion[VACUNA_UBICACION[v]] for v in vacunas}

    return {
        "vacunas": vacunas,
        "vida_util": vida_util,
        "proveedores": proveedores,
        "hospitales": hospitales,
        "sensores": sensores,
        "sensor_por_vacuna": sensor_por_vacuna,
        "vacuna_ids": list(vacunas.values()),
    }


def main():
    ap = argparse.ArgumentParser(description="Simulador de cadena de frio")
    ap.add_argument("--modo", choices=sorted(config.PRESETS), default="normal",
                    help="preset de escenario (normal, estres, critico)")
    ap.add_argument("--dias", type=int, default=config.DIAS_SIMULACION)
    ap.add_argument("--semilla", type=int, default=config.SEMILLA,
                    help="misma semilla => resultados reproducibles")
    ap.add_argument("--reset", action="store_true",
                    help="borra los datos simulados y vuelve a ejecutar")
    ap.add_argument("--reset-total", action="store_true",
                    help="borra tambien los datos fijos (se vuelven a sembrar)")
    ap.add_argument("--set", action="append", metavar="CLAVE=VALOR",
                    help="ajusta un parametro, ej. --set prob_falla_diaria=0.05")
    args = ap.parse_args()

    config.aplicar_preset(args.modo)
    aplicar_override(args.set)

    conn = config.get_connection()
    cursor = conn.cursor()

    if hay_datos(cursor):
        if args.reset or args.reset_total:
            limpiar(cursor, total=args.reset_total)
            conn.commit()
            print("Datos anteriores borrados.")
        else:
            raise SystemExit("Ya hay datos simulados en la BD. Usa --reset (o --reset-total).")
    elif args.reset_total:
        limpiar(cursor, total=True)
        conn.commit()

    rng = random.Random(args.semilla)
    seed_estaticos.ejecutar(cursor)
    conn.commit()

    ids = cargar_ids(cursor)
    plan = lotes.planificar(config.ESCENARIO, rng, args.dias, config.FECHA_INICIO)
    llegadas = defaultdict(list)
    for item in plan:
        llegadas[item["dia"]].append(item)

    print(f"Modo: {args.modo} | Dias: {args.dias} | Semilla: {args.semilla} "
          f"| Lotes planificados: {len(plan)}")

    pendientes = []
    try:
        for dia in range(args.dias):
            hoy = config.FECHA_INICIO + timedelta(days=dia)

            lotes.registrar_llegadas(cursor, llegadas.get(dia, []), ids, rng)
            vencidos = pedidos.procesar_vencimientos(cursor, hoy)
            stats_frio = frio.simular_dia(cursor, ids["sensores"], config.ESCENARIO, rng, hoy)
            pedidos.crear_pedidos(cursor, ids["hospitales"], ids["vacuna_ids"],
                                  config.ESCENARIO, rng, hoy, pendientes)

            pendientes.sort(key=lambda p: (pedidos.PRIORIDAD_ORDEN[p["prioridad"]],
                                           p["fecha_requerida"]))
            for p in pendientes:
                pedidos.intentar_cumplir(cursor, p, hoy)
            pendientes = pedidos.depurar(cursor, pendientes, hoy, config.ESCENARIO)

            costos.acumular_almacenamiento(cursor, hoy)

            if dia % 30 == 0 or dia == args.dias - 1:
                conn.commit()
                print(f"Dia {dia:4d} | fallas={stats_frio['fallas']} "
                      f"perdidas_frio={stats_frio['unidades_perdidas']} "
                      f"vencidos={vencidos} pendientes={len(pendientes)}")
    except Exception:
        conn.rollback()
        raise

    conn.commit()
    informes.generar(cursor, args.modo, args.dias)
    conn.close()


if __name__ == "__main__":
    main()