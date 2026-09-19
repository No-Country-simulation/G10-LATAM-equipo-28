from __future__ import annotations

from dataclasses import dataclass

from src.contracts import NivelDetalle, PerfilDestinatario


@dataclass(frozen=True)
class EspecificacionPedagogica:
    bloom: str
    andamiaje: str
    registro: str
    foco: str
    verbos_recomendados: tuple[str, ...]


_MAPEO_PERFILES: dict[PerfilDestinatario, EspecificacionPedagogica] = {
    PerfilDestinatario.PRINCIPIANTE: EspecificacionPedagogica(
        bloom="Entender",
        andamiaje="Alto",
        registro="Cotidiano",
        foco="Comprensión conceptual",
        verbos_recomendados=("explicar", "identificar", "describir"),
    ),
    PerfilDestinatario.DESARROLLADOR: EspecificacionPedagogica(
        bloom="Aplicar",
        andamiaje="Medio",
        registro="Técnico",
        foco="Ejecución práctica",
        verbos_recomendados=("aplicar", "implementar", "demostrar"),
    ),
    PerfilDestinatario.LIDER_TECNICO: EspecificacionPedagogica(
        bloom="Evaluar",
        andamiaje="Bajo",
        registro="Técnico-estratégico",
        foco="Criterio de decisión",
        verbos_recomendados=("evaluar", "comparar", "justificar"),
    ),
    PerfilDestinatario.GESTOR_EJECUTIVO: EspecificacionPedagogica(
        bloom="Entender",
        andamiaje="Alto",
        registro="Ejecutivo",
        foco="Impacto en negocio",
        verbos_recomendados=("explicar", "relacionar", "resumir"),
    ),
}


def construir_especificacion_pedagogica(
    perfil: PerfilDestinatario,
    nivel_detalle: NivelDetalle,
) -> EspecificacionPedagogica:
    """
    Devuelve la especificación pedagógica base para un perfil.

    `nivel_detalle` forma parte de la firma para respetar el contrato
    actual y permitir refinar el andamiaje posteriormente.
    """
    _ = nivel_detalle

    return _MAPEO_PERFILES[perfil]
