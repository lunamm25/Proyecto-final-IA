# Laboratorio 03 — Agente Python con modelo local (Ollama)

**Asignatura:** Inteligencia Artificial — Ingeniería de Sistemas  
**Continuidad:** Laboratorio 01 Python tradicional → Laboratorio 02 Python con DeepSeek Cloud → **Laboratorio 03 Python con Ollama local**.  
**Duración recomendada:** 75–90 minutos.  
**Entorno:** Windows 11, PowerShell y Python 3.12.

## 1. Objetivo

Ejecutar el **mismo agente** del Laboratorio 02 con un LLM local, sin enviar las solicitudes a DeepSeek Cloud. Los archivos siguen siendo procesados por funciones Python, bajo aprobación humana para cambios. Comparar decisiones y resultados en condiciones equivalentes.

## 2. Arquitectura y nombres de archivos

```text
Laboratorio_03_Agente_Python_Local_Ollama/
├── agente_archivos_local.py     # NUEVO: bucle y SDK Ollama
├── agente_archivos_nube.py      # REUTILIZADO: herramientas, autorizaciones y trazas
├── organizador_archivos.py     # REUTILIZADO: motor tradicional Lab 01
├── requirements.txt            # SDK ollama
├── GUIA_ESTUDIANTES.md
├── COMPARACION_NUBE_LOCAL.md
├── tests/                       # pruebas deterministas, sin modelo real
└── workspace/                   # se crea automáticamente
```

**Importante:** `agente_archivos_local.py` importa herramientas desde `agente_archivos_nube.py`, pero **no llama a DeepSeek Cloud**. El acceso a DeepSeek solo ocurre al ejecutar explícitamente la función `ejecutar_nube()`, que el programa local no invoca.

## 3. Requisitos previos

Desde la carpeta raíz del laboratorio:

```powershell
py -3.12 --version
ollama --version
```

Si `ollama` no existe, instala Ollama siguiendo https://ollama.com/download/windows y abre su aplicación para mantener su servidor local activo.

Consulta modelos ya disponibles:

```powershell
ollama list
```

Recomendamos comenzar con **Qwen3 4B Instruct**, variante de ~2,5 GB con soporte de herramientas:

```powershell
ollama pull qwen3:4b-instruct
```

Puedes comprobarlo en terminal:

```powershell
ollama run qwen3:4b-instruct "Contesta solo: modelo local activo"
```

> *No es necesario usar una API Key ni mantener conexión a Internet después de instalar el programa y descargar el modelo.*

## 4. Instalar el SDK de Python

```powershell
py -3.12 -m pip install -r requirements.txt
```

Si la instalación local de Ollama está activa, su servidor suele escuchar en `http://127.0.0.1:11434`.

Comprobación de conectividad local:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags | Select-Object -ExpandProperty models
```

## 5. Crear los 12 archivos ficticios

```powershell
py -3.12 agente_archivos_local.py --crear-demo
```

Se genera `workspace\Archivos`, con 11 archivos pendientes, uno ya organizado y una colisión de nombres intencional.

Inspecciona el inventario:

```powershell
Get-ChildItem .\workspace\Archivos -Recurse -File
```

**Nunca uses tu carpeta real de Descargas, Documentos o escritorio.**

## 6. Primera ejecución con modelo LOCAL (solo lectura)

```powershell
py -3.12 agente_archivos_local.py --modelo qwen3:4b-instruct --objetivo "Inspecciona los archivos y propon un plan de organizacion. No modifiques nada."
```

Eventos observables esperados, aunque el modelo puede variar la secuencia:

```text
SOLICITUD_LLM
MODELO_SOLICITA_HERRAMIENTA: listar_archivos
PYTHON_DEVUELVE_RESULTADO
MODELO_SOLICITA_HERRAMIENTA: proponer_plan
PYTHON_DEVUELVE_RESULTADO
RESPUESTA_FINAL
```

Si el modelo pide aplicar el plan por error, Python **bloquea** la escritura porque no has indicado `--permitir-escritura`.

## 7. Segunda ejecución con aprobación humana

**Únicamente tras validar que los datos son ficticios:**

```powershell
py -3.12 agente_archivos_local.py --modelo qwen3:4b-instruct --permitir-escritura --objetivo "Organiza realmente los archivos por tipo. Primero lista y propone el plan, luego solicita aplicar_plan y despues verificar_resultados."
```

Si el modelo invoca `aplicar_plan`, Python muestra los movimientos y pide escribir **`APROBAR`**. No teclees esa palabra sin revisar el plan.

Si el modelo solo propone un plan y finaliza, **eso no significa que haya movido archivos**. Revisa la traza y repite una instrucción explícita; las decisiones del modelo no se garantizan.

## 8. Verificar resultados y trazas

```powershell
Get-ChildItem .\workspace\Archivos -Recurse -File
Get-ChildItem .\workspace\trazas\ -File | Sort-Object LastWriteTime -Descending | Select-Object -First 3
Get-ChildItem .\workspace\registros_Archivos\ -File
```

En la traza local, `SOLICITUD_LLM` significa que **Python consultó Ollama local**; `MODELO_SOLICITA_HERRAMIENTA` indica una elección generada por el LLM; `PYTHON_DEVUELVE_RESULTADO` indica ejecución de una función local. La verificación del motor incluye SHA-256.

## 9. Ejecutar las pruebas automatizadas

Desde la carpeta raíz:

```powershell
py -3.12 -m unittest discover -s tests -v
```

**Resultado esperado: 23 pruebas, OK.** Son pruebas deterministas con clientes falsos, sin llamar realmente a Ollama; no validan la capacidad predictiva del modelo descargado.

Si aparece `Start directory is not importable: 'tests'`, estás dentro de una subcarpeta: vuelve a la carpeta raíz.

## 10. Comparación con Laboratorio 02

| Variable | Nube — DeepSeek API | Local — Ollama |
|---|---|---|
| Motor de inferencia | DeepSeek remoto | Qwen3 local (valor predeterminado) |
| `organizador_archivos.py` | Igual | Igual |
| Funciones y seguridad | Iguales | Iguales |
| Tool Calling | API externa | SDK y servidor local |
| API Key | Requerida | No requerida |
| Internet durante inferencia | Sí | No, tras descarga y con servidor local |
| Recursos de cómputo del usuario | Menor inferencia local | RAM/CPU/GPU del equipo |
| Posible variación | Orden y selección de herramientas | Orden y selección de herramientas |

**Anota**: número de llamadas al LLM, número de herramientas, organización completada, conflictos gestionados, tiempo medido de principio a fin, autorizaciones y necesidad de reintentar.

## 11. Errores frecuentes

- `ollama : The term 'ollama' is not recognized`: instala Ollama o abre una terminal nueva tras instalar.
- `model not found`: ejecuta `ollama pull qwen3:4b-instruct` y verifica con `ollama list`.
- `connection refused` o `No connection could be made`: abre Ollama o inicia su servicio local.
- `Read timed out`: primera inferencia lenta en equipos sin GPU; cierra otros procesos o elige modelo más pequeño compatible con tools.
- `Start directory is not importable: 'tests'`: corre las pruebas desde la raíz del proyecto.
- El modelo solo planifica: revisa el objetivo y la traza; la disponibilidad de una herramienta no obliga al LLM a invocarla.
- `BLOQUEADO_MODO_LECTURA`: es el comportamiento correcto sin `--permitir-escritura`.

## 12. Preguntas de cierre

1. ¿Qué parte del agente no cambió al pasar de la nube al modelo local?
2. ¿Qué decisiones dependen del modelo elegido?
3. ¿Dónde se ejecutaron las acciones sobre archivos en ambos casos?
4. ¿Puede el modelo omitir una herramienta aunque esté disponible?
5. ¿Por qué la autorización y la integridad SHA-256 deben continuar en Python?

## 13. Entregable

Incluye capturas o evidencias textuales de las dos trazas; una tabla comparativa nube/local; los resultados de `unittest`; y una reflexión técnica de 200–300 palabras sobre la diferencia entre ubicación de inferencia e infraestructura agéntica.
