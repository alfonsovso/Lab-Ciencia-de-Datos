# Simulador de Cadena de Frío — Distribución de Vacunas

Simulación de una cadena de suministro de vacunas con control de **cadena de
frío**. Modela, día a día y con datos persistidos en SQL Server, todo el
ciclo: llegada de lotes desde proveedores, almacenamiento en distintas
cámaras térmicas, fallas de refrigeración con protocolo de cuarentena y
control de calidad, pedidos de hospitales con despacho FEFO, vencimientos,
desabastecimiento, y un informe final con indicadores operativos y
financieros (KPI).

## Características principales

- **Catálogo maestro** de vacunas, cámaras, proveedores y hospitales,
  centralizado en un único archivo (`catalogo.py`) para que nada quede
  duplicado ni desincronizado entre módulos.
- **Cadena de frío realista (GDP/OMS)**: cuando una cámara sufre una falla,
  el lote no se destruye automáticamente. Pasa a *cuarentena*, acumula
  exposición térmica (grados-hora sobre su límite) y, al finalizar la falla,
  un proceso de calidad decide su destino:
  - exposición ≤ 50% del presupuesto de excursión → se libera completo
  - 50%–100% del presupuesto → rechazo parcial proporcional
  - > 100% del presupuesto → rechazo total (pérdida)
- **Despacho FEFO** (*First Expired, First Out*): los pedidos se atienden
  primero con los lotes más próximos a caducar.
- **Escenarios configurables**: `normal`, `estres` y `critico`, o ajustes
  puntuales de cualquier parámetro vía línea de comandos.
- **Informe final de 11 secciones** con balance de masas, inventario,
  nivel de servicio, cadena de frío, calidad, logística, desabastecimiento,
  valoración de inventario, costos operativos, resultado económico y un
  diagnóstico automático con alertas accionables.

## Estructura del proyecto

| Archivo               | Responsabilidad                                                        |
|------------------------|-------------------------------------------------------------------------|
| `catalogo.py`          | Fuente única de verdad: vacunas, cámaras, proveedores, hospitales, severidad de fallas, presupuestos de excursión y costos operativos. |
| `config.py`            | Conexión a SQL Server, parámetros generales de la simulación y el diccionario `ESCENARIO` (con sus presets `normal` / `estres` / `critico`). |
| `seed_estaticos.py`    | Siembra idempotente de los datos fijos (proveedores, hospitales, vacunas, sensores). |
| `lotes.py`             | Planifica y registra la llegada de lotes según la cadencia de cada proveedor. |
| `pedidos.py`           | Demanda hospitalaria, despacho FEFO, vencimientos y desabastecimiento. |
| `frio.py`              | Simulación diaria de la cadena de frío: lecturas de temperatura, fallas, cuarentena y control de calidad. |
| `costos.py`            | Acumulación diaria del costo de almacenamiento (dosis-día). |
| `informes.py`          | Reporte final de KPIs y diagnóstico de la cadena. |
| `run_all.py`           | Orquestador único de la simulación: ejecuta todo el flujo día a día. |
| `solo_informe.py`      | Reimprime el informe final sobre datos ya existentes, sin correr la simulación. |
| `limpia_datos.py`      | Borra el contenido de todas las tablas dinámicas y reinicia sus IDENTITY. |

## Requisitos

- Python 3.9+
- SQL Server (local o remoto) con el esquema de la base de datos creado
- Driver ODBC 18 para SQL Server
- Paquete `pyodbc`

```bash
pip install pyodbc
```

## Configuración

Antes de correr la simulación, edita `config.py` con los datos de conexión
a tu base de datos (`DB_CONFIG`):

```python
DB_CONFIG = {
    "driver": "{ODBC Driver 18 for SQL Server}",
    "server": "localhost,1433",
    "database": "LabCadenaSuministro",
    "username": "sa",
    "password": "TU_CONTRASEÑA",
}
```

> ⚠️ **Seguridad:** no subas credenciales reales a un repositorio público.
> Se recomienda mover `DB_CONFIG` a variables de entorno (por ejemplo con
> `python-dotenv`) antes de publicar el código.

## Uso

Ejecutar la simulación completa con el escenario base:

```bash
python run_all.py
```

Ejecutar con un preset distinto y reiniciando los datos transaccionales:

```bash
python run_all.py --modo estres --reset
python run_all.py --modo critico --reset
```

Ajustar parámetros puntuales del escenario (sin usar un preset completo):

```bash
python run_all.py --reset --set prob_falla_diaria=0.05 --set multiplicador_demanda=1.8
```

### Argumentos disponibles

| Argumento         | Descripción                                                              |
|-------------------|---------------------------------------------------------------------------|
| `--modo`          | Preset de escenario: `normal` (default), `estres` o `critico`.           |
| `--dias`          | Duración de la simulación en días (default: `config.DIAS_SIMULACION`).   |
| `--semilla`       | Semilla del generador aleatorio; misma semilla → resultados reproducibles.|
| `--reset`         | Borra los datos transaccionales previos antes de correr.                 |
| `--reset-total`   | Además borra los datos estáticos del catálogo (se vuelven a sembrar).    |
| `--set CLAVE=VALOR` | Sobrescribe un parámetro puntual de `ESCENARIO` (puede repetirse).      |

### Otros scripts útiles

```bash
python solo_informe.py    # reimprime el informe sobre los datos ya existentes
python limpia_datos.py    # limpia todas las tablas dinámicas y reinicia los IDs
```

## Escenarios (presets)

| Parámetro                         | normal | estres | critico |
|------------------------------------|--------|--------|---------|
| `multiplicador_demanda`            | 1.0    | 1.5    | 2.0     |
| `multiplicador_oferta`             | 0.85   | 0.8    | 0.6     |
| `dias_extra_entre_lotes`           | 0      | 4      | 8       |
| `prob_falla_diaria`                | 0.0002 | 0.02   | 0.04    |
| `multiplicador_severidad`          | 1.0    | 1.5    | 2.0     |
| `presupuesto_excursion_mult`       | 1.0    | 0.7    | 0.4     |
| `max_dias_espera`                  | 12     | 8      | 5       |

## Informe final

Al terminar la simulación (o al correr `solo_informe.py`), se imprime en
consola un reporte con las siguientes secciones:

1. Balance de masas
2. Inventario
3. Demanda y nivel de servicio
4. Demanda por vacuna
5. Cadena de frío
6. Calidad y cuarentena
7. Logística y entregas
8. Desabastecimiento
9. Valoración de inventario (USD)
10. Costos operativos (USD)
11. Resultado económico (USD)

Seguido de un **diagnóstico automático** (EXCELENTE / BUENA / DEGRADADA /
CRITICA) y una lista de alertas concretas, cada una con el parámetro de
`ESCENARIO` sugerido para corregir el problema detectado.

## Autor

**Ing. G. Alfonso Vargas Solís**
📧 alfonso.vargas.solis@gmail.com
🐙 [github.com/alfonsovso](https://github.com/alfonsovso)
