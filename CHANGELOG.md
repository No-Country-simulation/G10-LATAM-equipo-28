# Cambios

## v1.0.1 — 2026-10-23

- Corrige el arranque documentado: la app exige el **entorno virtual activo**. Con el `streamlit`
  del Python global falla con `ModuleNotFoundError: No module named 'langgraph'`. Se documenta
  también la alternativa `.venv/Scripts/python.exe -m streamlit run app.py`.
- Tag anotado `v1.0.1` sobre `main`.

## v1.0 — 2026-10-23

Primera versión entregable, tag anotado `v1.0`.

- Grafo LangGraph completo: supervisor, investigador, redactor pedagógico, crítico/revisor y
  modificador, con pausas HITL de una ronda y contadores que no se resetean.
- RAG con embeddings e5 multilingües, Chroma persistente por documento (D-07) y umbral de
  recuperación calibrado en 0.83 (D-12).
- Capa pedagógica: perfil del destinatario → nivel de Bloom, andamiaje y registro lingüístico.
- Fidelidad: verificador separado del redactor (D-02), umbral 0.80 con un reintento (D-03) y
  degradación controlada si OCI falla (D-05).
- Persistencia en OCI Object Storage vía servidor MCP propio.
- Interfaz Streamlit con carga de documento, casos de uso y documento de salida.
- Suite completa en verde y README con video, capturas y ejemplo de salida.

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
