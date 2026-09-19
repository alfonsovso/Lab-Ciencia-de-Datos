"""
limpia_datos.py — Script utilitario de limpieza de datos dinamicos.

Borra por completo el contenido de las tablas "dinamicas" (las que se
llenan durante la ejecucion de la simulacion: movimientos, pedidos,
entregas, perdidas, fallas, lecturas y costos operativos) y reinicia sus
contadores de identidad (IDENTITY) a 0, dejando la base de datos lista
para correr una simulacion nueva desde cero, sin tener que recrear el
esquema ni los datos estaticos del catalogo (vacunas, hospitales,
proveedores, sensores, etc.).

Author: Ing. G. Alfonso Vargas Solís
Email:  alfonso.vargas.solis@gmail.com
GitHub: alfonsovso
"""
from config import get_connection

# Se abre una conexion a la base de datos y se obtiene un cursor para
# ejecutar el script de limpieza.
conn = get_connection(); cur = conn.cursor()

# Script SQL de limpieza, ejecutado como un solo batch:
#   1. Desactiva temporalmente TODAS las restricciones de llave foranea
#      de TODAS las tablas (sp_MSforeachtable + NOCHECK CONSTRAINT ALL),
#      para poder borrar las tablas sin que el orden de los DELETE choque
#      con las dependencias entre ellas.
#   2. Borra el contenido completo de cada tabla dinamica, en un orden
#      que respeta (por prudencia) las dependencias logicas entre ellas:
#      primero las tablas que dependen de Lote/Pedido (movimientos,
#      desabastecimiento, perdidas, fallas, lecturas, entregas, detalle
#      de pedido, costos operativos), y al final Pedido y Lote.
#   3. Reinicia el contador IDENTITY de cada una de esas tablas a 0
#      (DBCC CHECKIDENT ... RESEED, 0), de modo que la proxima fila
#      insertada en cada tabla vuelva a arrancar desde el id 1.
#   4. Reactiva todas las restricciones de llave foranea que se habian
#      desactivado en el paso 1 (CHECK CONSTRAINT ALL), dejando la base
#      de datos con su integridad referencial normal.
cur.execute("""
EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL';
DELETE FROM MovimientoInventario;
DELETE FROM Desabastecimiento;
DELETE FROM PerdidaLote;
DELETE FROM EventoFalla;
DELETE FROM LecturaTemperatura;
DELETE FROM Entrega;
DELETE FROM DetallePedido;
DELETE FROM Pedido;
DELETE FROM CostoOperativo;
DELETE FROM Lote;
DBCC CHECKIDENT ('MovimientoInventario', RESEED, 0);
DBCC CHECKIDENT ('Desabastecimiento', RESEED, 0);
DBCC CHECKIDENT ('PerdidaLote', RESEED, 0);
DBCC CHECKIDENT ('EventoFalla', RESEED, 0);
DBCC CHECKIDENT ('LecturaTemperatura', RESEED, 0);
DBCC CHECKIDENT ('Entrega', RESEED, 0);
DBCC CHECKIDENT ('DetallePedido', RESEED, 0);
DBCC CHECKIDENT ('Pedido', RESEED, 0);
DBCC CHECKIDENT ('CostoOperativo', RESEED, 0);
DBCC CHECKIDENT ('Lote', RESEED, 0);
EXEC sp_MSforeachtable 'ALTER TABLE ? CHECK CONSTRAINT ALL';
""")
# Confirma (commit) todos los cambios realizados por el script de
# limpieza y cierra la conexion a la base de datos.
conn.commit(); conn.close()
print("Datos dinamicos limpiados.")