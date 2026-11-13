---
description: Ejecuta todas las verificaciones del proyecto (lint, tipos, tests, build) y reporta resultados
---

Ejecuta las verificaciones de `CLAUDE.md` §3 para las partes del proyecto que existan:

1. Backend (si existe `backend/`): `cd backend && ruff check . && pytest -q`
2. Frontend (si existe `frontend/`): `cd frontend && npm run lint && npx tsc --noEmit && npm run build`

Reporta una tabla: Comprobación | Resultado (✅/❌) | Detalle del error. Si algo falla, explica en español la causa probable y propone la corrección mínima, pero **no la apliques sin confirmación**. $ARGUMENTS
