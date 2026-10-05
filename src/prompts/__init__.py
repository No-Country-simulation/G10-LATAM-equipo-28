"""Constructores de prompts del sistema NuevaMente.

Los prompts viven fuera de la lógica de los agentes para poder iterarlos sin
tocar el flujo. Cada builder separa la política del sistema de los datos no
confiables (mensajes del usuario, contenido del documento).
"""

from .critico_revisor import construir_prompt_critico_revisor
from .investigador import construir_prompt_investigador
from .modificador import construir_prompt_modificador
from .redactor_pedagogico import construir_prompt_redactor
from .supervisor import construir_prompt_supervisor

__all__ = [
    "construir_prompt_supervisor",
    "construir_prompt_investigador",
    "construir_prompt_redactor",
    "construir_prompt_critico_revisor",
    "construir_prompt_modificador",
]
