# solo_informe.py
#
# Script utilitario para regenerar (reimprimir) el informe final sobre
# los datos que ya existen en la base de datos, sin volver a correr la
# simulacion completa. Util cuando se quiere revisar de nuevo el reporte
# de una corrida ya realizada, sin tener que ejecutar run_all.py otra vez.
#
# Author: Ing. G. Alfonso Vargas Solís
# Email:  alfonso.vargas.solis@gmail.com
# GitHub: alfonsovso
import config
import informes

# Abre la conexion a la base de datos (usando la configuracion definida
# en config.DB_CONFIG) y obtiene un cursor para consultarla.
conn = config.get_connection()
cursor = conn.cursor()

# Genera e imprime por consola el informe completo de indicadores (KPI),
# etiquetandolo con el modo "normal" y usando la duracion total de
# simulacion definida por defecto en config.DIAS_SIMULACION. Nota: si la
# base de datos contiene datos de una corrida hecha con otro modo o con
# otra cantidad de dias, este encabezado ("normal", DIAS_SIMULACION) es
# solo una etiqueta informativa y no afecta el calculo de los indicadores,
# que se basan enteramente en lo que haya almacenado en la BD.
informes.generar(cursor, "normal", config.DIAS_SIMULACION)

# Cierra la conexion a la base de datos; este script no modifica datos,
# por lo que no hace falta hacer commit.
conn.close()