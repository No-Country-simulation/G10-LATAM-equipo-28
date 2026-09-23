from __future__ import annotations

from dataclasses import dataclass

from src.contracts import NivelDetalle, PerfilDestinatario


@dataclass(frozen=True)
class EspecificacionPedagogica:
    """
    Especificación pedagógica canónica consumida por la orquestación.

    El contrato público utiliza exactamente estos cinco campos:
    bloom, andamiaje, registro, foco y verbos.
    """

    bloom: str
    andamiaje: str
    registro: str
    foco: str
    verbos: tuple[str, ...]

    @property
    def verbos_recomendados(self) -> tuple[str, ...]:
        """
        Alias temporal de compatibilidad.

        Permite que el código existente que todavía utiliza
        `verbos_recomendados` continúe funcionando mientras se migra
        al nombre canónico `verbos`.
        """
        return self.verbos


_MAPEO_PERFILES: dict[PerfilDestinatario, EspecificacionPedagogica] = {
    PerfilDestinatario.PRINCIPIANTE: EspecificacionPedagogica(
        bloom="Entender",
        andamiaje="Alto",
        registro="Cotidiano",
        foco="Comprensión conceptual",
        verbos=("explicar", "identificar", "describir"),
    ),
    PerfilDestinatario.DESARROLLADOR: EspecificacionPedagogica(
        bloom="Aplicar",
        andamiaje="Medio",
        registro="Técnico",
        foco="Ejecución práctica",
        verbos=("aplicar", "implementar", "demostrar"),
    ),
    PerfilDestinatario.LIDER_TECNICO: EspecificacionPedagogica(
        bloom="Evaluar",
        andamiaje="Bajo",
        registro="Técnico-estratégico",
        foco="Criterio de decisión",
        verbos=("evaluar", "comparar", "justificar"),
    ),
    PerfilDestinatario.GESTOR_EJECUTIVO: EspecificacionPedagogica(
        bloom="Entender",
        andamiaje="Alto",
        registro="Ejecutivo",
        foco="Impacto en negocio",
        verbos=("explicar", "relacionar", "resumir"),
    ),
}


def construir_especificacion_pedagogica(
    perfil: PerfilDestinatario,
    nivel_detalle: NivelDetalle,
) -> EspecificacionPedagogica:
    """
    Devuelve la especificación pedagógica base para un perfil.

    `nivel_detalle` forma parte de la firma pública porque el contrato
    del proyecto lo requiere, pero actualmente no modifica el mapping.

    No se aplica una regla automática hasta que el equipo defina
    explícitamente cómo debe afectar al andamiaje o a otros parámetros.
    """
    _ = nivel_detalle

    return _MAPEO_PERFILES[perfil]
