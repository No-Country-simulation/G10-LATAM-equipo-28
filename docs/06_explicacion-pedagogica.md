# Capa de adaptación pedagógica

## Propósito y evolución arquitectónica

La capa `src/pedagogia/` construye una `spec_pedagogica` determinística a partir del perfil destinatario. `nivel_detalle` forma parte de la interfaz recibida, pero actualmente no modifica el mapping. La especificación orienta cómo redactar el contenido educativo; la capa no genera directamente ese contenido.

### Evolución arquitectónica

Inicialmente se contempló `explicacion_pedagogica` como un nodo LangGraph independiente entre el Investigador RAG y el Redactor Pedagógico. El 5TO SPEC DE CAMBIOS consolidó la arquitectura del flujo y definió cinco agentes LLM. En el diseño vigente, la lógica pedagógica se conserva como un helper determinístico consumido por el Redactor Pedagógico. Esta evolución mantiene el trabajo pedagógico y lo integra en la responsabilidad de redacción, sin agregar un sexto agente ni un nodo adicional al grafo.

## Relación con la arquitectura vigente

Los cinco agentes LLM declarados por el 5TO SPEC son:

1. Supervisor
2. Investigador RAG
3. Redactor Pedagógico
4. Crítico/Revisor
5. Modificador

`src/pedagogia/` no es un agente y no añade un nodo al grafo. Su especificación será consumida por `agente_redactor_pedagogico.py`.

El Redactor Pedagógico genera `contenido_adaptado` utilizando los chunks fuente y el sub-esquema correspondiente al formato de salida. Sus instrucciones mantienen la fidelidad a la fuente: la adaptación pedagógica no autoriza a agregar información sin respaldo en los chunks.

El Crítico/Revisor valida el formato, los typos y la fidelidad según el 5TO SPEC.

## Contrato público

La salida actual de `preparar_explicacion_pedagogica()` contiene exactamente estos campos:

```python
{
    "bloom": str,
    "andamiaje": str,
    "registro": str,
    "foco": str,
    "verbos": list[str],
}
```

Los verbos recomendados orientan la redacción y se exponen bajo el nombre canónico `verbos`.

## Mapeo pedagógico base

| Perfil | Bloom | Andamiaje | Registro | Foco | Verbos |
|---|---|---|---|---|---|
| Principiante | Entender | Alto | Cotidiano | Comprensión conceptual | explicar, identificar, describir |
| Desarrollador | Aplicar | Medio | Técnico | Ejecución práctica | aplicar, implementar, demostrar |
| Líder técnico | Evaluar | Bajo | Técnico-estratégico | Criterio de decisión | evaluar, comparar, justificar |
| Gestor ejecutivo | Entender | Alto | Ejecutivo | Impacto en negocio | explicar, relacionar, resumir |

## Interfaz y nivel de detalle

`nivel_detalle` forma parte de la interfaz de `construir_especificacion_pedagogica(perfil, nivel_detalle)`. Actualmente no modifica el mapping: todavía no existe una regla canónica acordada para cambiar Bloom, andamiaje, registro, foco o verbos según ese valor. La función conserva el parámetro sin inventar una fórmula.

## Límites y pruebas

La capa:

- es determinística para las mismas entradas;
- no genera el paquete ni el contenido educativo final;
- no depende de OCI ni de Chroma;
- no depende de LangGraph;
- no depende directamente de un proveedor LLM;
- debe poder probarse de manera aislada.

Las instrucciones del Redactor mantienen la restricción de fidelidad a la fuente. Las pruebas de `src/pedagogia/` verifican por separado el mapping, el fragmento de prompt y el contrato público de cinco campos.
