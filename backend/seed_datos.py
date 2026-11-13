"""Datos semilla editables: cohortes, laboratorios, temáticas y configuración de IA.

IMPORTANTE: los laboratorios marcados como PROVISIONAL son de ejemplo.
Reemplázalos por los laboratorios reales del curso (los reúne Rol 1) editando
solo esta lista; luego corre `python seed.py`. El seed no sobrescribe
laboratorios que ya existan con el mismo código.
"""

COHORTES: list[dict] = [
    {"numero": 1, "nombre": "Cohorte 1"},
    {"numero": 2, "nombre": "Cohorte 2"},
]

LABORATORIOS: list[dict] = [
    {
        "cohorte": 1,
        "codigo": "C1-L1",
        "titulo": "[PROVISIONAL] Laboratorio 1 de la cohorte 1",
        "descripcion": "Descripción provisional. Reemplazar por la del laboratorio real.",
        "objetivos": "Objetivos provisionales. Reemplazar por los del laboratorio real.",
    },
    {
        "cohorte": 1,
        "codigo": "C1-L2",
        "titulo": "[PROVISIONAL] Laboratorio 2 de la cohorte 1",
        "descripcion": "Descripción provisional. Reemplazar por la del laboratorio real.",
        "objetivos": "Objetivos provisionales. Reemplazar por los del laboratorio real.",
    },
    {
        "cohorte": 1,
        "codigo": "C1-L3",
        "titulo": "[PROVISIONAL] Laboratorio 3 de la cohorte 1",
        "descripcion": "Descripción provisional. Reemplazar por la del laboratorio real.",
        "objetivos": "Objetivos provisionales. Reemplazar por los del laboratorio real.",
    },
    {
        "cohorte": 2,
        "codigo": "C2-L1",
        "titulo": "[PROVISIONAL] Laboratorio 1 de la cohorte 2",
        "descripcion": "Descripción provisional. Reemplazar por la del laboratorio real.",
        "objetivos": "Objetivos provisionales. Reemplazar por los del laboratorio real.",
    },
    {
        "cohorte": 2,
        "codigo": "C2-L2",
        "titulo": "[PROVISIONAL] Laboratorio 2 de la cohorte 2",
        "descripcion": "Descripción provisional. Reemplazar por la del laboratorio real.",
        "objetivos": "Objetivos provisionales. Reemplazar por los del laboratorio real.",
    },
    {
        "cohorte": 2,
        "codigo": "C2-L3",
        "titulo": "[PROVISIONAL] Laboratorio 3 de la cohorte 2",
        "descripcion": "Descripción provisional. Reemplazar por la del laboratorio real.",
        "objetivos": "Objetivos provisionales. Reemplazar por los del laboratorio real.",
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

CONFIG_IA: dict = {"proveedor": "gemini", "modelo": "gemini-2.5-flash", "temperatura": 0.1}
