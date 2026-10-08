# Cambios

## 2026-10-07 — Hardening y auditoría local

- Valida tema, historial y campos tipados antes de cualquier llamada MCP; el contrato/documento se valida de nuevo tras la ingesta.
- Rechaza confirmaciones HITL malformadas sin autorizar la ingesta o la modificación.
- Mantiene Ollama local disponible sobre loopback IPv4 e IPv6 en el puerto permitido.
- Añade pruebas adversariales y evidencia de auditoría; documenta el riesgo crítico pendiente de ChromaDB.

## 2026-10-07 — Seguridad de Sprint 3

- Añade validación determinística de la entrada y de la clasificación del Supervisor antes de continuar a otros agentes LLM.
- Añade límites por etapa para herramientas MCP y una política local de allowlist para endpoints de proveedores.
- Valida instrucciones del Modificador y restringe las lecturas al prefijo `fuentes/`.
- Documenta los límites del control local y las tareas de egress e IAM que Franklin debe revisar.
