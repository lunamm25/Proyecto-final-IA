"""Datos semilla editables: cohortes, laboratorios de demo, temáticas y configuración de IA.

Los laboratorios de demo usan el código para indicar el orden dentro de la cohorte
(C1-01, C1-02, ...). Cada uno indica el archivo de su rúbrica en `rubricas_demo/`;
el seed la carga como versión 1 aprobada solo si el laboratorio aún no tiene versiones.
El seed no sobrescribe laboratorios ni rúbricas que ya existan.
"""

COHORTES: list[dict] = [
    {"numero": 1, "nombre": "Cohorte 1"},
    {"numero": 2, "nombre": "Cohorte 2"},
]

LABORATORIOS: list[dict] = [
    {
        "cohorte": 1,
        "codigo": "C1-01",
        "titulo": "Parcial 1 - Fundamentos de IA para el Desarrollo de Software Aumentado",
        "descripcion": (
            "Introduce el uso práctico de modelos de IA desde la perspectiva del "
            "ingeniero de sistemas."
        ),
        "objetivos": (
            "- Relacionar los conceptos de IA, ML y modelos generativos.\n"
            "- Distinguir tipos de modelo (LLM, SLM, VLM, embeddings).\n"
            "- Ejecutar modelos locales con Ollama y LM Studio.\n"
            "- Aplicar Vibe Coding con supervisión humana.\n"
            "- Construir una aplicación que consuma una API de serie temporal."
        ),
        "rubrica_archivo": "rubrica_fundamentos_ia.json",
    },
    {
        "cohorte": 1,
        "codigo": "C1-02",
        "titulo": "LAB 01 - Manizales Resiliente",
        "descripcion": (
            "Diseño de una aplicación inteligente y resiliente para la gestión "
            "post-terremoto, sin implementar los modelos."
        ),
        "objetivos": (
            "- Formular el problema.\n"
            "- Distinguir software convencional de ML e IA.\n"
            "- Seleccionar tecnologías con argumentos.\n"
            "- Diseñar una arquitectura conceptual con resiliencia y Human-in-the-Loop.\n"
            "- Usar la IA de forma responsable con un Banco de Prompts."
        ),
        "rubrica_archivo": "rubrica_manizales.json",
    },
    {
        "cohorte": 2,
        "codigo": "C2-01",
        "titulo": "Laboratorio 01 - Automatización de archivos con Python tradicional",
        "descripcion": (
            "Ejecutar, auditar y ampliar un programa que organiza archivos, sin usar LLM."
        ),
        "objetivos": (
            "- Ejecutar y verificar una automatización por reglas.\n"
            "- Demostrar integridad e idempotencia.\n"
            "- Implementar una ampliación (soporte .rtf) con una prueba automatizada."
        ),
        "rubrica_archivo": "rubrica_lab01.json",
    },
    {
        "cohorte": 2,
        "codigo": "C2-02",
        "titulo": "Laboratorio 03 - Agente Python con modelo local (Ollama)",
        "descripcion": (
            "Ejecutar el mismo agente del Laboratorio 02 con un LLM local (Ollama), sin "
            "enviar solicitudes a DeepSeek Cloud; los archivos los procesan funciones "
            "Python con aprobación humana para los cambios."
        ),
        "objetivos": (
            "- Comparar decisiones y resultados entre nube y local en condiciones equivalentes."
        ),
        "rubrica_archivo": "rubrica_lab03.json",
    },
]

# Taxonomía base de RF-09 CA1 (temáticas raíz, sin padre).
TEMATICAS: list[dict] = [
    {"nombre": "Fundamentos de IA", "descripcion": "Conceptos básicos e historia de la IA."},
    {"nombre": "Aprendizaje automático", "descripcion": "Modelos supervisados y no supervisados."},
    {"nombre": "LLMs", "descripcion": "Modelos de lenguaje de gran tamaño."},
    {"nombre": "Ingeniería de prompts", "descripcion": "Diseño y evaluación de prompts."},
    {
        "nombre": "Modelos locales (Ollama/LM Studio)",
        "descripcion": "Ejecución de modelos en el propio equipo.",
    },
    {"nombre": "Agentes de IA", "descripcion": "Agentes, herramientas y orquestación."},
    {"nombre": "RAG", "descripcion": "Generación aumentada con recuperación."},
    {"nombre": "Visión artificial", "descripcion": "Procesamiento y análisis de imágenes."},
    {
        "nombre": "Series temporales/APIs de datos",
        "descripcion": "Consumo de APIs y análisis de series temporales.",
    },
    {
        "nombre": "Desarrollo de software aumentado / vibe coding",
        "descripcion": "Programación asistida por IA.",
    },
    {"nombre": "Ética y verificación", "descripcion": "Uso responsable y verificación de la IA."},
]

CONFIG_IA: dict = {"proveedor": "gemini", "modelo": "gemini-3.5-flash-lite", "temperatura": 0.1}
