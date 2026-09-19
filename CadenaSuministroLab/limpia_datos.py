from config import get_connection

conn = get_connection(); cur = conn.cursor()

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
conn.commit(); conn.close()
print("Datos dinamicos limpiados.")