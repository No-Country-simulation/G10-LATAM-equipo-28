# Cambios

## 2026-10-07 — Seguridad de Sprint 3

- Añade validación determinística de la entrada y de la clasificación del Supervisor antes de continuar a otros agentes LLM.
- Añade límites por etapa para herramientas MCP y una política local de allowlist para endpoints de proveedores.
- Valida instrucciones del Modificador y restringe las lecturas al prefijo `fuentes/`.
- Documenta los límites del control local y las tareas de egress e IAM que Franklin debe revisar.
