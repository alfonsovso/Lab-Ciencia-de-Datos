USE [LabCadenaSuministro]
GO
/****** Object:  Table [dbo].[CostoOperativo]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[CostoOperativo](
	[id] [bigint] IDENTITY(1,1) NOT NULL,
	[fecha] [datetime2](7) NOT NULL,
	[categoria] [nvarchar](50) NOT NULL,
	[lote_id] [int] NULL,
	[cantidad_base] [decimal](18, 2) NOT NULL,
	[monto] [decimal](18, 2) NOT NULL,
	[descripcion] [nvarchar](200) NULL,
 CONSTRAINT [PK_CostoOperativo] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Desabastecimiento]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Desabastecimiento](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[hospital_id] [int] NOT NULL,
	[vacuna_id] [int] NOT NULL,
	[pedido_id] [int] NULL,
	[fecha_inicio] [datetime2](7) NOT NULL,
	[fecha_fin] [datetime2](7) NULL,
	[cantidad_faltante] [int] NOT NULL,
	[causa] [nvarchar](200) NULL,
 CONSTRAINT [PK_Desabastecimiento] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[DetallePedido]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[DetallePedido](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[pedido_id] [int] NOT NULL,
	[vacuna_id] [int] NOT NULL,
	[cantidad_solicitada] [int] NOT NULL,
	[cantidad_atendida] [int] NOT NULL,
 CONSTRAINT [PK_DetallePedido] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Entrega]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Entrega](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[detalle_pedido_id] [int] NOT NULL,
	[lote_id] [int] NOT NULL,
	[cantidad_entregada] [int] NOT NULL,
	[fecha_prometida] [datetime2](7) NOT NULL,
	[fecha_real] [datetime2](7) NULL,
	[retraso_dias]  AS (datediff(day,[fecha_prometida],[fecha_real])) PERSISTED,
 CONSTRAINT [PK_Entrega] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[EventoFalla]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[EventoFalla](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[sensor_id] [int] NOT NULL,
	[tipo_falla] [nvarchar](100) NOT NULL,
	[fecha_inicio] [datetime2](7) NOT NULL,
	[fecha_fin] [datetime2](7) NULL,
	[duracion_minutos]  AS (datediff(minute,[fecha_inicio],[fecha_fin])) PERSISTED,
	[causa] [nvarchar](500) NULL,
 CONSTRAINT [PK_EventoFalla] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Hospital]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Hospital](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[nombre] [nvarchar](200) NOT NULL,
	[ciudad] [nvarchar](100) NULL,
	[capacidad_almacen] [int] NULL,
	[activo] [bit] NOT NULL,
 CONSTRAINT [PK_Hospital] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[LecturaTemperatura]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[LecturaTemperatura](
	[id] [bigint] IDENTITY(1,1) NOT NULL,
	[sensor_id] [int] NOT NULL,
	[timestamp] [datetime2](7) NOT NULL,
	[temperatura] [decimal](5, 2) NOT NULL,
 CONSTRAINT [PK_LecturaTemperatura] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Lote]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Lote](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[codigo_lote] [nvarchar](50) NOT NULL,
	[vacuna_id] [int] NOT NULL,
	[proveedor_id] [int] NOT NULL,
	[sensor_id] [int] NULL,
	[fecha_fabricacion] [date] NOT NULL,
	[fecha_caducidad] [date] NOT NULL,
	[cantidad_inicial] [int] NOT NULL,
	[cantidad_actual] [int] NOT NULL,
	[fecha_ingreso] [datetime2](7) NOT NULL,
	[fecha_salida] [datetime2](7) NULL,
	[estado] [nvarchar](20) NOT NULL,
 CONSTRAINT [PK_Lote] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Lote_codigo] UNIQUE NONCLUSTERED 
(
	[codigo_lote] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[MovimientoInventario]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[MovimientoInventario](
	[id] [bigint] IDENTITY(1,1) NOT NULL,
	[lote_id] [int] NOT NULL,
	[tipo] [nvarchar](20) NOT NULL,
	[cantidad] [int] NOT NULL,
	[fecha] [datetime2](7) NOT NULL,
	[referencia] [nvarchar](100) NULL,
 CONSTRAINT [PK_MovimientoInventario] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Pedido]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Pedido](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[hospital_id] [int] NOT NULL,
	[fecha_pedido] [datetime2](7) NOT NULL,
	[fecha_requerida] [datetime2](7) NOT NULL,
	[estado] [nvarchar](20) NOT NULL,
	[prioridad] [nvarchar](10) NOT NULL,
 CONSTRAINT [PK_Pedido] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[PerdidaLote]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[PerdidaLote](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[lote_id] [int] NOT NULL,
	[evento_falla_id] [int] NULL,
	[fecha_perdida] [datetime2](7) NOT NULL,
	[cantidad_perdida] [int] NOT NULL,
	[motivo] [nvarchar](200) NULL,
	[temp_maxima] [decimal](5, 2) NULL,
 CONSTRAINT [PK_PerdidaLote] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Proveedor]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Proveedor](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[nombre] [nvarchar](200) NOT NULL,
	[contacto] [nvarchar](200) NULL,
	[tiempo_entrega_promedio_dias] [int] NOT NULL,
	[variabilidad_dias] [int] NOT NULL,
	[activo] [bit] NOT NULL,
 CONSTRAINT [PK_Proveedor] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Sensor]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Sensor](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[ubicacion] [nvarchar](200) NOT NULL,
	[tipo] [nvarchar](50) NOT NULL,
	[estado] [nvarchar](20) NOT NULL,
	[fecha_instalacion] [datetime2](7) NOT NULL,
 CONSTRAINT [PK_Sensor] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Vacuna]    Script Date: 18/9/2026 18:18:46 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Vacuna](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[nombre] [nvarchar](200) NOT NULL,
	[fabricante] [nvarchar](200) NULL,
	[temp_min] [decimal](5, 2) NOT NULL,
	[temp_max] [decimal](5, 2) NOT NULL,
	[dosis_por_vial] [int] NOT NULL,
	[vida_util_dias] [int] NOT NULL,
	[costo_unitario] [decimal](12, 2) NOT NULL,
	[precio_unitario] [decimal](12, 2) NOT NULL,
 CONSTRAINT [PK_Vacuna] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
ALTER TABLE [dbo].[CostoOperativo] ADD  CONSTRAINT [DF_CostoOperativo_fecha]  DEFAULT (sysdatetime()) FOR [fecha]
GO
ALTER TABLE [dbo].[Desabastecimiento] ADD  CONSTRAINT [DF_Desabastecimiento_fecha_inicio]  DEFAULT (sysdatetime()) FOR [fecha_inicio]
GO
ALTER TABLE [dbo].[DetallePedido] ADD  CONSTRAINT [DF_DetallePedido_cantidad_atendida]  DEFAULT ((0)) FOR [cantidad_atendida]
GO
ALTER TABLE [dbo].[EventoFalla] ADD  CONSTRAINT [DF_EventoFalla_fecha_inicio]  DEFAULT (sysdatetime()) FOR [fecha_inicio]
GO
ALTER TABLE [dbo].[Hospital] ADD  CONSTRAINT [DF_Hospital_activo]  DEFAULT ((1)) FOR [activo]
GO
ALTER TABLE [dbo].[LecturaTemperatura] ADD  CONSTRAINT [DF_LecturaTemperatura_timestamp]  DEFAULT (sysdatetime()) FOR [timestamp]
GO
ALTER TABLE [dbo].[Lote] ADD  CONSTRAINT [DF_Lote_fecha_ingreso]  DEFAULT (sysdatetime()) FOR [fecha_ingreso]
GO
ALTER TABLE [dbo].[Lote] ADD  CONSTRAINT [DF_Lote_estado]  DEFAULT ('Disponible') FOR [estado]
GO
ALTER TABLE [dbo].[MovimientoInventario] ADD  CONSTRAINT [DF_MovimientoInventario_fecha]  DEFAULT (sysdatetime()) FOR [fecha]
GO
ALTER TABLE [dbo].[Pedido] ADD  CONSTRAINT [DF_Pedido_fecha_pedido]  DEFAULT (sysdatetime()) FOR [fecha_pedido]
GO
ALTER TABLE [dbo].[Pedido] ADD  CONSTRAINT [DF_Pedido_estado]  DEFAULT ('Pendiente') FOR [estado]
GO
ALTER TABLE [dbo].[Pedido] ADD  CONSTRAINT [DF_Pedido_prioridad]  DEFAULT ('Normal') FOR [prioridad]
GO
ALTER TABLE [dbo].[PerdidaLote] ADD  CONSTRAINT [DF_PerdidaLote_fecha_perdida]  DEFAULT (sysdatetime()) FOR [fecha_perdida]
GO
ALTER TABLE [dbo].[Proveedor] ADD  CONSTRAINT [DF_Proveedor_activo]  DEFAULT ((1)) FOR [activo]
GO
ALTER TABLE [dbo].[Sensor] ADD  CONSTRAINT [DF_Sensor_estado]  DEFAULT ('Activo') FOR [estado]
GO
ALTER TABLE [dbo].[Sensor] ADD  CONSTRAINT [DF_Sensor_fecha_instalacion]  DEFAULT (sysdatetime()) FOR [fecha_instalacion]
GO
ALTER TABLE [dbo].[Vacuna] ADD  CONSTRAINT [DF_Vacuna_costo]  DEFAULT ((0)) FOR [costo_unitario]
GO
ALTER TABLE [dbo].[Vacuna] ADD  CONSTRAINT [DF_Vacuna_precio]  DEFAULT ((0)) FOR [precio_unitario]
GO
ALTER TABLE [dbo].[CostoOperativo]  WITH CHECK ADD  CONSTRAINT [FK_CostoOperativo_Lote] FOREIGN KEY([lote_id])
REFERENCES [dbo].[Lote] ([id])
GO
ALTER TABLE [dbo].[CostoOperativo] CHECK CONSTRAINT [FK_CostoOperativo_Lote]
GO
ALTER TABLE [dbo].[Desabastecimiento]  WITH NOCHECK ADD  CONSTRAINT [FK_Desabastecimiento_Hospital] FOREIGN KEY([hospital_id])
REFERENCES [dbo].[Hospital] ([id])
GO
ALTER TABLE [dbo].[Desabastecimiento] CHECK CONSTRAINT [FK_Desabastecimiento_Hospital]
GO
ALTER TABLE [dbo].[Desabastecimiento]  WITH NOCHECK ADD  CONSTRAINT [FK_Desabastecimiento_Pedido] FOREIGN KEY([pedido_id])
REFERENCES [dbo].[Pedido] ([id])
GO
ALTER TABLE [dbo].[Desabastecimiento] CHECK CONSTRAINT [FK_Desabastecimiento_Pedido]
GO
ALTER TABLE [dbo].[Desabastecimiento]  WITH NOCHECK ADD  CONSTRAINT [FK_Desabastecimiento_Vacuna] FOREIGN KEY([vacuna_id])
REFERENCES [dbo].[Vacuna] ([id])
GO
ALTER TABLE [dbo].[Desabastecimiento] CHECK CONSTRAINT [FK_Desabastecimiento_Vacuna]
GO
ALTER TABLE [dbo].[DetallePedido]  WITH NOCHECK ADD  CONSTRAINT [FK_DetallePedido_Pedido] FOREIGN KEY([pedido_id])
REFERENCES [dbo].[Pedido] ([id])
ON DELETE CASCADE
GO
ALTER TABLE [dbo].[DetallePedido] CHECK CONSTRAINT [FK_DetallePedido_Pedido]
GO
ALTER TABLE [dbo].[DetallePedido]  WITH NOCHECK ADD  CONSTRAINT [FK_DetallePedido_Vacuna] FOREIGN KEY([vacuna_id])
REFERENCES [dbo].[Vacuna] ([id])
GO
ALTER TABLE [dbo].[DetallePedido] CHECK CONSTRAINT [FK_DetallePedido_Vacuna]
GO
ALTER TABLE [dbo].[Entrega]  WITH NOCHECK ADD  CONSTRAINT [FK_Entrega_DetallePedido] FOREIGN KEY([detalle_pedido_id])
REFERENCES [dbo].[DetallePedido] ([id])
GO
ALTER TABLE [dbo].[Entrega] CHECK CONSTRAINT [FK_Entrega_DetallePedido]
GO
ALTER TABLE [dbo].[Entrega]  WITH NOCHECK ADD  CONSTRAINT [FK_Entrega_Lote] FOREIGN KEY([lote_id])
REFERENCES [dbo].[Lote] ([id])
GO
ALTER TABLE [dbo].[Entrega] CHECK CONSTRAINT [FK_Entrega_Lote]
GO
ALTER TABLE [dbo].[EventoFalla]  WITH NOCHECK ADD  CONSTRAINT [FK_EventoFalla_Sensor] FOREIGN KEY([sensor_id])
REFERENCES [dbo].[Sensor] ([id])
GO
ALTER TABLE [dbo].[EventoFalla] CHECK CONSTRAINT [FK_EventoFalla_Sensor]
GO
ALTER TABLE [dbo].[LecturaTemperatura]  WITH NOCHECK ADD  CONSTRAINT [FK_LecturaTemperatura_Sensor] FOREIGN KEY([sensor_id])
REFERENCES [dbo].[Sensor] ([id])
GO
ALTER TABLE [dbo].[LecturaTemperatura] CHECK CONSTRAINT [FK_LecturaTemperatura_Sensor]
GO
ALTER TABLE [dbo].[Lote]  WITH NOCHECK ADD  CONSTRAINT [FK_Lote_Proveedor] FOREIGN KEY([proveedor_id])
REFERENCES [dbo].[Proveedor] ([id])
GO
ALTER TABLE [dbo].[Lote] CHECK CONSTRAINT [FK_Lote_Proveedor]
GO
ALTER TABLE [dbo].[Lote]  WITH NOCHECK ADD  CONSTRAINT [FK_Lote_Sensor] FOREIGN KEY([sensor_id])
REFERENCES [dbo].[Sensor] ([id])
GO
ALTER TABLE [dbo].[Lote] CHECK CONSTRAINT [FK_Lote_Sensor]
GO
ALTER TABLE [dbo].[Lote]  WITH NOCHECK ADD  CONSTRAINT [FK_Lote_Vacuna] FOREIGN KEY([vacuna_id])
REFERENCES [dbo].[Vacuna] ([id])
GO
ALTER TABLE [dbo].[Lote] CHECK CONSTRAINT [FK_Lote_Vacuna]
GO
ALTER TABLE [dbo].[MovimientoInventario]  WITH NOCHECK ADD  CONSTRAINT [FK_MovimientoInventario_Lote] FOREIGN KEY([lote_id])
REFERENCES [dbo].[Lote] ([id])
GO
ALTER TABLE [dbo].[MovimientoInventario] CHECK CONSTRAINT [FK_MovimientoInventario_Lote]
GO
ALTER TABLE [dbo].[Pedido]  WITH NOCHECK ADD  CONSTRAINT [FK_Pedido_Hospital] FOREIGN KEY([hospital_id])
REFERENCES [dbo].[Hospital] ([id])
GO
ALTER TABLE [dbo].[Pedido] CHECK CONSTRAINT [FK_Pedido_Hospital]
GO
ALTER TABLE [dbo].[PerdidaLote]  WITH NOCHECK ADD  CONSTRAINT [FK_PerdidaLote_EventoFalla] FOREIGN KEY([evento_falla_id])
REFERENCES [dbo].[EventoFalla] ([id])
GO
ALTER TABLE [dbo].[PerdidaLote] CHECK CONSTRAINT [FK_PerdidaLote_EventoFalla]
GO
ALTER TABLE [dbo].[PerdidaLote]  WITH NOCHECK ADD  CONSTRAINT [FK_PerdidaLote_Lote] FOREIGN KEY([lote_id])
REFERENCES [dbo].[Lote] ([id])
GO
ALTER TABLE [dbo].[PerdidaLote] CHECK CONSTRAINT [FK_PerdidaLote_Lote]
GO
ALTER TABLE [dbo].[CostoOperativo]  WITH CHECK ADD  CONSTRAINT [CK_CostoOperativo_categoria] CHECK  (([categoria]='Cuarentena' OR [categoria]='Disposicion' OR [categoria]='Distribucion' OR [categoria]='Transporte' OR [categoria]='Almacenamiento'))
GO
ALTER TABLE [dbo].[CostoOperativo] CHECK CONSTRAINT [CK_CostoOperativo_categoria]
GO
ALTER TABLE [dbo].[CostoOperativo]  WITH CHECK ADD  CONSTRAINT [CK_CostoOperativo_monto] CHECK  (([monto]>=(0)))
GO
ALTER TABLE [dbo].[CostoOperativo] CHECK CONSTRAINT [CK_CostoOperativo_monto]
GO
ALTER TABLE [dbo].[Desabastecimiento]  WITH NOCHECK ADD  CONSTRAINT [CK_Desabastecimiento_cantidad] CHECK  (([cantidad_faltante]>(0)))
GO
ALTER TABLE [dbo].[Desabastecimiento] CHECK CONSTRAINT [CK_Desabastecimiento_cantidad]
GO
ALTER TABLE [dbo].[Desabastecimiento]  WITH NOCHECK ADD  CONSTRAINT [CK_Desabastecimiento_fechas] CHECK  (([fecha_fin] IS NULL OR [fecha_fin]>=[fecha_inicio]))
GO
ALTER TABLE [dbo].[Desabastecimiento] CHECK CONSTRAINT [CK_Desabastecimiento_fechas]
GO
ALTER TABLE [dbo].[DetallePedido]  WITH NOCHECK ADD  CONSTRAINT [CK_DetallePedido_cantidades] CHECK  (([cantidad_solicitada]>(0) AND [cantidad_atendida]>=(0) AND [cantidad_atendida]<=[cantidad_solicitada]))
GO
ALTER TABLE [dbo].[DetallePedido] CHECK CONSTRAINT [CK_DetallePedido_cantidades]
GO
ALTER TABLE [dbo].[Entrega]  WITH NOCHECK ADD  CONSTRAINT [CK_Entrega_cantidad] CHECK  (([cantidad_entregada]>(0)))
GO
ALTER TABLE [dbo].[Entrega] CHECK CONSTRAINT [CK_Entrega_cantidad]
GO
ALTER TABLE [dbo].[EventoFalla]  WITH NOCHECK ADD  CONSTRAINT [CK_EventoFalla_fechas] CHECK  (([fecha_fin] IS NULL OR [fecha_fin]>=[fecha_inicio]))
GO
ALTER TABLE [dbo].[EventoFalla] CHECK CONSTRAINT [CK_EventoFalla_fechas]
GO
ALTER TABLE [dbo].[LecturaTemperatura]  WITH NOCHECK ADD  CONSTRAINT [CK_LecturaTemperatura_temp] CHECK  (([temperatura]>=(-100) AND [temperatura]<=(100)))
GO
ALTER TABLE [dbo].[LecturaTemperatura] CHECK CONSTRAINT [CK_LecturaTemperatura_temp]
GO
ALTER TABLE [dbo].[Lote]  WITH NOCHECK ADD  CONSTRAINT [CK_Lote_cantidades] CHECK  (([cantidad_inicial]>(0) AND [cantidad_actual]>=(0) AND [cantidad_actual]<=[cantidad_inicial]))
GO
ALTER TABLE [dbo].[Lote] CHECK CONSTRAINT [CK_Lote_cantidades]
GO
ALTER TABLE [dbo].[Lote]  WITH NOCHECK ADD  CONSTRAINT [CK_Lote_estado] CHECK  (([estado]='Cuarentena' OR [estado]='Perdido' OR [estado]='Vencido' OR [estado]='Agotado' OR [estado]='Disponible'))
GO
ALTER TABLE [dbo].[Lote] CHECK CONSTRAINT [CK_Lote_estado]
GO
ALTER TABLE [dbo].[Lote]  WITH NOCHECK ADD  CONSTRAINT [CK_Lote_fechas] CHECK  (([fecha_caducidad]>[fecha_fabricacion]))
GO
ALTER TABLE [dbo].[Lote] CHECK CONSTRAINT [CK_Lote_fechas]
GO
ALTER TABLE [dbo].[MovimientoInventario]  WITH NOCHECK ADD  CONSTRAINT [CK_MovimientoInventario_tipo] CHECK  (([tipo]='Perdida' OR [tipo]='Ajuste' OR [tipo]='Salida' OR [tipo]='Entrada'))
GO
ALTER TABLE [dbo].[MovimientoInventario] CHECK CONSTRAINT [CK_MovimientoInventario_tipo]
GO
ALTER TABLE [dbo].[Pedido]  WITH NOCHECK ADD  CONSTRAINT [CK_Pedido_estado] CHECK  (([estado]='Cancelado' OR [estado]='Atendido' OR [estado]='Parcial' OR [estado]='Pendiente'))
GO
ALTER TABLE [dbo].[Pedido] CHECK CONSTRAINT [CK_Pedido_estado]
GO
ALTER TABLE [dbo].[Pedido]  WITH NOCHECK ADD  CONSTRAINT [CK_Pedido_fechas] CHECK  (([fecha_requerida]>=[fecha_pedido]))
GO
ALTER TABLE [dbo].[Pedido] CHECK CONSTRAINT [CK_Pedido_fechas]
GO
ALTER TABLE [dbo].[Pedido]  WITH NOCHECK ADD  CONSTRAINT [CK_Pedido_prioridad] CHECK  (([prioridad]='Urgente' OR [prioridad]='Alta' OR [prioridad]='Normal' OR [prioridad]='Baja'))
GO
ALTER TABLE [dbo].[Pedido] CHECK CONSTRAINT [CK_Pedido_prioridad]
GO
ALTER TABLE [dbo].[PerdidaLote]  WITH NOCHECK ADD  CONSTRAINT [CK_PerdidaLote_cantidad] CHECK  (([cantidad_perdida]>(0)))
GO
ALTER TABLE [dbo].[PerdidaLote] CHECK CONSTRAINT [CK_PerdidaLote_cantidad]
GO
ALTER TABLE [dbo].[Sensor]  WITH NOCHECK ADD  CONSTRAINT [CK_Sensor_estado] CHECK  (([estado]='Falla' OR [estado]='Inactivo' OR [estado]='Activo'))
GO
ALTER TABLE [dbo].[Sensor] CHECK CONSTRAINT [CK_Sensor_estado]
GO
ALTER TABLE [dbo].[Vacuna]  WITH NOCHECK ADD  CONSTRAINT [CK_Vacuna_dosis] CHECK  (([dosis_por_vial]>(0)))
GO
ALTER TABLE [dbo].[Vacuna] CHECK CONSTRAINT [CK_Vacuna_dosis]
GO
ALTER TABLE [dbo].[Vacuna]  WITH NOCHECK ADD  CONSTRAINT [CK_Vacuna_temp] CHECK  (([temp_max]>=[temp_min]))
GO
ALTER TABLE [dbo].[Vacuna] CHECK CONSTRAINT [CK_Vacuna_temp]
GO
ALTER TABLE [dbo].[Vacuna]  WITH NOCHECK ADD  CONSTRAINT [CK_Vacuna_vida] CHECK  (([vida_util_dias]>(0)))
GO
ALTER TABLE [dbo].[Vacuna] CHECK CONSTRAINT [CK_Vacuna_vida]
GO
