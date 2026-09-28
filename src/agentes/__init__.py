"""Agentes de NuevaMente.

Cada agente es un núcleo puro que recibe sus dependencias inyectadas y devuelve
resultados tipados, desacoplado del grafo y del proveedor de LLM.
"""

from .protocolos import GeneradorEstructurado

__all__ = ["GeneradorEstructurado"]
