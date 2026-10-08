import pytest

from src.seguridad.permisos import (
    AccesoHerramientaDenegado,
    ETAPAS_AGENTE_SIN_HERRAMIENTAS,
    obtener_herramienta_autorizada,
)


class Herramienta:
    def __init__(self, name):
        self.name = name


def test_nodo_deterministico_solo_recibe_la_herramienta_de_su_etapa():
    lista = Herramienta("listar_documentos_fuente")
    guardar = Herramienta("guardar_resultado_formateado")
    assert obtener_herramienta_autorizada(
        [lista, guardar], etapa="buscador_documentos", nombre="listar_documentos_fuente"
    ) is lista
    with pytest.raises(AccesoHerramientaDenegado):
        obtener_herramienta_autorizada(
            [lista, guardar], etapa="buscador_documentos", nombre="guardar_resultado_formateado"
        )


@pytest.mark.parametrize("agente", sorted(ETAPAS_AGENTE_SIN_HERRAMIENTAS))
def test_agentes_no_tienen_permisos_de_herramientas_mcp(agente):
    with pytest.raises(AccesoHerramientaDenegado):
        obtener_herramienta_autorizada(
            [Herramienta("listar_documentos_fuente")], etapa=agente,
            nombre="listar_documentos_fuente",
        )
