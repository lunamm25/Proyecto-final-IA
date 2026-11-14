# Rúbricas de demostración (formato RubricaSchema)

Tres rúbricas reales del curso, ya convertidas al formato de `backend/app/ia/schemas.py` (§7 de REQUISITOS).
Validadas con Pydantic; todas suman 100 %.

| Archivo | Laboratorio | Criterios | Niveles |
|---|---|---|---|
| rubrica_fundamentos_ia.json | Parcial 1 – Fundamentos de IA (desarrollo de software aumentado) | 5 | Los del documento (rangos con punto medio: 4.75 / 3.95 / 1.7) |
| rubrica_lab01.json | LAB01 – Automatización de archivos con Python | 6 | Generados: 5.0 / 3.5 / 0.0 |
| rubrica_manizales.json | LAB 01 – Manizales Resiliente | 10 | Generados: 5.0 / 3.5 / 0.0 |

## Origen de los niveles generados (LAB01 y Manizales)
Esos documentos traen criterios y puntos, pero no niveles de desempeño. Los descriptores de los 3 niveles
se armaron con una plantilla fija sobre los aspectos que pide el propio documento, copiados de su texto
(sin adjetivos ni requisitos añadidos). Son una **propuesta pendiente de aprobación docente**:
el docente puede ajustarlos en el editor de rúbricas (RF-03 CA3) antes de aprobar la versión.

## Uso sugerido
- Rol 2 (Mariana): cargarlas en `seed.py` como rúbricas de los laboratorios de la cohorte correspondiente.
- Rol 1 (Laura): como entradas de prueba del evaluador (Tarea 3), sin gastar llamadas a la IA.
