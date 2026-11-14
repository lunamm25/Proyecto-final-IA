// Datos simulados con la misma forma del contrato §11. Las notas son valores fijos:
// el frontend nunca calcula la nota (la calcula el backend).
import type {
  Cita,
  Cohorte,
  ConfigIA,
  Entrega,
  Evaluacion,
  EvaluacionCriterio,
  EvidenciaMapa,
  Informe,
  Laboratorio,
  Mapa,
  NivelDominio,
  NodoMapa,
  Perfil,
  Retroalimentacion,
  RetroalimentacionCriterioIA,
  Rol,
  Rubrica,
  RubricaVersion,
  TipoNodo,
  Traza,
  Usuario,
} from "@/lib/tipos";

const FECHA = "2026-11-10T15:00:00Z";

export const perfilesMock: Record<Rol, Perfil> = {
  estudiante: {
    id: "est-1",
    nombre: "Ana Estudiante",
    rol: "estudiante",
    foto_url: null,
  },
  docente: {
    id: "doc-1",
    nombre: "Carlos Docente",
    rol: "docente",
    foto_url: null,
  },
  admin: {
    id: "adm-1",
    nombre: "Admin Demo",
    rol: "admin",
    foto_url: null,
  },
};

export const usuariosMock: Usuario[] = [
  { id: "est-1", nombre: "Ana Estudiante", correo: "estudiante@demo.edu.co", rol: "estudiante" },
  { id: "doc-1", nombre: "Carlos Docente", correo: "docente@demo.edu.co", rol: "docente" },
  { id: "adm-1", nombre: "Admin Demo", correo: "admin@demo.edu.co", rol: "admin" },
  { id: "est-2", nombre: "Juan Pérez", correo: "juan.perez@demo.edu.co", rol: "estudiante" },
  { id: "est-3", nombre: "María Gómez", correo: "maria.gomez@demo.edu.co", rol: "estudiante" },
  ...["Andrés", "Camila", "Diego", "Elena", "Felipe", "Gabriela", "Hugo", "Isabel", "Julián", "Karen", "Luis", "Natalia"].map(
    (nombre, i): Usuario => ({
      id: `est-${i + 4}`,
      nombre: `${nombre} Prueba`,
      correo: `${nombre.toLowerCase()}.prueba@demo.edu.co`,
      rol: "estudiante",
    }),
  ),
];

/**
 * Cohortes base del mock: sin `version_rubrica_vigente`, que el mock de GET /cohortes calcula a partir de
 * las rúbricas en memoria (igual que hace el backend con sus versiones aprobadas).
 */
export type CohorteMock = Omit<Cohorte, "laboratorios"> & { laboratorios: Laboratorio[] };

export const cohortesMock: CohorteMock[] = [
  {
    id: 1,
    nombre: "Cohorte 1",
    numero: 1,
    laboratorios: [
      {
        id: 1,
        cohorte_id: 1,
        codigo: "C1-L1",
        titulo: "Fundamentos de IA y Python",
        descripcion: "Primer acercamiento a la IA con cuadernos de Python.",
        objetivos: "Comprender conceptos básicos de IA y escribir scripts simples en Python.",
      },
      {
        id: 2,
        cohorte_id: 1,
        codigo: "C1-L2",
        titulo: "Aprendizaje automático supervisado",
        descripcion: "Entrenar y evaluar un clasificador con scikit-learn.",
        objetivos: "Preparar datos, entrenar un modelo y reportar métricas.",
      },
    ],
  },
  {
    id: 2,
    nombre: "Cohorte 2",
    numero: 2,
    laboratorios: [
      {
        id: 3,
        cohorte_id: 2,
        codigo: "C2-L1",
        titulo: "Ingeniería de prompts con LLMs",
        descripcion: "Diseño de prompts y salidas estructuradas con un LLM.",
        objetivos: "Diseñar prompts reproducibles y validar las salidas con esquemas.",
      },
      {
        id: 4,
        cohorte_id: 2,
        codigo: "C2-L2",
        titulo: "RAG con modelos locales",
        descripcion: "Recuperación aumentada con Ollama y una base vectorial.",
        objetivos: "Construir un flujo RAG y evaluar la calidad de las respuestas.",
      },
      {
        id: 5,
        cohorte_id: 2,
        codigo: "C2-L3",
        titulo: "Agentes de IA",
        descripcion: "Agente con herramientas para resolver tareas de varios pasos.",
        objetivos: "Implementar un agente con herramientas y documentar sus límites.",
      },
      {
        id: 6,
        cohorte_id: 2,
        codigo: "C2-L4",
        titulo: "Evaluación de modelos de lenguaje",
        descripcion: "Comparar dos LLMs con un conjunto de pruebas propio.",
        objetivos: "Definir métricas, ejecutar pruebas reproducibles y reportar hallazgos.",
      },
      {
        id: 7,
        cohorte_id: 2,
        codigo: "C2-L5",
        titulo: "Proyecto integrador",
        descripcion: "Aplicación completa que integra los temas del curso.",
        objetivos: "Integrar prompts, RAG y agentes en una solución documentada.",
      },
    ],
  },
];

/** Laboratorios sin rúbrica vigente en el modo mock (para probar RF-02 CA2). */
export const laboratoriosSinRubricaMock: number[] = [7];

export const rubricaVersionMock: RubricaVersion = {
  id: 1,
  version: 1,
  estado: "aprobada",
  creada_por: "doc-1",
  creada_en: FECHA,
  contenido: {
    titulo: "Rúbrica – Ingeniería de prompts con LLMs",
    criterios: [
      {
        id: "c1",
        competencia: "Ingeniería de prompts",
        nombre: "Diseño de prompts",
        ponderacion: 40,
        niveles: [
          { nombre: "Excelente", puntaje: 5, descriptor: "Prompts claros, con rol, contexto, formato y ejemplos." },
          { nombre: "Bueno", puntaje: 4, descriptor: "Prompts claros con algunos elementos faltantes." },
          { nombre: "Básico", puntaje: 2, descriptor: "Prompts genéricos sin estructura." },
          { nombre: "Insuficiente", puntaje: 0, descriptor: "No presenta prompts." },
        ],
      },
      {
        id: "c2",
        competencia: "LLMs",
        nombre: "Salidas estructuradas y validación",
        ponderacion: 35,
        niveles: [
          { nombre: "Excelente", puntaje: 5, descriptor: "Valida todas las salidas con esquemas y maneja errores." },
          { nombre: "Bueno", puntaje: 4, descriptor: "Valida la mayoría de las salidas." },
          { nombre: "Básico", puntaje: 2, descriptor: "Validación parcial o manual." },
          { nombre: "Insuficiente", puntaje: 0, descriptor: "Sin validación." },
        ],
      },
      {
        id: "c3",
        competencia: "Ética y verificación",
        nombre: "Análisis crítico de resultados",
        ponderacion: 25,
        niveles: [
          { nombre: "Excelente", puntaje: 5, descriptor: "Analiza sesgos, alucinaciones y límites con ejemplos." },
          { nombre: "Bueno", puntaje: 4, descriptor: "Menciona límites con algún ejemplo." },
          { nombre: "Básico", puntaje: 2, descriptor: "Análisis superficial." },
          { nombre: "Insuficiente", puntaje: 0, descriptor: "Sin análisis." },
        ],
      },
    ],
  },
};

/**
 * Resultado simulado de "extraer rúbrica con IA". Tiene inconsistencias a propósito para probar el editor:
 * las ponderaciones suman 95 %, un nivel no tiene descriptor y los puntajes del criterio c2 no están ordenados.
 */
export const rubricaExtraidaMock: Rubrica = {
  titulo: "Rúbrica extraída – Laboratorio",
  criterios: [
    {
      id: "c1",
      competencia: "Programación en Python",
      nombre: "Calidad del código",
      ponderacion: 40,
      niveles: [
        { nombre: "Excelente", puntaje: 5, descriptor: "Código modular, legible y con pruebas." },
        { nombre: "Aceptable", puntaje: 3, descriptor: "Código funcional con poca estructura." },
        { nombre: "Insuficiente", puntaje: 1, descriptor: "" },
      ],
    },
    {
      id: "c2",
      competencia: "Comunicación técnica",
      nombre: "Informe del laboratorio",
      ponderacion: 30,
      niveles: [
        { nombre: "Bueno", puntaje: 3, descriptor: "Informe completo con conclusiones claras." },
        { nombre: "Excelente", puntaje: 5, descriptor: "Informe completo, con análisis y referencias." },
      ],
    },
    {
      id: "c3",
      competencia: "Análisis de resultados",
      nombre: "Interpretación de métricas",
      ponderacion: 25,
      niveles: [
        { nombre: "Excelente", puntaje: 5, descriptor: "Interpreta las métricas y propone mejoras." },
        { nombre: "Insuficiente", puntaje: 1, descriptor: "Reporta métricas sin interpretarlas." },
      ],
    },
  ],
};

export const entregasMock: Entrega[] = [
  {
    id: 1,
    estudiante_id: "est-1",
    laboratorio_id: 1,
    rubrica_version_id: 10,
    pdf_path: "entregas/est-1/lab-1/informe.pdf",
    codigo_zip_path: "entregas/est-1/lab-1/codigo.zip",
    github_url: null,
    extras: [],
    creada_en: "2026-09-02T14:00:00Z",
    evaluacion: { id: 6, estado: "publicada", nota: 3.6 },
  },
  {
    id: 2,
    estudiante_id: "est-1",
    laboratorio_id: 2,
    rubrica_version_id: 11,
    pdf_path: "entregas/est-1/lab-2/informe.pdf",
    codigo_zip_path: null,
    github_url: "https://github.com/ana-estudiante/lab2-ml",
    extras: [],
    creada_en: "2026-09-20T14:00:00Z",
    evaluacion: { id: 3, estado: "en_revision", nota: 3.1 },
  },
  {
    id: 3,
    estudiante_id: "est-1",
    laboratorio_id: 3,
    rubrica_version_id: 1,
    pdf_path: "entregas/est-1/lab-3/informe.pdf",
    codigo_zip_path: "entregas/est-1/lab-3/codigo.zip",
    github_url: null,
    extras: ["entregas/est-1/lab-3/captura.png"],
    creada_en: "2026-10-15T14:00:00Z",
    evaluacion: { id: 1, estado: "publicada", nota: 4.2 },
  },
  {
    id: 4,
    estudiante_id: "est-1",
    laboratorio_id: 4,
    rubrica_version_id: 2,
    pdf_path: "entregas/est-1/lab-4/informe.pdf",
    codigo_zip_path: null,
    github_url: "https://github.com/ana-estudiante/rag-local",
    extras: [],
    creada_en: "2026-11-05T14:00:00Z",
    evaluacion: { id: 2, estado: "borrador", nota: 3.8 },
  },
  {
    id: 5,
    estudiante_id: "est-1",
    laboratorio_id: 5,
    rubrica_version_id: 3,
    pdf_path: "entregas/est-1/lab-5/informe.pdf",
    codigo_zip_path: null,
    github_url: null,
    extras: [],
    creada_en: "2026-11-12T14:00:00Z",
    evaluacion: null,
  },
  {
    id: 6,
    estudiante_id: "est-1",
    laboratorio_id: 6,
    rubrica_version_id: 4,
    pdf_path: "entregas/est-1/lab-6/informe.pdf",
    codigo_zip_path: "entregas/est-1/lab-6/codigo.zip",
    github_url: null,
    extras: [],
    creada_en: "2026-11-11T14:00:00Z",
    evaluacion: { id: 4, estado: "error", nota: null },
  },
  {
    id: 7,
    estudiante_id: "est-2",
    laboratorio_id: 3,
    rubrica_version_id: 1,
    pdf_path: "entregas/est-2/lab-3/informe.pdf",
    codigo_zip_path: "entregas/est-2/lab-3/codigo.zip",
    github_url: null,
    extras: [],
    creada_en: "2026-11-09T14:00:00Z",
    evaluacion: { id: 5, estado: "aprobada", nota: 4.6 },
  },
];

/** Cita del mock con la forma de CitaRespuesta (la similitud la calcula el backend). */
function cita(fragmento: string, fuente: string, ubicacion: string, verificada: boolean): Cita {
  return { fragmento, fuente, ubicacion, verificada, similitud: verificada ? 93 : 41 };
}

const criteriosPublicadaMock: EvaluacionCriterio[] = [
  {
    criterio_id: "c1",
    nivel_ia: "Excelente",
    nivel_final: "Excelente",
    puntaje_normalizado: 1,
    citas: [
      cita("Se definió un rol de experto y un formato JSON de salida con dos ejemplos.", "informe", "página 3", true),
      cita('SYSTEM_PROMPT = "Eres un asistente experto en..."', "codigo", "prompts.py:5", true),
    ],
    justificacion: "Los prompts incluyen rol, contexto, formato y ejemplos, como pide el nivel Excelente.",
    fortalezas: ["Uso de ejemplos few-shot", "Formato de salida explícito"],
    debilidades: ["No se versionan los prompts"],
    recomendacion: "Guardar los prompts en archivos con versión para comparar resultados.",
    ajuste_docente: null,
    original_ia: null,
  },
  {
    criterio_id: "c2",
    nivel_ia: "Excelente",
    nivel_final: "Bueno",
    puntaje_normalizado: 0.8,
    citas: [
      cita("La respuesta se valida con un modelo Pydantic antes de guardarla.", "informe", "página 4", true),
      cita("Se implementaron reintentos automáticos con backoff exponencial.", "informe", "página 5", false),
    ],
    justificacion: "Valida la mayoría de las salidas, pero un test de formato falla.",
    fortalezas: ["Validación con Pydantic"],
    debilidades: ["No maneja todos los errores de formato"],
    recomendacion: "Agregar manejo de errores cuando la salida no cumple el esquema.",
    ajuste_docente: "La evidencia de reintentos no aparece en el material y un test falla.",
    original_ia: null,
  },
  {
    criterio_id: "c3",
    nivel_ia: "Bueno",
    nivel_final: "Bueno",
    puntaje_normalizado: 0.8,
    citas: [cita("El modelo inventó una referencia bibliográfica en la prueba 3.", "informe", "página 6", true)],
    justificacion: "Identifica una alucinación con un ejemplo concreto, sin profundizar en sesgos.",
    fortalezas: ["Detecta alucinaciones"],
    debilidades: ["No analiza sesgos"],
    recomendacion: "Incluir un análisis de sesgos con al menos dos casos.",
    ajuste_docente: null,
    original_ia: null,
  },
];

const retroalimentacionMock: Retroalimentacion = {
  aprendizajes_identificados: ["Diseño de prompts estructurados", "Validación de salidas con esquemas"],
  como_aplico_conocimientos: "Aplicó few-shot y validación con Pydantic en un clasificador de textos.",
  aspectos_a_fortalecer: ["Manejo de errores", "Análisis de sesgos"],
  retroalimentacion_general: "Buen trabajo: los prompts son claros y la validación es sólida. Falta robustez ante errores.",
};

/** Textos originales de la IA de un criterio (lo que el docente ve como "propuesta de la IA"). */
function originalIa(criterio: EvaluacionCriterio): RetroalimentacionCriterioIA {
  return {
    justificacion: criterio.justificacion,
    fortalezas: criterio.fortalezas,
    debilidades: criterio.debilidades,
    recomendacion: criterio.recomendacion,
  };
}

const criteriosConOriginal = criteriosPublicadaMock.map((criterio) => ({ ...criterio, original_ia: originalIa(criterio) }));

export const evaluacionPublicadaMock: Evaluacion = {
  id: 1,
  entrega_id: 3,
  estado: "publicada",
  nota: 4.2,
  rubrica_version_id: 103,
  rubrica_version: 1,
  proveedor: "gemini",
  modelo: "gemini-2.0-flash",
  temperatura: 0.1,
  prompt_version: "evaluacion-v1",
  error: null,
  criterios: criteriosConOriginal,
  retroalimentacion: retroalimentacionMock,
  retroalimentacion_ia: retroalimentacionMock,
  creada_en: "2026-10-15T15:00:00Z",
  aprobada_en: "2026-10-16T10:00:00Z",
  publicada_en: "2026-10-16T10:05:00Z",
};

/** Criterios recién salidos de la IA: nivel final = nivel IA y sin ajustes. */
const criteriosBorradorMock: EvaluacionCriterio[] = criteriosConOriginal.map((criterio) => ({
  ...criterio,
  nivel_final: criterio.nivel_ia,
  ajuste_docente: null,
}));

export const evaluacionBorradorMock: Evaluacion = {
  ...evaluacionPublicadaMock,
  id: 2,
  entrega_id: 4,
  rubrica_version_id: 104,
  estado: "borrador",
  nota: 3.8,
  criterios: criteriosBorradorMock,
  aprobada_en: null,
  publicada_en: null,
  creada_en: "2026-11-05T15:00:00Z",
};

const evaluacionEnRevisionMock: Evaluacion = {
  ...evaluacionBorradorMock,
  id: 3,
  entrega_id: 2,
  rubrica_version_id: 102,
  estado: "en_revision",
  nota: 3.1,
  creada_en: "2026-09-20T15:00:00Z",
};

const evaluacionErrorMock: Evaluacion = {
  ...evaluacionBorradorMock,
  id: 4,
  entrega_id: 6,
  rubrica_version_id: 106,
  estado: "error",
  nota: null,
  criterios: [],
  retroalimentacion: null,
  retroalimentacion_ia: null,
  error: "La respuesta del modelo no cumplió el esquema después de 2 reintentos: falta el criterio c3.",
  creada_en: "2026-11-11T15:00:00Z",
};

const evaluacionAprobadaMock: Evaluacion = {
  ...evaluacionBorradorMock,
  id: 5,
  entrega_id: 7,
  rubrica_version_id: 103,
  estado: "aprobada",
  nota: 4.6,
  aprobada_en: "2026-11-10T09:00:00Z",
  creada_en: "2026-11-09T15:00:00Z",
};

export const evaluacionesMock: Evaluacion[] = [
  evaluacionPublicadaMock,
  evaluacionBorradorMock,
  evaluacionEnRevisionMock,
  evaluacionErrorMock,
  evaluacionAprobadaMock,
];

/** Resultado que "devuelve el pipeline" al terminar una evaluación simulada. La nota es un valor fijo de ejemplo. */
export const resultadoSimuladoMock: Pick<Evaluacion, "nota" | "criterios" | "retroalimentacion" | "retroalimentacion_ia"> = {
  nota: 3.8,
  criterios: criteriosBorradorMock,
  retroalimentacion: retroalimentacionMock,
  retroalimentacion_ia: retroalimentacionMock,
};

export const trazaMock: Traza = {
  evaluacion_id: 1,
  entrega_id: 3,
  estado: "publicada",
  nota: 4.2,
  proveedor: "gemini",
  modelo: "gemini-2.0-flash",
  temperatura: 0.1,
  prompt_version: "evaluacion-v1",
  rubrica_version_id: 103,
  rubrica_version: 1,
  eventos: [
    {
      id: 1,
      fecha: "2026-10-15T15:00:00Z",
      usuario: { id: "est-1", nombre: "Ana Estudiante" },
      accion: "lanzar_evaluacion",
      antes: null,
      despues: { estado: "procesando" },
      motivo: null,
    },
    {
      id: 2,
      fecha: "2026-10-15T15:01:10Z",
      usuario: null,
      accion: "evaluacion_completada",
      antes: { estado: "procesando" },
      despues: { estado: "borrador" },
      motivo: null,
    },
    {
      id: 3,
      fecha: "2026-10-16T09:50:00Z",
      usuario: { id: "doc-1", nombre: "Carlos Docente" },
      accion: "ajustar_criterio",
      antes: { criterio_id: "c2", nivel_final: "Excelente" },
      despues: { criterio_id: "c2", nivel_final: "Bueno" },
      motivo: "La evidencia de reintentos no aparece en el material y un test falla.",
    },
    {
      id: 4,
      fecha: "2026-10-16T10:05:00Z",
      usuario: { id: "doc-1", nombre: "Carlos Docente" },
      accion: "publicar",
      antes: { estado: "aprobada" },
      despues: { estado: "publicada" },
      motivo: null,
    },
  ],
};

export const informeMock: Informe = {
  estudiante: { id: "est-1", nombre: "Ana Estudiante" },
  laboratorios_evaluados: 4,
  laboratorios: [
    { laboratorio_id: 1, codigo: "C1-L1", titulo: "Fundamentos de IA y Python", cohorte: "Cohorte 1", cohorte_numero: 1, nota: 3.6, evaluacion_id: 6, publicada_en: "2026-09-05T15:00:00Z" },
    { laboratorio_id: 2, codigo: "C1-L2", titulo: "Aprendizaje automático supervisado", cohorte: "Cohorte 1", cohorte_numero: 1, nota: 3.2, evaluacion_id: 7, publicada_en: "2026-09-25T15:00:00Z" },
    { laboratorio_id: 3, codigo: "C2-L1", titulo: "Ingeniería de prompts con LLMs", cohorte: "Cohorte 2", cohorte_numero: 2, nota: 4.2, evaluacion_id: 1, publicada_en: "2026-10-16T10:05:00Z" },
    { laboratorio_id: 4, codigo: "C2-L2", titulo: "RAG con modelos locales", cohorte: "Cohorte 2", cohorte_numero: 2, nota: 3.8, evaluacion_id: 8, publicada_en: "2026-11-02T15:00:00Z" },
  ],
  promedios_cohorte: [
    { cohorte: "Cohorte 1", cohorte_numero: 1, promedio: 3.4, laboratorios_evaluados: 2 },
    { cohorte: "Cohorte 2", cohorte_numero: 2, promedio: 4.0, laboratorios_evaluados: 2 },
  ],
  promedio_general: 3.7,
  competencias: [
    { competencia: "Fundamentos de IA", promedio: 3.5, nivel_dominio: "medio", criterios_evaluados: 3 },
    { competencia: "Aprendizaje automático", promedio: 2.8, nivel_dominio: "medio", criterios_evaluados: 3 },
    { competencia: "Ingeniería de prompts", promedio: 4.5, nivel_dominio: "alto", criterios_evaluados: 2 },
    { competencia: "LLMs", promedio: 4.0, nivel_dominio: "alto", criterios_evaluados: 2 },
    { competencia: "RAG", promedio: 3.0, nivel_dominio: "medio", criterios_evaluados: 2 },
    { competencia: "Ética y verificación", promedio: 1.8, nivel_dominio: "bajo", criterios_evaluados: 2 },
    { competencia: "Agentes de IA", promedio: null, nivel_dominio: null, criterios_evaluados: 0 },
  ],
  tematicas: [
    { tematica_id: 1, tematica: "Fundamentos de IA", promedio: 3.5, nivel_dominio: "medio", criterios_evaluados: 3 },
    { tematica_id: 2, tematica: "Aprendizaje automático", promedio: 2.8, nivel_dominio: "medio", criterios_evaluados: 3 },
    { tematica_id: 4, tematica: "Ingeniería de prompts", promedio: 4.5, nivel_dominio: "alto", criterios_evaluados: 2 },
    { tematica_id: 7, tematica: "RAG", promedio: 3.0, nivel_dominio: "medio", criterios_evaluados: 2 },
  ],
  evolucion: {
    cohorte_inicial: "Cohorte 1",
    cohorte_final: "Cohorte 2",
    promedio_inicial: 3.4,
    promedio_final: 4.0,
    diferencia: 0.6,
  },
  narrativa: {
    estado: "generada",
    mensaje: null,
    competencias_desarrolladas: [
      "Diseño de prompts estructurados con rol, formato de salida y ejemplos.",
      "Validación de las salidas del LLM con esquemas Pydantic.",
      "Construcción de un flujo RAG básico con un modelo local.",
    ],
    brechas: [
      "Análisis de sesgos y verificación de las respuestas del modelo.",
      "Reporte de métricas en los modelos de aprendizaje supervisado.",
      "Aún no hay evidencia en agentes de IA.",
    ],
    plan_fortalecimiento: [
      {
        accion: "Analizar sesgos en las respuestas de un LLM con al menos dos casos documentados.",
        recurso: "Guía de evaluación de LLMs del curso",
        prioridad: "alta",
        competencia: "Ética y verificación",
      },
      {
        accion: "Reportar precisión, exhaustividad y matriz de confusión del clasificador.",
        recurso: "Documentación de métricas de scikit-learn",
        prioridad: "media",
        competencia: "Aprendizaje automático",
      },
      {
        accion: "Implementar un agente sencillo con una herramienta y documentar sus límites.",
        recurso: "Laboratorio C2-L3 · Agentes de IA",
        prioridad: "media",
        competencia: "Agentes de IA",
      },
      {
        accion: "Comparar dos estrategias de fragmentación de documentos en el flujo RAG.",
        recurso: "Tutorial de RAG con Ollama",
        prioridad: "baja",
        competencia: "RAG",
      },
    ],
    conclusion:
      "La estudiante mejoró de la cohorte 1 a la cohorte 2 y alcanzó un dominio alto en ingeniería de prompts y LLMs. El siguiente paso es fortalecer la verificación ética de las respuestas y empezar a trabajar con agentes.",
    generada_en: FECHA,
  },
  avisos: ["La competencia «Agentes de IA» aún no tiene criterios evaluados."],
};

/** Informe con números válidos pero narrativa en error (est-3): se muestran los números y el mensaje. */
export const informeNarrativaErrorMock: Informe = {
  estudiante: { id: "est-3", nombre: "María Gómez" },
  laboratorios_evaluados: 2,
  laboratorios: [
    { laboratorio_id: 1, codigo: "C1-L1", titulo: "Fundamentos de IA y Python", cohorte: "Cohorte 1", cohorte_numero: 1, nota: 3.4, evaluacion_id: 21, publicada_en: "2026-11-13T21:30:00Z" },
    { laboratorio_id: 3, codigo: "C2-L1", titulo: "Ingeniería de prompts con LLMs", cohorte: "Cohorte 2", cohorte_numero: 2, nota: 2.9, evaluacion_id: 22, publicada_en: "2026-11-14T04:15:00Z" },
  ],
  promedios_cohorte: [
    { cohorte: "Cohorte 1", cohorte_numero: 1, promedio: 3.4, laboratorios_evaluados: 1 },
    { cohorte: "Cohorte 2", cohorte_numero: 2, promedio: 2.9, laboratorios_evaluados: 1 },
  ],
  promedio_general: 3.2,
  competencias: [
    { competencia: "Programación", promedio: 3.2, nivel_dominio: "medio", criterios_evaluados: 3 },
    { competencia: "Ética y verificación", promedio: 2.4, nivel_dominio: "bajo", criterios_evaluados: 2 },
    { competencia: "Arquitectura de software", promedio: null, nivel_dominio: null, criterios_evaluados: 0 },
  ],
  tematicas: [],
  evolucion: { cohorte_inicial: "Cohorte 1", cohorte_final: "Cohorte 2", promedio_inicial: 3.4, promedio_final: 2.9, diferencia: -0.5 },
  narrativa: {
    estado: "error",
    mensaje: "No fue posible generar el análisis narrativo en este momento. Los números del informe son válidos.",
    competencias_desarrolladas: [],
    brechas: [],
    plan_fortalecimiento: [],
    conclusion: null,
    generada_en: null,
  },
  avisos: ["El mapeo a temáticas con IA no está disponible para este estudiante."],
};

/** Informe de un estudiante sin evaluaciones publicadas (est-2 en el modo mock). */
export const informeSinPublicadasMock: Informe = {
  estudiante: { id: "est-2", nombre: "Juan Pérez" },
  laboratorios_evaluados: 0,
  laboratorios: [],
  promedios_cohorte: [
    { cohorte: "Cohorte 1", cohorte_numero: 1, promedio: null, laboratorios_evaluados: 0 },
    { cohorte: "Cohorte 2", cohorte_numero: 2, promedio: null, laboratorios_evaluados: 0 },
  ],
  promedio_general: null,
  competencias: [],
  tematicas: [],
  evolucion: null,
  narrativa: {
    estado: "sin_datos",
    mensaje: "El estudiante aún no tiene evaluaciones publicadas.",
    competencias_desarrolladas: [],
    brechas: [],
    plan_fortalecimiento: [],
    conclusion: null,
    generada_en: null,
  },
  avisos: [],
};

/** Datos de un nodo simulado: las evidencias se escriben como texto y el helper las convierte en objetos. */
interface DatosNodoMock {
  id: string;
  etiqueta: string;
  tipo: TipoNodo;
  nivel_dominio: NivelDominio | null;
  dominio: number | null;
  laboratorios?: string[];
  evidencias?: string[];
  aspectos_por_profundizar?: string[];
}

/** El padre solo existe en el mock para generar las aristas; el backend no envía padre_id. */
interface NodoConPadre {
  padre: string | null;
  nodo: NodoMapa;
}

function nodoMock(padre: string | null, datos: DatosNodoMock): NodoConPadre {
  const laboratorios = datos.laboratorios ?? [];
  const evidencias: EvidenciaMapa[] = (datos.evidencias ?? []).map((fragmento) => ({
    fragmento,
    fuente: "informe",
    ubicacion: null,
    laboratorio: laboratorios[0] ?? "",
    criterio_id: "c1",
  }));
  return {
    padre,
    nodo: {
      id: datos.id,
      tipo: datos.tipo,
      etiqueta: datos.etiqueta,
      dominio: datos.dominio,
      nivel_dominio: datos.nivel_dominio,
      evidencias,
      aspectos_por_profundizar: datos.aspectos_por_profundizar ?? [],
      laboratorios,
    },
  };
}

/** Grafo simulado (RF-09 CA3): temática → subtemas/conceptos/competencias → laboratorios donde se aplicó. Dominio de 0 a 5. */
const nodosConPadreMock: NodoConPadre[] = [
  nodoMock(null, {
    id: "t-fundamentos",
    etiqueta: "Fundamentos de IA",
    tipo: "tematica",
    nivel_dominio: "medio",
    dominio: 3.5,
    laboratorios: ["C1-L1"],
    evidencias: ["Explica la diferencia entre búsqueda no informada e informada con un ejemplo propio."],
    aspectos_por_profundizar: ["Justificar la elección de la heurística con un análisis de costo."],
  }),
  nodoMock("t-fundamentos", {
    id: "k-busqueda",
    etiqueta: "Búsqueda y resolución de problemas",
    tipo: "subtema",
    nivel_dominio: "medio",
    dominio: 3,
    laboratorios: ["C1-L1"],
    evidencias: ["Implementó búsqueda en anchura para el problema del laberinto."],
    aspectos_por_profundizar: ["Comparar A* con búsqueda en anchura en tiempo y memoria."],
  }),
  nodoMock("k-busqueda", {
    id: "l-c1l1-busqueda",
    etiqueta: "C1-L1 · Fundamentos de IA y Python",
    tipo: "laboratorio",
    nivel_dominio: "medio",
    dominio: 3,
    laboratorios: ["C1-L1"],
    evidencias: ["laberinto.py:12-48 — función bfs con cola y conjunto de visitados."],
  }),
  nodoMock("t-fundamentos", {
    id: "k-python",
    etiqueta: "Python para datos",
    tipo: "concepto",
    nivel_dominio: "alto",
    dominio: 4.2,
    laboratorios: ["C1-L1"],
    evidencias: ["Usa listas por comprensión y funciones con type hints en todo el cuaderno."],
  }),
  nodoMock("k-python", {
    id: "l-c1l1-python",
    etiqueta: "C1-L1 · Fundamentos de IA y Python",
    tipo: "laboratorio",
    nivel_dominio: "alto",
    dominio: 4.2,
    laboratorios: ["C1-L1"],
    evidencias: ["utilidades.py — funciones cortas, documentadas y sin errores de ruff."],
  }),
  nodoMock(null, {
    id: "t-ml",
    etiqueta: "Aprendizaje automático",
    tipo: "tematica",
    nivel_dominio: "medio",
    dominio: 2.8,
    laboratorios: ["C1-L2"],
    evidencias: ["Entrenó un árbol de decisión con validación cruzada de 5 particiones."],
    aspectos_por_profundizar: ["Reportar métricas más allá de la exactitud."],
  }),
  nodoMock("t-ml", {
    id: "k-supervisado",
    etiqueta: "Aprendizaje supervisado",
    tipo: "subtema",
    nivel_dominio: "medio",
    dominio: 3.2,
    laboratorios: ["C1-L2"],
    evidencias: ["Separó datos de entrenamiento y prueba antes de normalizar."],
    aspectos_por_profundizar: ["Ajuste de hiperparámetros con búsqueda en rejilla."],
  }),
  nodoMock("k-supervisado", {
    id: "l-c1l2-supervisado",
    etiqueta: "C1-L2 · Aprendizaje automático supervisado",
    tipo: "laboratorio",
    nivel_dominio: "medio",
    dominio: 3.2,
    laboratorios: ["C1-L2"],
    evidencias: ["Informe, pág. 3: «usamos train_test_split con estratificación»."],
  }),
  nodoMock("t-ml", {
    id: "k-metricas",
    etiqueta: "Métricas de evaluación",
    tipo: "concepto",
    nivel_dominio: "bajo",
    dominio: 1.8,
    laboratorios: ["C1-L2"],
    evidencias: ["Solo reporta exactitud con un conjunto de datos desbalanceado."],
    aspectos_por_profundizar: ["Precisión, exhaustividad y matriz de confusión.", "Curva ROC y AUC."],
  }),
  nodoMock("k-metricas", {
    id: "l-c1l2-metricas",
    etiqueta: "C1-L2 · Aprendizaje automático supervisado",
    tipo: "laboratorio",
    nivel_dominio: "bajo",
    dominio: 1.8,
    laboratorios: ["C1-L2"],
    evidencias: ["Informe, pág. 5: «el modelo tiene 92 % de exactitud»."],
    aspectos_por_profundizar: ["Interpretar el resultado frente a la clase minoritaria."],
  }),
  nodoMock(null, {
    id: "t-llms",
    etiqueta: "LLMs",
    tipo: "tematica",
    nivel_dominio: "alto",
    dominio: 4,
    laboratorios: ["C2-L1", "C2-L2"],
    evidencias: ["La respuesta del modelo se valida con Pydantic antes de guardarla."],
    aspectos_por_profundizar: ["Manejo de errores de formato y reintentos."],
  }),
  nodoMock("t-llms", {
    id: "k-salida",
    etiqueta: "Salida estructurada y validación",
    tipo: "concepto",
    nivel_dominio: "alto",
    dominio: 4.5,
    laboratorios: ["C2-L1"],
    evidencias: ["Define un esquema JSON y rechaza respuestas que no lo cumplen."],
  }),
  nodoMock("k-salida", {
    id: "l-c2l1-salida",
    etiqueta: "C2-L1 · Ingeniería de prompts con LLMs",
    tipo: "laboratorio",
    nivel_dominio: "alto",
    dominio: 4.5,
    laboratorios: ["C2-L1"],
    evidencias: ["cliente_llm.py:30 — RespuestaSchema.model_validate_json(texto)."],
  }),
  nodoMock("t-llms", {
    id: "k-parametros",
    etiqueta: "Parámetros de generación",
    tipo: "concepto",
    nivel_dominio: "medio",
    dominio: 3,
    laboratorios: ["C2-L1", "C2-L2"],
    evidencias: ["Fija temperature en 0,2 para respuestas reproducibles."],
    aspectos_por_profundizar: ["Explicar el efecto de top_p y del tamaño de contexto."],
  }),
  nodoMock("k-parametros", {
    id: "l-c2l1-parametros",
    etiqueta: "C2-L1 · Ingeniería de prompts con LLMs",
    tipo: "laboratorio",
    nivel_dominio: "medio",
    dominio: 3,
    laboratorios: ["C2-L1"],
    evidencias: ["Informe, pág. 2: tabla que compara temperature 0,2 y 0,8."],
  }),
  nodoMock(null, {
    id: "t-prompts",
    etiqueta: "Ingeniería de prompts",
    tipo: "tematica",
    nivel_dominio: "alto",
    dominio: 4.5,
    laboratorios: ["C2-L1"],
    evidencias: ["Se definió un rol de experto y un formato JSON de salida con dos ejemplos."],
    aspectos_por_profundizar: ["Versionado de prompts."],
  }),
  nodoMock("t-prompts", {
    id: "k-fewshot",
    etiqueta: "Few-shot",
    tipo: "concepto",
    nivel_dominio: "alto",
    dominio: 5,
    laboratorios: ["C2-L1"],
    evidencias: ["Uso de dos ejemplos representativos en el prompt."],
  }),
  nodoMock("k-fewshot", {
    id: "l-c2l1-fewshot",
    etiqueta: "C2-L1 · Ingeniería de prompts con LLMs",
    tipo: "laboratorio",
    nivel_dominio: "alto",
    dominio: 5,
    laboratorios: ["C2-L1"],
    evidencias: ["prompts/clasificar.md — sección «Ejemplos» con dos casos."],
  }),
  nodoMock("t-prompts", {
    id: "k-rol",
    etiqueta: "Rol y formato de salida",
    tipo: "concepto",
    nivel_dominio: "alto",
    dominio: 4.2,
    laboratorios: ["C2-L1"],
    evidencias: ["El prompt fija un rol de evaluador y exige salida en JSON."],
  }),
  nodoMock("k-rol", {
    id: "l-c2l1-rol",
    etiqueta: "C2-L1 · Ingeniería de prompts con LLMs",
    tipo: "laboratorio",
    nivel_dominio: "alto",
    dominio: 4.2,
    laboratorios: ["C2-L1"],
    evidencias: ["prompts/clasificar.md:1-8 — instrucciones de rol y formato."],
  }),
  nodoMock("t-prompts", {
    id: "k-versionado",
    etiqueta: "Versionado de prompts",
    tipo: "concepto",
    nivel_dominio: null,
    dominio: null,
    aspectos_por_profundizar: ["Guardar cada prompt con un número de versión y registrar los cambios."],
  }),
  nodoMock(null, {
    id: "t-locales",
    etiqueta: "Modelos locales (Ollama/LM Studio)",
    tipo: "tematica",
    nivel_dominio: "medio",
    dominio: 3,
    laboratorios: ["C2-L2"],
    evidencias: ["Ejecutó llama3 en Ollama y lo consumió desde Python."],
    aspectos_por_profundizar: ["Comparar latencia y calidad frente a un modelo en la nube."],
  }),
  nodoMock("t-locales", {
    id: "k-ollama",
    etiqueta: "Ejecución con Ollama",
    tipo: "concepto",
    nivel_dominio: "medio",
    dominio: 3,
    laboratorios: ["C2-L2"],
    evidencias: ["Documenta los comandos para descargar y servir el modelo."],
  }),
  nodoMock("k-ollama", {
    id: "l-c2l2-ollama",
    etiqueta: "C2-L2 · RAG con modelos locales",
    tipo: "laboratorio",
    nivel_dominio: "medio",
    dominio: 3,
    laboratorios: ["C2-L2"],
    evidencias: ["README.md — sección «Cómo ejecutar el modelo local»."],
  }),
  nodoMock(null, {
    id: "t-rag",
    etiqueta: "RAG",
    tipo: "tematica",
    nivel_dominio: "medio",
    dominio: 3,
    laboratorios: ["C2-L2"],
    evidencias: ["Construyó un flujo de recuperación con un índice vectorial local."],
    aspectos_por_profundizar: ["Evaluar la calidad de la recuperación con preguntas de prueba."],
  }),
  nodoMock("t-rag", {
    id: "k-embeddings",
    etiqueta: "Embeddings y búsqueda semántica",
    tipo: "concepto",
    nivel_dominio: "medio",
    dominio: 3.2,
    laboratorios: ["C2-L2"],
    evidencias: ["Genera embeddings con un modelo local y busca por similitud coseno."],
  }),
  nodoMock("k-embeddings", {
    id: "l-c2l2-embeddings",
    etiqueta: "C2-L2 · RAG con modelos locales",
    tipo: "laboratorio",
    nivel_dominio: "medio",
    dominio: 3.2,
    laboratorios: ["C2-L2"],
    evidencias: ["indice.py:20-55 — creación del índice y consulta top-k."],
  }),
  nodoMock("t-rag", {
    id: "k-fragmentacion",
    etiqueta: "Fragmentación de documentos",
    tipo: "concepto",
    nivel_dominio: "bajo",
    dominio: 2,
    laboratorios: ["C2-L2"],
    evidencias: ["Usa fragmentos de tamaño fijo sin solapamiento."],
    aspectos_por_profundizar: ["Comparar dos estrategias de fragmentación y su efecto en las respuestas."],
  }),
  nodoMock("k-fragmentacion", {
    id: "l-c2l2-fragmentacion",
    etiqueta: "C2-L2 · RAG con modelos locales",
    tipo: "laboratorio",
    nivel_dominio: "bajo",
    dominio: 2,
    laboratorios: ["C2-L2"],
    evidencias: ["indice.py:8 — CHUNK = 500 sin justificar el valor."],
  }),
  nodoMock(null, {
    id: "t-etica",
    etiqueta: "Ética y verificación",
    tipo: "tematica",
    nivel_dominio: "bajo",
    dominio: 1.8,
    laboratorios: ["C2-L1"],
    evidencias: ["El modelo inventó una referencia bibliográfica en la prueba 3 y no se detectó."],
    aspectos_por_profundizar: ["Análisis de sesgos.", "Verificación de las respuestas contra fuentes."],
  }),
  nodoMock("t-etica", {
    id: "k-alucinaciones",
    etiqueta: "Detección de alucinaciones",
    tipo: "concepto",
    nivel_dominio: "bajo",
    dominio: 2,
    laboratorios: ["C2-L1"],
    evidencias: ["Menciona las alucinaciones, pero no propone una forma de detectarlas."],
    aspectos_por_profundizar: ["Contrastar las citas del modelo con el material original."],
  }),
  nodoMock("k-alucinaciones", {
    id: "l-c2l1-alucinaciones",
    etiqueta: "C2-L1 · Ingeniería de prompts con LLMs",
    tipo: "laboratorio",
    nivel_dominio: "bajo",
    dominio: 2,
    laboratorios: ["C2-L1"],
    evidencias: ["Informe, pág. 6: «el modelo a veces inventa datos»."],
  }),
  nodoMock("t-etica", {
    id: "k-sesgos",
    etiqueta: "Análisis de sesgos",
    tipo: "concepto",
    nivel_dominio: null,
    dominio: null,
    aspectos_por_profundizar: ["Documentar al menos dos casos de sesgo en las respuestas de un LLM."],
  }),
  nodoMock(null, {
    id: "t-agentes",
    etiqueta: "Agentes de IA",
    tipo: "tematica",
    nivel_dominio: null,
    dominio: null,
    aspectos_por_profundizar: ["Aún no hay evaluaciones publicadas en esta temática."],
  }),
  nodoMock(null, {
    id: "t-vision",
    etiqueta: "Visión artificial",
    tipo: "tematica",
    nivel_dominio: null,
    dominio: null,
    aspectos_por_profundizar: ["Aún no hay evaluaciones publicadas en esta temática."],
  }),
];


/** Competencia de ejemplo para tener los cinco tipos de nodo del backend. */
nodosConPadreMock.push(
  nodoMock("t-fundamentos", {
    id: "c-programacion",
    etiqueta: "Programación en Python",
    tipo: "competencia",
    nivel_dominio: "alto",
    dominio: 4.3,
    laboratorios: ["C1-L1"],
    evidencias: ["Funciones cortas, con type hints y sin errores de ruff."],
  }),
);

/** Mapa de est-1: aristas padre → hijo más una relación transversal (Ollama → laboratorio de RAG). */
export const mapaMock: Mapa = {
  nodos: nodosConPadreMock.map(({ nodo }) => nodo),
  aristas: [
    ...nodosConPadreMock.flatMap(({ padre, nodo }) => (padre === null ? [] : [{ origen: padre, destino: nodo.id }])),
    { origen: "k-ollama", destino: "l-c2l2-embeddings" },
  ],
  avisos: ["Las temáticas sin evaluaciones publicadas aparecen sin nivel de dominio."],
};

/** Mapa de un estudiante sin evaluaciones publicadas (est-2 en el modo mock). */
export const mapaVacioMock: Mapa = { nodos: [], aristas: [], avisos: [] };

/** Mapa cuando el mapeo de la IA no está disponible: agrupado competencia → criterio → laboratorio, con aviso. */
export const mapaConAvisosMock: Mapa = {
  nodos: [
    { id: "competencia:programacion", tipo: "competencia", etiqueta: "Programación", dominio: 3.2, nivel_dominio: "medio",
      evidencias: [], aspectos_por_profundizar: ["Agregar pruebas automatizadas."], laboratorios: ["C1-L1", "C2-L1"] },
    { id: "concepto:programacion:c1", tipo: "concepto", etiqueta: "Calidad del código", dominio: 3.5, nivel_dominio: "medio",
      evidencias: [{ fragmento: "Las funciones tienen type hints y docstrings.", fuente: "codigo", ubicacion: "utilidades.py:10", laboratorio: "C1-L1", criterio_id: "c1" }],
      aspectos_por_profundizar: [], laboratorios: ["C1-L1"] },
    { id: "lab:C1-L1", tipo: "laboratorio", etiqueta: "C1-L1 · Fundamentos de IA y Python", dominio: 3.4, nivel_dominio: "medio",
      evidencias: [], aspectos_por_profundizar: [], laboratorios: ["C1-L1"] },
    { id: "competencia:etica", tipo: "competencia", etiqueta: "Ética y verificación", dominio: 2.4, nivel_dominio: "bajo",
      evidencias: [], aspectos_por_profundizar: ["Verificar las respuestas del modelo con fuentes."], laboratorios: ["C2-L1"] },
    { id: "lab:C2-L1", tipo: "laboratorio", etiqueta: "C2-L1 · Ingeniería de prompts con LLMs", dominio: 2.9, nivel_dominio: "bajo",
      evidencias: [], aspectos_por_profundizar: [], laboratorios: ["C2-L1"] },
    { id: "competencia:arquitectura", tipo: "competencia", etiqueta: "Arquitectura de software", dominio: null, nivel_dominio: null,
      evidencias: [], aspectos_por_profundizar: [], laboratorios: [] },
  ],
  aristas: [
    { origen: "competencia:programacion", destino: "concepto:programacion:c1" },
    { origen: "concepto:programacion:c1", destino: "lab:C1-L1" },
    { origen: "competencia:programacion", destino: "lab:C2-L1" },
    { origen: "competencia:etica", destino: "lab:C2-L1" },
  ],
  avisos: [
    "El mapeo a temáticas con IA no está disponible: el mapa se agrupa por competencia → criterio → laboratorio.",
  ],
};

/**
 * Configuración de IA (ConfigIARespuesta). Modelos probados y sin probar en ambos proveedores.
 * En el modo mock, probar la conexión con "qwen2.5" falla (ok: false) para ver ese caso.
 */
export const configIAMock: ConfigIA = {
  proveedor: "gemini",
  modelo: "gemini-3.5-flash-lite",
  temperatura: 0.1,
  origen: "base_de_datos",
  modelo_permitido: true,
  actualizado_por: { id: "adm-1", nombre: "Admin Demo" },
  actualizado_en: FECHA,
  temperatura_maxima: 0.2,
  claves: {
    gemini_api_key_configurada: true,
    openai_compat_api_key_configurada: false,
    openai_compat_base_url_configurada: true,
  },
  proveedores_permitidos: [
    {
      proveedor: "gemini",
      etiqueta: "Google Gemini",
      modelos: ["gemini-3.5-flash-lite", "gemini-3.5-flash"],
      modelos_probados: ["gemini-3.5-flash-lite"],
    },
    {
      proveedor: "openai_compat",
      etiqueta: "OpenAI-compatible (Ollama, Groq, OpenRouter)",
      modelos: ["llama3.1:8b", "qwen2.5"],
      modelos_probados: ["llama3.1:8b"],
    },
  ],
  versiones_prompt: {
    evaluacion: "evaluacion-v1",
    extraer_rubrica: "1.0",
    informe_narrativo: "informe-v1",
    mapeo_tematicas: null,
  },
};

/** Modelo con el que la prueba de conexión simulada falla. */
export const MODELO_FALLA_MOCK = "qwen2.5";
