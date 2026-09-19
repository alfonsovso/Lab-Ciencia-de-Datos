import config
import informes

conn = config.get_connection()
cursor = conn.cursor()

informes.generar(cursor, "normal", config.DIAS_SIMULACION)

conn.close()