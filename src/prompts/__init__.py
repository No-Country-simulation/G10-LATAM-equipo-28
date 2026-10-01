"""Constructores de prompts del sistema NuevaMente.

Los prompts viven fuera de la lógica de los agentes para poder iterarlos sin
tocar el flujo. Cada builder separa la política del sistema de los datos no
confiables (mensajes del usuario, contenido del documento).
"""

from .investigador import construir_prompt_investigador
from .supervisor import construir_prompt_supervisor

__all__ = ["construir_prompt_supervisor", "construir_prompt_investigador"]
