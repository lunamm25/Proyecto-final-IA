# LABORATORIO 01 — Automatización de archivos con Python tradicional

**Curso:** Desarrollo de software con IA · Ingeniería de Sistemas  
**Modalidad:** parejas (máximo 2 estudiantes) o individual  
**Tiempo:** 90 minutos de laboratorio + 30 minutos para informe  
**Herramientas:** Python 3.12, PowerShell y editor de código; no se utilizan modelos LLM ni agentes en la implementación.  
**Propósito:** ejecutar, observar, validar, explicar y ampliar un programa existente; no limitarse a copiar comandos.

## 1. Situación problema

Una organización recibe archivos PDF, imágenes, textos y formatos diversos sin clasificar. Se proporciona un programa Python que los inventaría, organiza y verifica. Tu misión consiste en **auditar su funcionamiento y realizar una mejora controlada**, manteniendo la seguridad de los datos de prueba.

**Resultado de aprendizaje:** ejecutar y verificar una automatización programada mediante reglas, identificar funciones y estructuras de control, demostrar propiedades de integridad e idempotencia e implementar una ampliación con una prueba automatizada.

**Regla de seguridad:** utiliza EXCLUSIVAMENTE las carpetas ficticias que genera este laboratorio. No apuntes el programa hacia Descargas, Documentos, Escritorio ni carpetas personales. La ejecución real mueve archivos.

## 2. Material recibido

```text
Laboratorio_01_Python_Tradicional/
├── organizador_archivos.py
├── README.md
├── Archivos_Ejemplo_Entrada/
├── tests/
│   └── test_organizador.py
├── GUIA_ACTIVIDAD_ESTUDIANTES.md
└── PLANTILLA_INFORME.md
```

Las carpetas `Archivos/`, `Archivos_Reto/`, `registros_Archivos/` y `registros_Archivos_Reto/` aparecerán durante las ejecuciones. Las carpetas `Archivos_Ejemplo_Entrada/` contienen datos de referencia: **no las modifiques**.

## 3. Desarrollo paso a paso

### Fase A. Preparar y comprender el entorno (10 min)

1. Descomprime el ZIP y entra a `Laboratorio_01_Python_Tradicional`.
2. En el Explorador de Windows, escribe `powershell` en la barra de direcciones para abrir la terminal **en la raíz del proyecto**.
3. Ejecuta:

```powershell
Get-Location
Get-ChildItem
py -0p
py -3.12 --version
```

**Verifica:** puedes ver `organizador_archivos.py` y la carpeta `tests` en el directorio actual. Si estás dentro de `Archivos`, usa `cd ..`. Si no tienes Python 3.12, utiliza otra versión disponible 3.10+ cambiando `-3.12`.

**Evidencia E1:** captura de la estructura de proyecto y versión de Python.

### Fase B. Crear los datos y registrar el estado inicial (10 min)

```powershell
py -3.12 .\organizador_archivos.py --ruta .\Archivos --crear-demo
Get-ChildItem .\Archivos -Recurse -File
```

El conjunto limpio de demostración tiene **12 archivos**: 11 en el directorio raíz de `Archivos` y un PDF ya ubicado en `Documentos` para provocar una colisión de nombre. Si ya creaste la demo, no ejecutes de nuevo esperando restaurarla: la opción no sobrescribe archivos existentes. Trabaja en una extracción limpia del ZIP o utiliza otra ruta.

Conserva las huellas del contenido **antes** de organizar:

```powershell
$antes = @(Get-ChildItem .\Archivos -Recurse -File | Get-FileHash -Algorithm SHA256 | Select-Object -ExpandProperty Hash | Sort-Object)
$antes.Count
```

**Evidencia E2:** inventario inicial y cantidad de archivos.

### Fase C. Simular y explicar el plan (10 min)

```powershell
py -3.12 .\organizador_archivos.py --ruta .\Archivos --simular
```

La simulación no debe mover archivos. Puede generar registros fuera de `Archivos`.

**Registra** al menos tres ejemplos de origen y destino, una extensión no contemplada explícitamente y la colisión prevista para `acta reunion.pdf`.

**Evidencia E3:** captura de simulación; explica qué significa cada operación.

### Fase D. Ejecutar y auditar resultados (15 min)

```powershell
py -3.12 .\organizador_archivos.py --ruta .\Archivos
Get-ChildItem .\Archivos -Recurse -File | Select-Object FullName, Length
```

**Sobre una demo limpia se espera:** 12 archivos iniciales, 11 movimientos, un conflicto de nombres resuelto (`acta_reunion__2.pdf`), cero errores y 12 archivos finales.

Calcula nuevamente las huellas:

```powershell
$despues = @(Get-ChildItem .\Archivos -Recurse -File | Get-FileHash -Algorithm SHA256 | Select-Object -ExpandProperty Hash | Sort-Object)
Compare-Object -ReferenceObject $antes -DifferenceObject $despues
```

**Resultado esperado:** `Compare-Object` no muestra diferencias. Es una comparación de huellas, no de nombres, porque los nombres y rutas cambian. Si no guardaste la variable `$antes` en la **misma sesión**, no podrás realizar esta comparación; en ese caso utiliza una copia limpia y vuelve a generar el inventario inicial.

Examina la evidencia de auditoría:

```powershell
Get-ChildItem .\registros_Archivos
$reportes = Get-ChildItem .\registros_Archivos -Filter *.json | Sort-Object LastWriteTime
$reportes | Select-Object Name, LastWriteTime
Get-Content $reportes[-1].FullName -Raw
```

**Evidencia E4:** estructura final, salida de verificación y reporte JSON correspondiente a la ejecución real con movimientos. Puedes escoger el JSON adecuado de la lista de reportes, no necesariamente el último cuando hayas ejecutado varias veces.

### Fase E. Probar comportamiento e idempotencia (15 min)

Ejecuta las pruebas automatizadas **desde la raíz del proyecto**:

```powershell
py -3.12 -m unittest discover -s tests -v
```

**Resultado de referencia:** `Ran 10 tests` y `OK` en el proyecto original.

Repite la ejecución real:

```powershell
py -3.12 .\organizador_archivos.py --ruta .\Archivos
```

**Resultado esperado:** `archivos_movidos: 0`; el programa no vuelve a procesar lo que ya está ordenado.

**Evidencia E5:** pruebas correctas y segunda ejecución con cero movimientos. Explica con tus palabras por qué se trata de un comportamiento idempotente.

### Fase F. Examinar el código y ampliar la funcionalidad (30 min)

Abre `organizador_archivos.py` e identifica las funciones: `inventario()`, `categoria()`, `normalizar()`, `nombre_libre()`, `copiar_y_retirar()`, `huella()` y `organizar()`.

**Reto obligatorio:** agregar soporte a la extensión **`.rtf`** para que se clasifique en `Documentos`.

1. Localiza el diccionario `CATEGORIAS` y agrega la extensión `.rtf` en la categoría pertinente.
2. En `tests/`, crea un nuevo archivo llamado `test_extension_rtf.py` que compruebe, como mínimo, que `categoria(Path('ensayo tecnico.RTF'))` devuelve `Documentos` (la mayúscula verifica normalización de extensión).
3. Ejecuta las pruebas. **Debe haber 11 pruebas correctas**: las 10 anteriores más tu prueba nueva.
4. Prepara un conjunto de datos separado para la ampliación:

```powershell
py -3.12 .\organizador_archivos.py --ruta .\Archivos_Reto --crear-demo
Set-Content -LiteralPath '.\Archivos_Reto\ensayo tecnico.rtf' -Value '{\rtf1\ansi Ejemplo de documento RTF}' -Encoding ascii
py -3.12 .\organizador_archivos.py --ruta .\Archivos_Reto --simular
py -3.12 .\organizador_archivos.py --ruta .\Archivos_Reto
Test-Path '.\Archivos_Reto\Documentos\ensayo_tecnico.rtf'
py -3.12 -m unittest discover -s tests -v
```

**Resultado esperado:** `True` en `Test-Path`, 13 archivos conservados en `Archivos_Reto` (12 de la demo más el RTF), y 11 pruebas correctas. El archivo RTF es un ejemplo de formato RTF, no un documento confidencial.

**Evidencia E6:** cambio realizado en el código, nueva prueba y salida de organización. **No edites las diez pruebas originales para forzar su aprobación.**

> **Reto opcional:** identifica otra situación límite (por ejemplo, una extensión en mayúsculas, varios espacios o archivos de igual contenido con nombres diferentes), escribe una prueba adicional e interpreta el resultado.

## 4. Preguntas de análisis técnico

Contesta con ejemplos del programa (no con definiciones genéricas):

1. ¿Qué función decide la categoría del archivo y en qué estructura están codificadas esas reglas?
2. ¿Cuál es la diferencia entre `--simular` y ejecutar sin esa bandera?
3. ¿Qué ocurre cuando dos archivos terminan con el mismo nombre? ¿Por qué no se pierde el archivo original?
4. ¿Por qué la validación SHA-256 aporta evidencia adicional al conteo de archivos? ¿Qué limitación sigue existiendo?
5. ¿Por qué la segunda ejecución no genera movimientos adicionales?
6. ¿Qué decisiones toma el programa y cuáles siguen dependiendo del ingeniero que lo programó?
7. ¿Qué habría que agregar para clasificar documentos según su **contenido** en lugar de únicamente su extensión?
8. ¿Qué diferencia esperarías al resolver esta tarea con un agente que utiliza Tool Calling?

## 5. Entrega solicitada

Entrega **un solo ZIP** titulado `LAB01_GrupoXX.zip`, sin carpetas personales ni claves de acceso, con:

```text
LAB01_GrupoXX/
├── INFORME_LAB01.md (o PDF, máximo 3 páginas + anexos)
├── organizador_archivos.py            # versión modificada para .rtf
├── test_extension_rtf.py              # prueba escrita por el equipo
├── evidencia/
│   ├── E1_entorno.png
│   ├── E2_inventario_inicial.png
│   ├── E3_simulacion.png
│   ├── E4_ejecucion_integridad.png
│   ├── E5_pruebas_idempotencia.png
│   └── E6_reto_rtf.png
└── auditoria/
    └── ejecucion_real.json            # copia del reporte correspondiente
```

**No se exige volver a entregar los PDF, PNG u otros datos ficticios que ya entregó el docente.** Las capturas deben ser legibles y mostrar los resultados reales. No se aceptan afirmaciones de verificación sin evidencia.

## 6. Rúbrica de evaluación (100 puntos)

| Criterio | Puntos |
|---|---:|
| Preparación, inventario y evidencia inicial | 10 |
| Simulación e interpretación correcta del plan | 15 |
| Ejecución real, solución de colisiones e integridad | 25 |
| Pruebas automatizadas e idempotencia | 20 |
| Modificación `.rtf` y nueva prueba propia | 20 |
| Análisis técnico y conexión con programación agéntica | 10 |
| **Total** | **100** |

**Criterio de calidad:** la entrega debe permitir al docente reproducir el resultado. Se valorará el análisis de errores y limitaciones por encima de capturas sin interpretación.

## 7. Errores frecuentes

| Error | Explicación y corrección |
|---|---|
| `can't open file ... organizador_archivos.py` | Estás en otro directorio. Ejecuta `Get-Location` y vuelve a la carpeta que contiene el `.py`. |
| `No suitable Python runtime found` | No tienes esa versión; consulta `py -0p`. Usa una versión 3.10+ instalada. |
| `Start directory is not importable: 'tests'` | Estás dentro de `Archivos/`; ejecuta `cd ..` y repite `unittest`. |
| La demo no crea archivos nuevos | Ya existen; `--crear-demo` no los sobrescribe. Utiliza otra carpeta de prueba. |
| `archivos_movidos: 0` en segunda ejecución | Es el comportamiento idempotente esperado. |
| El RTF queda en `Otros` | Falta actualizar `CATEGORIAS` o estás ejecutando otra versión del programa. |
| `Test-Path` devuelve `False` | Revisa si el RTF se creó dentro de `Archivos_Reto`, si el nombre se normalizó y si `.rtf` apunta a Documentos. |

## 8. Conexión con la siguiente práctica

En este laboratorio **las reglas y la secuencia están codificadas en Python**. En el siguiente, el mismo problema se resolverá con un **agente Python conectado a un LLM en la nube**: el modelo podrá seleccionar herramientas mediante Tool Calling, mientras Python continuará controlando y verificando las operaciones sobre archivos.

**Reflexión de cierre:** ¿Qué decisiones delegarías en un agente y qué verificaciones jamás eliminarías del programa tradicional?
