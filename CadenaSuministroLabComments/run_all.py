"""
run_all.py — Orquestador unico de la simulacion (reemplaza a los tres
scripts viejos). Cada dia simulado ejecuta, en orden:
  1) llegada de lotes  2) vencimientos  3) cadena de frio (lecturas/fallas)
  4) creacion de pedidos  5) despacho por prioridad/FEFO  6) cancelaciones.

Uso:
    python run_all.py                              # escenario normal
    python run_all.py --modo estres --reset
    python run_all.py --modo critico --reset
    python run_all.py --reset --set prob_falla_diaria=0.05 --set multiplicador_demanda=1.8

Author: Ing. G. Alfonso Vargas Solís
Email:  alfonso.vargas.solis@gmail.com
GitHub: alfonsovso
"""
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

# Orden de borrado seguro respecto a las FK (hijos antes que padres).
# Las tablas "transaccionales" son las que se generan durante la
# simulacion (lotes, pedidos, entregas, fallas, etc.); se listan de modo
# que cada tabla se borre despues de las que dependen de ella.
TABLAS_TRANSACCIONALES = [
    "MovimientoInventario", "PerdidaLote", "Entrega", "EventoFalla",
    "LecturaTemperatura", "Desabastecimiento", "DetallePedido", "Pedido", "Lote",
]
# Tablas "estaticas": datos de referencia/catalogo (sensores, vacunas,
# hospitales, proveedores) que normalmente se siembran una sola vez y
# solo se borran si se pide un reset total.
TABLAS_ESTATICAS = ["Sensor", "Vacuna", "Hospital", "Proveedor"]


def hay_datos(cursor):
    """
    Indica si ya existen datos de una simulacion previa en la base de
    datos, usando la cantidad de filas en la tabla Lote como indicador:
    si hay al menos un lote registrado, se asume que ya se corrio una
    simulacion antes.
    """
    cursor.execute("SELECT COUNT(*) FROM Lote")
    return cursor.fetchone()[0] > 0


def limpiar(cursor, total=False):
    """
    Borra los datos generados por una simulacion previa.

    Siempre borra el contenido de todas las TABLAS_TRANSACCIONALES, en el
    orden definido en esa lista (para respetar las dependencias de llave
    foranea sin necesidad de desactivar restricciones). Si "total" es
    True, ademas borra las TABLAS_ESTATICAS (catalogo de sensores,
    vacunas, hospitales y proveedores), que luego deberan volver a
    sembrarse con seed_estaticos.ejecutar().

    Parametros:
        cursor: cursor de base de datos usado para ejecutar los DELETE.
        total: si es True, tambien borra las tablas de datos estaticos;
            por defecto (False) solo borra las tablas transaccionales.
    """
    for tabla in TABLAS_TRANSACCIONALES:
        cursor.execute(f"DELETE FROM {tabla}")
    if total:
        for tabla in TABLAS_ESTATICAS:
            cursor.execute(f"DELETE FROM {tabla}")


def aplicar_override(pares):
    """
    Aplica ajustes --set CLAVE=VALOR sobre config.ESCENARIO.

    Recorre la lista de cadenas "CLAVE=VALOR" recibidas por la linea de
    comandos (argumento --set, que puede repetirse) y, para cada una:
      - Separa la clave y el valor usando el primer signo "=" encontrado.
      - Verifica que la clave exista en config.ESCENARIO; si no, termina
        la ejecucion (SystemExit) mostrando la lista de claves validas.
      - Convierte el valor de texto al mismo tipo de dato que tenia
        actualmente ese parametro en ESCENARIO (por ejemplo, float, int),
        usando type(actual)(valor); si la conversion falla (ValueError),
        termina la ejecucion indicando el tipo esperado.
      - Si todo es valido, sobreescribe config.ESCENARIO[clave] con el
        nuevo valor convertido.

    Parametros:
        pares: lista de strings con el formato "CLAVE=VALOR" (o None/lista
            vacia si no se paso ningun --set), tal como los entrega
            argparse con action="append".

    No retorna ningun valor; su efecto es modificar en el lugar el
    diccionario config.ESCENARIO.
    """
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
    """
    Carga los ids reales de la BD (sin asumir 1..N en ningun orden).

    Consulta la base de datos para construir todos los mapeos de nombres
    (definidos en el catalogo en memoria) hacia los identificadores
    reales asignados por la base de datos, necesarios para el resto de la
    simulacion:
      - "vacunas": nombre de vacuna -> id en la tabla Vacuna.
      - "vida_util": nombre de vacuna -> vida_util_dias (para calcular
        fechas de caducidad al registrar lotes).
      - "proveedores": nombre de proveedor -> id en la tabla Proveedor.
      - "hospitales": lista de ids de hospitales marcados como activos
        (activo = 1).
      - "sensores": diccionario {sensor_id: info} tal como lo retorna
        frio.cargar_sensores().
      - "sensor_por_vacuna": nombre de vacuna -> id del sensor de la
        camara donde debe almacenarse esa vacuna, resuelto combinando
        VACUNA_UBICACION (del catalogo) con el mapeo ubicacion -> sensor
        construido a partir de "sensores".
      - "vacuna_ids": lista simple de todos los ids de vacuna (valores de
        "vacunas"), usada para elegir vacunas al azar al generar pedidos.

    Parametros:
        cursor: cursor de base de datos usado para todas las consultas.

    Retorna:
        dict: diccionario con las claves descritas arriba, usado como
        "ids" en el resto de las funciones del motor de simulacion.
    """
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
    """
    Punto de entrada del orquestador: parsea los argumentos de linea de
    comandos, prepara la base de datos y el escenario, y ejecuta la
    simulacion dia a dia hasta generar el informe final.

    Flujo general:
      1. Define y parsea los argumentos de linea de comandos: --modo
         (preset de escenario), --dias (duracion), --semilla
         (reproducibilidad), --reset / --reset-total (limpieza previa de
         datos) y --set (ajustes puntuales de parametros del escenario).
      2. Aplica el preset elegido (config.aplicar_preset) y luego
         cualquier override individual pasado con --set
         (aplicar_override), de modo que los --set tienen la ultima
         palabra sobre los valores del preset.
      3. Abre la conexion a la base de datos y revisa si ya hay datos de
         una simulacion previa (hay_datos): si los hay, exige que se haya
         pasado --reset o --reset-total (si no, aborta con un mensaje de
         error); si se pidio reset, limpia los datos correspondientes. Si
         no habia datos pero se pidio --reset-total, tambien limpia por
         si acaso (para dejar las tablas estaticas en un estado
         conocido antes de volver a sembrarlas).
      4. Crea el generador de numeros aleatorios con la semilla indicada
         (para reproducibilidad) y siembra los datos estaticos del
         catalogo (seed_estaticos.ejecutar), confirmando los cambios.
      5. Carga los ids reales de la BD (cargar_ids) y planifica el
         calendario completo de llegadas de lotes para toda la
         simulacion (lotes.planificar), organizandolo en un diccionario
         "llegadas" indexado por dia (defaultdict(list)) para acceso
         rapido durante el bucle diario.
      6. Ejecuta el bucle principal de simulacion, un dia a la vez, desde
         0 hasta args.dias - 1:
            a. Registra en la BD los lotes que llegan hoy
               (lotes.registrar_llegadas).
            b. Procesa los lotes que caducaron hoy (pedidos.procesar_vencimientos).
            c. Simula la cadena de frio del dia: lecturas normales y
               posibles fallas (frio.simular_dia).
            d. Genera los pedidos que hacen los hospitales hoy
               (pedidos.crear_pedidos), agregandolos a la lista
               "pendientes".
            e. Ordena los pedidos pendientes por prioridad (segun
               pedidos.PRIORIDAD_ORDEN) y, dentro de la misma prioridad,
               por fecha requerida mas cercana primero, e intenta
               cumplir cada uno en ese orden (pedidos.intentar_cumplir),
               que a su vez despacha los lotes en orden FEFO.
            f. Depura la lista de pendientes: descarta los ya atendidos y
               cancela (registrando desabastecimiento) los que superaron
               el plazo maximo de espera (pedidos.depurar).
            g. Acumula el costo de almacenamiento del dia
               (costos.acumular_almacenamiento).
            h. Cada 30 dias (dia % 30 == 0) o en el ultimo dia de la
               simulacion, confirma (commit) los cambios acumulados y
               imprime una linea de progreso con estadisticas parciales
               (fallas, perdidas por frio, vencidos y pendientes).
         Si ocurre cualquier excepcion durante el bucle, se revierte
         (rollback) la transaccion antes de relanzar la excepcion, para
         no dejar la base de datos en un estado parcialmente
         inconsistente.
      7. Al terminar el bucle sin errores, confirma los ultimos cambios,
         genera e imprime el informe final (informes.generar) y cierra la
         conexion a la base de datos.

    No recibe parametros explicitos (los toma de sys.argv via argparse) y
    no retorna ningun valor.
    """
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

    # Se aplica primero el preset elegido y luego los overrides puntuales
    # de --set, de modo que estos ultimos prevalecen sobre el preset.
    config.aplicar_preset(args.modo)
    aplicar_override(args.set)

    conn = config.get_connection()
    cursor = conn.cursor()

    if hay_datos(cursor):
        # Ya hay una simulacion previa en la BD: se exige --reset o
        # --reset-total explicito para evitar sobrescribir datos sin
        # querer.
        if args.reset or args.reset_total:
            limpiar(cursor, total=args.reset_total)
            conn.commit()
            print("Datos anteriores borrados.")
        else:
            raise SystemExit("Ya hay datos simulados en la BD. Usa --reset (o --reset-total).")
    elif args.reset_total:
        # No habia datos transaccionales, pero se pidio reset total de
        # todos modos: se limpian tambien las tablas estaticas para
        # partir de un estado conocido antes de volver a sembrarlas.
        limpiar(cursor, total=True)
        conn.commit()

    # Generador de aleatoriedad con semilla fija: garantiza que, con los
    # mismos parametros, la simulacion sea reproducible.
    rng = random.Random(args.semilla)
    seed_estaticos.ejecutar(cursor)
    conn.commit()

    ids = cargar_ids(cursor)
    # Se planifica de una sola vez el calendario completo de llegadas de
    # lotes para toda la simulacion, y se organiza por dia para poder
    # consultarlo rapidamente en cada iteracion del bucle diario.
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

            # 1) Llegada de lotes planificados para hoy.
            lotes.registrar_llegadas(cursor, llegadas.get(dia, []), ids, rng)
            # 2) Vencimientos: lotes que caducaron sin usarse.
            vencidos = pedidos.procesar_vencimientos(cursor, hoy)
            # 3) Cadena de frio: lecturas normales y posibles fallas del dia.
            stats_frio = frio.simular_dia(cursor, ids["sensores"], config.ESCENARIO, rng, hoy)
            # 4) Nuevos pedidos generados hoy por los hospitales.
            pedidos.crear_pedidos(cursor, ids["hospitales"], ids["vacuna_ids"],
                                  config.ESCENARIO, rng, hoy, pendientes)

            # 5) Despacho: primero los pedidos mas urgentes; dentro de la
            # misma prioridad, los que vencen (fecha requerida) antes.
            pendientes.sort(key=lambda p: (pedidos.PRIORIDAD_ORDEN[p["prioridad"]],
                                           p["fecha_requerida"]))
            for p in pendientes:
                pedidos.intentar_cumplir(cursor, p, hoy)
            # 6) Depuracion: se quitan los ya atendidos y se cancelan
            # (con registro de desabastecimiento) los que superaron la
            # espera maxima permitida.
            pendientes = pedidos.depurar(cursor, pendientes, hoy, config.ESCENARIO)

            # Costo de almacenamiento del stock activo durante este dia.
            costos.acumular_almacenamiento(cursor, hoy)

            # Cada 30 dias (o en el ultimo dia) se confirma la transaccion
            # y se imprime una linea de progreso con estadisticas parciales.
            if dia % 30 == 0 or dia == args.dias - 1:
                conn.commit()
                print(f"Dia {dia:4d} | fallas={stats_frio['fallas']} "
                      f"perdidas_frio={stats_frio['unidades_perdidas']} "
                      f"vencidos={vencidos} pendientes={len(pendientes)}")
    except Exception:
        # Ante cualquier error durante la simulacion, se revierte la
        # transaccion antes de relanzar la excepcion, para no dejar la
        # base de datos en un estado parcialmente inconsistente.
        conn.rollback()
        raise

    # Simulacion completada sin errores: se confirma todo, se genera el
    # informe final y se cierra la conexion.
    conn.commit()
    informes.generar(cursor, args.modo, args.dias)
    conn.close()


if __name__ == "__main__":
    main()