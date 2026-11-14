// Datos simulados con la misma forma del contrato §11. Las notas son valores fijos:
// el frontend nunca calcula la nota (la calcula el backend).
import type {
  Cohorte,
  ConfigIA,
  Entrega,
  Evaluacion,
  Informe,
  Mapa,
  NodoMapa,
  Perfil,
  Rol,
  Rubrica,
  RubricaVersion,
  Traza,
  Usuario,
  VerificacionCodigo,
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
];

export const cohortesMock: Cohorte[] = [
  {
    id: "coh-1",
    nombre: "Cohorte 1",
    numero: 1,
    laboratorios: [
      {
        id: "lab-1",
        cohorte_id: "coh-1",
        codigo: "C1-L1",
        titulo: "Fundamentos de IA y Python",
        descripcion: "Primer acercamiento a la IA con cuadernos de Python.",
        objetivos: "Comprender conceptos básicos de IA y escribir scripts simples en Python.",
      },
      {
        id: "lab-2",
        cohorte_id: "coh-1",
        codigo: "C1-L2",
        titulo: "Aprendizaje automático supervisado",
        descripcion: "Entrenar y evaluar un clasificador con scikit-learn.",
        objetivos: "Preparar datos, entrenar un modelo y reportar métricas.",
      },
    ],
  },
  {
    id: "coh-2",
    nombre: "Cohorte 2",
    numero: 2,
    laboratorios: [
      {
        id: "lab-3",
        cohorte_id: "coh-2",
        codigo: "C2-L1",
        titulo: "Ingeniería de prompts con LLMs",
        descripcion: "Diseño de prompts y salidas estructuradas con un LLM.",
        objetivos: "Diseñar prompts reproducibles y validar las salidas con esquemas.",
      },
      {
        id: "lab-4",
        cohorte_id: "coh-2",
        codigo: "C2-L2",
        titulo: "RAG con modelos locales",
        descripcion: "Recuperación aumentada con Ollama y una base vectorial.",
        objetivos: "Construir un flujo RAG y evaluar la calidad de las respuestas.",
      },
      {
        id: "lab-5",
        cohorte_id: "coh-2",
        codigo: "C2-L3",
        titulo: "Agentes de IA",
        descripcion: "Agente con herramientas para resolver tareas de varios pasos.",
        objetivos: "Implementar un agente con herramientas y documentar sus límites.",
      },
      {
        id: "lab-6",
        cohorte_id: "coh-2",
        codigo: "C2-L4",
        titulo: "Evaluación de modelos de lenguaje",
        descripcion: "Comparar dos LLMs con un conjunto de pruebas propio.",
        objetivos: "Definir métricas, ejecutar pruebas reproducibles y reportar hallazgos.",
      },
      {
        id: "lab-7",
        cohorte_id: "coh-2",
        codigo: "C2-L5",
        titulo: "Proyecto integrador",
        descripcion: "Aplicación completa que integra los temas del curso.",
        objetivos: "Integrar prompts, RAG y agentes en una solución documentada.",
      },
    ],
  },
];

/** Laboratorios sin rúbrica vigente en el modo mock (para probar RF-02 CA2). */
export const laboratoriosSinRubricaMock: string[] = ["lab-7"];

export const rubricaVersionMock: RubricaVersion = {
  id: "rv-1",
  rubrica_id: "rub-1",
  laboratorio_id: "lab-3",
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
    id: "ent-1",
    estudiante_id: "est-1",
    laboratorio_id: "lab-1",
    rubrica_version_id: "rv-0",
    pdf_path: "entregas/est-1/lab-1/informe.pdf",
    codigo_zip_path: "entregas/est-1/lab-1/codigo.zip",
    github_url: null,
    extras: [],
    creada_en: "2026-09-02T14:00:00Z",
    evaluacion: { id: "eva-0", estado: "publicada", nota: 3.6 },
  },
  {
    id: "ent-2",
    estudiante_id: "est-1",
    laboratorio_id: "lab-2",
    rubrica_version_id: "rv-0b",
    pdf_path: "entregas/est-1/lab-2/informe.pdf",
    codigo_zip_path: null,
    github_url: "https://github.com/ana-estudiante/lab2-ml",
    extras: [],
    creada_en: "2026-09-20T14:00:00Z",
    evaluacion: { id: "eva-3", estado: "en_revision", nota: 3.1 },
  },
  {
    id: "ent-3",
    estudiante_id: "est-1",
    laboratorio_id: "lab-3",
    rubrica_version_id: "rv-1",
    pdf_path: "entregas/est-1/lab-3/informe.pdf",
    codigo_zip_path: "entregas/est-1/lab-3/codigo.zip",
    github_url: null,
    extras: ["entregas/est-1/lab-3/captura.png"],
    creada_en: "2026-10-15T14:00:00Z",
    evaluacion: { id: "eva-1", estado: "publicada", nota: 4.2 },
  },
  {
    id: "ent-4",
    estudiante_id: "est-1",
    laboratorio_id: "lab-4",
    rubrica_version_id: "rv-2",
    pdf_path: "entregas/est-1/lab-4/informe.pdf",
    codigo_zip_path: null,
    github_url: "https://github.com/ana-estudiante/rag-local",
    extras: [],
    creada_en: "2026-11-05T14:00:00Z",
    evaluacion: { id: "eva-2", estado: "borrador", nota: 3.8 },
  },
  {
    id: "ent-5",
    estudiante_id: "est-1",
    laboratorio_id: "lab-5",
    rubrica_version_id: "rv-3",
    pdf_path: "entregas/est-1/lab-5/informe.pdf",
    codigo_zip_path: null,
    github_url: null,
    extras: [],
    creada_en: "2026-11-12T14:00:00Z",
    evaluacion: null,
  },
  {
    id: "ent-6",
    estudiante_id: "est-1",
    laboratorio_id: "lab-6",
    rubrica_version_id: "rv-4",
    pdf_path: "entregas/est-1/lab-6/informe.pdf",
    codigo_zip_path: "entregas/est-1/lab-6/codigo.zip",
    github_url: null,
    extras: [],
    creada_en: "2026-11-11T14:00:00Z",
    evaluacion: { id: "eva-4", estado: "error", nota: null },
  },
  {
    id: "ent-7",
    estudiante_id: "est-2",
    laboratorio_id: "lab-3",
    rubrica_version_id: "rv-1",
    pdf_path: "entregas/est-2/lab-3/informe.pdf",
    codigo_zip_path: "entregas/est-2/lab-3/codigo.zip",
    github_url: null,
    extras: [],
    creada_en: "2026-11-09T14:00:00Z",
    evaluacion: { id: "eva-5", estado: "aprobada", nota: 4.6 },
  },
];

const verificacionMock: VerificacionCodigo = {
  sintaxis: [
    { archivo: "main.py", valido: true, error: null },
    { archivo: "prompts.py", valido: true, error: null },
  ],
  ruff: { errores: 1, advertencias: 3, mensajes: ["prompts.py:12: F401 'os' importado y no usado"] },
  complejidad: { promedio: 2.4, maxima: 6, rango: "A" },
  tests: { ejecutados: true, aprobados: 4, fallidos: 1, detalle: "test_formato_json falló" },
  metricas: {
    archivos: 6,
    lineas: 312,
    tiene_readme: true,
    tiene_requirements: true,
    tiene_tests: true,
    lenguajes: ["Python"],
  },
  sandbox: "subprocess",
  limitaciones: ["Sin aislamiento de red completo en este entorno."],
};

export const evaluacionPublicadaMock: Evaluacion = {
  id: "eva-1",
  entrega_id: "ent-3",
  estudiante_id: "est-1",
  laboratorio_id: "lab-3",
  estado: "publicada",
  nota: 4.2,
  proveedor: "gemini",
  modelo: "gemini-2.0-flash",
  prompt_version: "evaluacion-v1",
  temperatura: 0.1,
  rubrica_version: 1,
  criterios: [
    {
      criterio_id: "c1",
      nombre: "Diseño de prompts",
      competencia: "Ingeniería de prompts",
      ponderacion: 40,
      nivel_ia: "Excelente",
      nivel_final: "Excelente",
      evidencias: [
        {
          fragmento: "Se definió un rol de experto y un formato JSON de salida con dos ejemplos.",
          fuente: "informe",
          ubicacion: "página 3",
          verificada: true,
        },
        {
          fragmento: "SYSTEM_PROMPT = \"Eres un asistente experto en...\"",
          fuente: "codigo",
          ubicacion: "prompts.py:5",
          verificada: true,
        },
      ],
      justificacion: "Los prompts incluyen rol, contexto, formato y ejemplos, como pide el nivel Excelente.",
      fortalezas: ["Uso de ejemplos few-shot", "Formato de salida explícito"],
      debilidades: ["No se versionan los prompts"],
      recomendacion: "Guardar los prompts en archivos con versión para comparar resultados.",
      ajuste_docente: null,
    },
    {
      criterio_id: "c2",
      nombre: "Salidas estructuradas y validación",
      competencia: "LLMs",
      ponderacion: 35,
      nivel_ia: "Excelente",
      nivel_final: "Bueno",
      evidencias: [
        {
          fragmento: "La respuesta se valida con un modelo Pydantic antes de guardarla.",
          fuente: "informe",
          ubicacion: "página 4",
          verificada: true,
        },
        {
          fragmento: "Se implementaron reintentos automáticos con backoff exponencial.",
          fuente: "informe",
          ubicacion: "página 5",
          verificada: false,
        },
      ],
      justificacion: "Valida la mayoría de las salidas, pero un test de formato falla.",
      fortalezas: ["Validación con Pydantic"],
      debilidades: ["No maneja todos los errores de formato"],
      recomendacion: "Agregar manejo de errores cuando la salida no cumple el esquema.",
      ajuste_docente: "La evidencia de reintentos no aparece en el material y un test falla.",
    },
    {
      criterio_id: "c3",
      nombre: "Análisis crítico de resultados",
      competencia: "Ética y verificación",
      ponderacion: 25,
      nivel_ia: "Bueno",
      nivel_final: "Bueno",
      evidencias: [
        {
          fragmento: "El modelo inventó una referencia bibliográfica en la prueba 3.",
          fuente: "informe",
          ubicacion: "página 6",
          verificada: true,
        },
      ],
      justificacion: "Identifica una alucinación con un ejemplo concreto, sin profundizar en sesgos.",
      fortalezas: ["Detecta alucinaciones"],
      debilidades: ["No analiza sesgos"],
      recomendacion: "Incluir un análisis de sesgos con al menos dos casos.",
      ajuste_docente: null,
    },
  ],
  aprendizajes_identificados: ["Diseño de prompts estructurados", "Validación de salidas con esquemas"],
  como_aplico_conocimientos: "Aplicó few-shot y validación con Pydantic en un clasificador de textos.",
  aspectos_a_fortalecer: ["Manejo de errores", "Análisis de sesgos"],
  retroalimentacion_general: "Buen trabajo: los prompts son claros y la validación es sólida. Falta robustez ante errores.",
  verificacion: verificacionMock,
  error: null,
  creada_en: "2026-10-15T15:00:00Z",
  aprobada_en: "2026-10-16T10:00:00Z",
  publicada_en: "2026-10-16T10:05:00Z",
};

export const evaluacionBorradorMock: Evaluacion = {
  ...evaluacionPublicadaMock,
  id: "eva-2",
  entrega_id: "ent-4",
  laboratorio_id: "lab-4",
  estado: "borrador",
  nota: 3.8,
  criterios: evaluacionPublicadaMock.criterios.map((criterio) => ({
    ...criterio,
    nivel_final: criterio.nivel_ia,
    ajuste_docente: null,
  })),
  aprobada_en: null,
  publicada_en: null,
  creada_en: "2026-11-05T15:00:00Z",
};

const evaluacionEnRevisionMock: Evaluacion = {
  ...evaluacionBorradorMock,
  id: "eva-3",
  entrega_id: "ent-2",
  laboratorio_id: "lab-2",
  estado: "en_revision",
  nota: 3.1,
  creada_en: "2026-09-20T15:00:00Z",
};

const evaluacionErrorMock: Evaluacion = {
  ...evaluacionBorradorMock,
  id: "eva-4",
  entrega_id: "ent-6",
  laboratorio_id: "lab-6",
  estado: "error",
  nota: null,
  criterios: [],
  aprendizajes_identificados: [],
  como_aplico_conocimientos: "",
  aspectos_a_fortalecer: [],
  retroalimentacion_general: "",
  verificacion: null,
  error: "La respuesta del modelo no cumplió el esquema después de 2 reintentos: falta el criterio c3.",
  creada_en: "2026-11-11T15:00:00Z",
};

const evaluacionAprobadaMock: Evaluacion = {
  ...evaluacionBorradorMock,
  id: "eva-5",
  entrega_id: "ent-7",
  estudiante_id: "est-2",
  laboratorio_id: "lab-3",
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
export const resultadoSimuladoMock: Pick<
  Evaluacion,
  | "nota"
  | "criterios"
  | "aprendizajes_identificados"
  | "como_aplico_conocimientos"
  | "aspectos_a_fortalecer"
  | "retroalimentacion_general"
  | "verificacion"
> = {
  nota: 3.8,
  criterios: evaluacionBorradorMock.criterios,
  aprendizajes_identificados: evaluacionBorradorMock.aprendizajes_identificados,
  como_aplico_conocimientos: evaluacionBorradorMock.como_aplico_conocimientos,
  aspectos_a_fortalecer: evaluacionBorradorMock.aspectos_a_fortalecer,
  retroalimentacion_general: evaluacionBorradorMock.retroalimentacion_general,
  verificacion: verificacionMock,
};

export const trazaMock: Traza = {
  evaluacion_id: "eva-1",
  proveedor: "gemini",
  modelo: "gemini-2.0-flash",
  prompt_version: "evaluacion-v1",
  temperatura: 0.1,
  rubrica_version: 1,
  respuesta_cruda: { criterios: [{ criterio_id: "c1", nivel_elegido: "Excelente" }] },
  verificacion: verificacionMock,
  auditoria: [
    {
      id: "aud-1",
      usuario_id: "doc-1",
      usuario_nombre: "Carlos Docente",
      accion: "ajuste_criterio",
      antes: { criterio_id: "c2", nivel_final: "Excelente" },
      despues: { criterio_id: "c2", nivel_final: "Bueno" },
      motivo: "La evidencia de reintentos no aparece en el material y un test falla.",
      creado_en: "2026-10-16T09:50:00Z",
    },
    {
      id: "aud-2",
      usuario_id: "doc-1",
      usuario_nombre: "Carlos Docente",
      accion: "publicar",
      antes: { estado: "aprobada" },
      despues: { estado: "publicada" },
      motivo: null,
      creado_en: "2026-10-16T10:05:00Z",
    },
  ],
};

export const informeMock: Informe = {
  estudiante_id: "est-1",
  estudiante_nombre: "Ana Estudiante",
  notas_laboratorio: [
    { laboratorio_id: "lab-1", codigo: "C1-L1", titulo: "Fundamentos de IA y Python", cohorte: 1, evaluacion_id: "eva-0", nota: 3.6 },
    { laboratorio_id: "lab-2", codigo: "C1-L2", titulo: "Aprendizaje automático supervisado", cohorte: 1, evaluacion_id: "eva-2", nota: 3.2 },
    { laboratorio_id: "lab-3", codigo: "C2-L1", titulo: "Ingeniería de prompts con LLMs", cohorte: 2, evaluacion_id: "eva-1", nota: 4.2 },
    { laboratorio_id: "lab-4", codigo: "C2-L2", titulo: "RAG con modelos locales", cohorte: 2, evaluacion_id: "eva-3", nota: 3.8 },
  ],
  promedios_cohorte: [
    { cohorte: 1, promedio: 3.4 },
    { cohorte: 2, promedio: 4.0 },
  ],
  promedio_general: 3.7,
  dominio_competencias: [
    { competencia: "Fundamentos de IA", dominio: 0.7, nivel: "medio" },
    { competencia: "Aprendizaje automático", dominio: 0.55, nivel: "medio" },
    { competencia: "Ingeniería de prompts", dominio: 0.9, nivel: "alto" },
    { competencia: "LLMs", dominio: 0.8, nivel: "alto" },
    { competencia: "RAG", dominio: 0.6, nivel: "medio" },
    { competencia: "Ética y verificación", dominio: 0.35, nivel: "bajo" },
    { competencia: "Agentes de IA", dominio: 0, nivel: "sin_evidencia" },
  ],
  evolucion: { cohorte_1: 3.4, cohorte_2: 4.0, diferencia: 0.6 },
  narrativa: {
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
  },
  generado_en: FECHA,
};

/** Informe de un estudiante sin evaluaciones publicadas (est-2 en el modo mock). */
export const informeSinPublicadasMock: Informe = {
  estudiante_id: "est-2",
  estudiante_nombre: "Juan Pérez",
  notas_laboratorio: [],
  promedios_cohorte: [
    { cohorte: 1, promedio: null },
    { cohorte: 2, promedio: null },
  ],
  promedio_general: null,
  dominio_competencias: [],
  evolucion: { cohorte_1: null, cohorte_2: null, diferencia: null },
  narrativa: null,
  generado_en: FECHA,
};

type NodoMapaMock = Omit<NodoMapa, "padre_id" | "laboratorios" | "evidencias" | "por_profundizar"> &
  Partial<Pick<NodoMapa, "laboratorios" | "evidencias" | "por_profundizar">>;

/** Crea un nodo del mapa simulado con listas vacías por defecto. */
function nodoMock(padre_id: string | null, datos: NodoMapaMock): NodoMapa {
  return { laboratorios: [], evidencias: [], por_profundizar: [], ...datos, padre_id };
}

/** Grafo simulado (RF-09 CA3): temática → subtemas/conceptos → laboratorios donde se aplicó. */
const nodosMapaMock: NodoMapa[] = [
  nodoMock(null, {
    id: "t-fundamentos",
    etiqueta: "Fundamentos de IA",
    tipo: "tematica",
    nivel: "medio",
    dominio: 0.7,
    laboratorios: ["C1-L1"],
    evidencias: ["Explica la diferencia entre búsqueda no informada e informada con un ejemplo propio."],
    por_profundizar: ["Justificar la elección de la heurística con un análisis de costo."],
  }),
  nodoMock("t-fundamentos", {
    id: "k-busqueda",
    etiqueta: "Búsqueda y resolución de problemas",
    tipo: "concepto",
    nivel: "medio",
    dominio: 0.6,
    laboratorios: ["C1-L1"],
    evidencias: ["Implementó búsqueda en anchura para el problema del laberinto."],
    por_profundizar: ["Comparar A* con búsqueda en anchura en tiempo y memoria."],
  }),
  nodoMock("k-busqueda", {
    id: "l-c1l1-busqueda",
    etiqueta: "C1-L1 · Fundamentos de IA y Python",
    tipo: "laboratorio",
    nivel: "medio",
    dominio: 0.6,
    laboratorios: ["C1-L1"],
    evidencias: ["laberinto.py:12-48 — función bfs con cola y conjunto de visitados."],
  }),
  nodoMock("t-fundamentos", {
    id: "k-python",
    etiqueta: "Python para datos",
    tipo: "concepto",
    nivel: "alto",
    dominio: 0.85,
    laboratorios: ["C1-L1"],
    evidencias: ["Usa listas por comprensión y funciones con type hints en todo el cuaderno."],
  }),
  nodoMock("k-python", {
    id: "l-c1l1-python",
    etiqueta: "C1-L1 · Fundamentos de IA y Python",
    tipo: "laboratorio",
    nivel: "alto",
    dominio: 0.85,
    laboratorios: ["C1-L1"],
    evidencias: ["utilidades.py — funciones cortas, documentadas y sin errores de ruff."],
  }),
  nodoMock(null, {
    id: "t-ml",
    etiqueta: "Aprendizaje automático",
    tipo: "tematica",
    nivel: "medio",
    dominio: 0.55,
    laboratorios: ["C1-L2"],
    evidencias: ["Entrenó un árbol de decisión con validación cruzada de 5 particiones."],
    por_profundizar: ["Reportar métricas más allá de la exactitud."],
  }),
  nodoMock("t-ml", {
    id: "k-supervisado",
    etiqueta: "Aprendizaje supervisado",
    tipo: "concepto",
    nivel: "medio",
    dominio: 0.65,
    laboratorios: ["C1-L2"],
    evidencias: ["Separó datos de entrenamiento y prueba antes de normalizar."],
    por_profundizar: ["Ajuste de hiperparámetros con búsqueda en rejilla."],
  }),
  nodoMock("k-supervisado", {
    id: "l-c1l2-supervisado",
    etiqueta: "C1-L2 · Aprendizaje automático supervisado",
    tipo: "laboratorio",
    nivel: "medio",
    dominio: 0.65,
    laboratorios: ["C1-L2"],
    evidencias: ["Informe, pág. 3: «usamos train_test_split con estratificación»."],
  }),
  nodoMock("t-ml", {
    id: "k-metricas",
    etiqueta: "Métricas de evaluación",
    tipo: "concepto",
    nivel: "bajo",
    dominio: 0.35,
    laboratorios: ["C1-L2"],
    evidencias: ["Solo reporta exactitud con un conjunto de datos desbalanceado."],
    por_profundizar: ["Precisión, exhaustividad y matriz de confusión.", "Curva ROC y AUC."],
  }),
  nodoMock("k-metricas", {
    id: "l-c1l2-metricas",
    etiqueta: "C1-L2 · Aprendizaje automático supervisado",
    tipo: "laboratorio",
    nivel: "bajo",
    dominio: 0.35,
    laboratorios: ["C1-L2"],
    evidencias: ["Informe, pág. 5: «el modelo tiene 92 % de exactitud»."],
    por_profundizar: ["Interpretar el resultado frente a la clase minoritaria."],
  }),
  nodoMock(null, {
    id: "t-llms",
    etiqueta: "LLMs",
    tipo: "tematica",
    nivel: "alto",
    dominio: 0.8,
    laboratorios: ["C2-L1", "C2-L2"],
    evidencias: ["La respuesta del modelo se valida con Pydantic antes de guardarla."],
    por_profundizar: ["Manejo de errores de formato y reintentos."],
  }),
  nodoMock("t-llms", {
    id: "k-salida",
    etiqueta: "Salida estructurada y validación",
    tipo: "concepto",
    nivel: "alto",
    dominio: 0.9,
    laboratorios: ["C2-L1"],
    evidencias: ["Define un esquema JSON y rechaza respuestas que no lo cumplen."],
  }),
  nodoMock("k-salida", {
    id: "l-c2l1-salida",
    etiqueta: "C2-L1 · Ingeniería de prompts con LLMs",
    tipo: "laboratorio",
    nivel: "alto",
    dominio: 0.9,
    laboratorios: ["C2-L1"],
    evidencias: ["cliente_llm.py:30 — RespuestaSchema.model_validate_json(texto)."],
  }),
  nodoMock("t-llms", {
    id: "k-parametros",
    etiqueta: "Parámetros de generación",
    tipo: "concepto",
    nivel: "medio",
    dominio: 0.6,
    laboratorios: ["C2-L1", "C2-L2"],
    evidencias: ["Fija temperature en 0,2 para respuestas reproducibles."],
    por_profundizar: ["Explicar el efecto de top_p y del tamaño de contexto."],
  }),
  nodoMock("k-parametros", {
    id: "l-c2l1-parametros",
    etiqueta: "C2-L1 · Ingeniería de prompts con LLMs",
    tipo: "laboratorio",
    nivel: "medio",
    dominio: 0.6,
    laboratorios: ["C2-L1"],
    evidencias: ["Informe, pág. 2: tabla que compara temperature 0,2 y 0,8."],
  }),
  nodoMock(null, {
    id: "t-prompts",
    etiqueta: "Ingeniería de prompts",
    tipo: "tematica",
    nivel: "alto",
    dominio: 0.9,
    laboratorios: ["C2-L1"],
    evidencias: ["Se definió un rol de experto y un formato JSON de salida con dos ejemplos."],
    por_profundizar: ["Versionado de prompts."],
  }),
  nodoMock("t-prompts", {
    id: "k-fewshot",
    etiqueta: "Few-shot",
    tipo: "concepto",
    nivel: "alto",
    dominio: 1,
    laboratorios: ["C2-L1"],
    evidencias: ["Uso de dos ejemplos representativos en el prompt."],
  }),
  nodoMock("k-fewshot", {
    id: "l-c2l1-fewshot",
    etiqueta: "C2-L1 · Ingeniería de prompts con LLMs",
    tipo: "laboratorio",
    nivel: "alto",
    dominio: 1,
    laboratorios: ["C2-L1"],
    evidencias: ["prompts/clasificar.md — sección «Ejemplos» con dos casos."],
  }),
  nodoMock("t-prompts", {
    id: "k-rol",
    etiqueta: "Rol y formato de salida",
    tipo: "concepto",
    nivel: "alto",
    dominio: 0.85,
    laboratorios: ["C2-L1"],
    evidencias: ["El prompt fija un rol de evaluador y exige salida en JSON."],
  }),
  nodoMock("k-rol", {
    id: "l-c2l1-rol",
    etiqueta: "C2-L1 · Ingeniería de prompts con LLMs",
    tipo: "laboratorio",
    nivel: "alto",
    dominio: 0.85,
    laboratorios: ["C2-L1"],
    evidencias: ["prompts/clasificar.md:1-8 — instrucciones de rol y formato."],
  }),
  nodoMock("t-prompts", {
    id: "k-versionado",
    etiqueta: "Versionado de prompts",
    tipo: "concepto",
    nivel: "sin_evidencia",
    dominio: null,
    por_profundizar: ["Guardar cada prompt con un número de versión y registrar los cambios."],
  }),
  nodoMock(null, {
    id: "t-locales",
    etiqueta: "Modelos locales (Ollama/LM Studio)",
    tipo: "tematica",
    nivel: "medio",
    dominio: 0.6,
    laboratorios: ["C2-L2"],
    evidencias: ["Ejecutó llama3 en Ollama y lo consumió desde Python."],
    por_profundizar: ["Comparar latencia y calidad frente a un modelo en la nube."],
  }),
  nodoMock("t-locales", {
    id: "k-ollama",
    etiqueta: "Ejecución con Ollama",
    tipo: "concepto",
    nivel: "medio",
    dominio: 0.6,
    laboratorios: ["C2-L2"],
    evidencias: ["Documenta los comandos para descargar y servir el modelo."],
  }),
  nodoMock("k-ollama", {
    id: "l-c2l2-ollama",
    etiqueta: "C2-L2 · RAG con modelos locales",
    tipo: "laboratorio",
    nivel: "medio",
    dominio: 0.6,
    laboratorios: ["C2-L2"],
    evidencias: ["README.md — sección «Cómo ejecutar el modelo local»."],
  }),
  nodoMock(null, {
    id: "t-rag",
    etiqueta: "RAG",
    tipo: "tematica",
    nivel: "medio",
    dominio: 0.6,
    laboratorios: ["C2-L2"],
    evidencias: ["Construyó un flujo de recuperación con un índice vectorial local."],
    por_profundizar: ["Evaluar la calidad de la recuperación con preguntas de prueba."],
  }),
  nodoMock("t-rag", {
    id: "k-embeddings",
    etiqueta: "Embeddings y búsqueda semántica",
    tipo: "concepto",
    nivel: "medio",
    dominio: 0.65,
    laboratorios: ["C2-L2"],
    evidencias: ["Genera embeddings con un modelo local y busca por similitud coseno."],
  }),
  nodoMock("k-embeddings", {
    id: "l-c2l2-embeddings",
    etiqueta: "C2-L2 · RAG con modelos locales",
    tipo: "laboratorio",
    nivel: "medio",
    dominio: 0.65,
    laboratorios: ["C2-L2"],
    evidencias: ["indice.py:20-55 — creación del índice y consulta top-k."],
  }),
  nodoMock("t-rag", {
    id: "k-fragmentacion",
    etiqueta: "Fragmentación de documentos",
    tipo: "concepto",
    nivel: "bajo",
    dominio: 0.4,
    laboratorios: ["C2-L2"],
    evidencias: ["Usa fragmentos de tamaño fijo sin solapamiento."],
    por_profundizar: ["Comparar dos estrategias de fragmentación y su efecto en las respuestas."],
  }),
  nodoMock("k-fragmentacion", {
    id: "l-c2l2-fragmentacion",
    etiqueta: "C2-L2 · RAG con modelos locales",
    tipo: "laboratorio",
    nivel: "bajo",
    dominio: 0.4,
    laboratorios: ["C2-L2"],
    evidencias: ["indice.py:8 — CHUNK = 500 sin justificar el valor."],
  }),
  nodoMock(null, {
    id: "t-etica",
    etiqueta: "Ética y verificación",
    tipo: "tematica",
    nivel: "bajo",
    dominio: 0.35,
    laboratorios: ["C2-L1"],
    evidencias: ["El modelo inventó una referencia bibliográfica en la prueba 3 y no se detectó."],
    por_profundizar: ["Análisis de sesgos.", "Verificación de las respuestas contra fuentes."],
  }),
  nodoMock("t-etica", {
    id: "k-alucinaciones",
    etiqueta: "Detección de alucinaciones",
    tipo: "concepto",
    nivel: "bajo",
    dominio: 0.4,
    laboratorios: ["C2-L1"],
    evidencias: ["Menciona las alucinaciones, pero no propone una forma de detectarlas."],
    por_profundizar: ["Contrastar las citas del modelo con el material original."],
  }),
  nodoMock("k-alucinaciones", {
    id: "l-c2l1-alucinaciones",
    etiqueta: "C2-L1 · Ingeniería de prompts con LLMs",
    tipo: "laboratorio",
    nivel: "bajo",
    dominio: 0.4,
    laboratorios: ["C2-L1"],
    evidencias: ["Informe, pág. 6: «el modelo a veces inventa datos»."],
  }),
  nodoMock("t-etica", {
    id: "k-sesgos",
    etiqueta: "Análisis de sesgos",
    tipo: "concepto",
    nivel: "sin_evidencia",
    dominio: null,
    por_profundizar: ["Documentar al menos dos casos de sesgo en las respuestas de un LLM."],
  }),
  nodoMock(null, {
    id: "t-agentes",
    etiqueta: "Agentes de IA",
    tipo: "tematica",
    nivel: "sin_evidencia",
    dominio: null,
    por_profundizar: ["Aún no hay evaluaciones publicadas en esta temática."],
  }),
  nodoMock(null, {
    id: "t-vision",
    etiqueta: "Visión artificial",
    tipo: "tematica",
    nivel: "sin_evidencia",
    dominio: null,
    por_profundizar: ["Aún no hay evaluaciones publicadas en esta temática."],
  }),
];

/** Mapa de est-1: aristas padre → hijo más una relación transversal (Ollama → laboratorio de RAG). */
export const mapaMock: Mapa = {
  nodos: nodosMapaMock,
  aristas: [
    ...nodosMapaMock.flatMap((nodo) =>
      nodo.padre_id === null ? [] : [{ id: `a-${nodo.id}`, origen: nodo.padre_id, destino: nodo.id }],
    ),
    { id: "a-ollama-embeddings", origen: "k-ollama", destino: "l-c2l2-embeddings" },
  ],
};

/** Mapa de un estudiante sin evaluaciones publicadas (est-2 en el modo mock). */
export const mapaVacioMock: Mapa = { nodos: [], aristas: [] };

export const configIAMock: ConfigIA = {
  proveedor: "gemini",
  modelo: "gemini-3.5-flash-lite",
  temperatura: 0.1,
  actualizado_por: "doc-1",
  actualizado_en: FECHA,
};
