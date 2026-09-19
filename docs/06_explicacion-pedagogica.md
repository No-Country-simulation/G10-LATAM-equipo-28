# Nodo `explicacion_pedagogica`

## Objetivo

Agregar una etapa pedagógica al flujo de NuevaMente antes del Redactor Pedagógico.

Su responsabilidad será transformar el perfil del destinatario y el nivel de detalle en instrucciones pedagógicas concretas que el Redactor pueda utilizar para adaptar el contenido.

## Posición prevista en el flujo

Investigador RAG  
→ `explicacion_pedagogica`  
→ Redactor Pedagógico  
→ Crítico / Revisor

La conexión definitiva se adaptará al `AgentState` y al grafo oficial cuando estén disponibles en `main`.

## Entradas previstas

- `perfil_destinatario`
- `nivel_detalle`
- `formato_salida`
- `nicho_sector`

## Salida prevista

Una especificación pedagógica que contenga, al menos:

- nivel de Bloom
- nivel de andamiaje
- registro lingüístico
- foco pedagógico
- verbos o instrucciones recomendadas para el Redactor

## Mapeo pedagógico base

### Principiante / Transición de carrera

- Bloom: Entender
- Andamiaje: Alto
- Registro: Cotidiano
- Foco: Comprensión conceptual

### Desarrollador Junior / Semi Senior

- Bloom: Aplicar
- Andamiaje: Medio
- Registro: Técnico
- Foco: Ejecución práctica

### Líder Técnico / Arquitecto

- Bloom: Evaluar
- Andamiaje: Bajo
- Registro: Técnico-estratégico
- Foco: Criterio de decisión

### Gestor / Ejecutivo no técnico

- Bloom: Entender
- Andamiaje: Alto
- Registro: Ejecutivo
- Foco: Impacto en negocio

## Responsabilidad del nodo

El nodo no debe generar directamente el paquete educativo final.

Su función será preparar una instrucción pedagógica estructurada para que el Redactor Pedagógico sepa:

1. qué nivel cognitivo utilizar;
2. cuánto apoyo entregar;
3. qué lenguaje utilizar;
4. en qué aspecto enfocar la explicación.

## Criterios iniciales de aceptación

1. No genera el contenido educativo final.
2. Produce instrucciones pedagógicas para el Redactor.
3. Para la misma entrada debe producir la misma especificación pedagógica.
4. No consulta directamente OCI.
5. No consulta directamente ChromaDB.
6. Debe poder probarse de manera aislada.
7. Debe respetar los valores definidos por los contratos actuales.
8. La implementación definitiva deberá adaptarse al `AgentState` oficial del equipo.

## Pendientes de integración

- Confirmar la estructura definitiva de `AgentState`.
- Confirmar el campo donde se almacenará la especificación pedagógica.
- Implementar el nodo en Python.
- Integrarlo en `grafo.py`.
- Conectarlo antes del Redactor Pedagógico.
- Agregar pruebas unitarias y de integración.
