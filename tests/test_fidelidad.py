"""
NuevaMente — Pruebas del cálculo de fidelidad en cascada.

La prueba que justifica el módulo es `test_detecta_la_afirmacion_contaminada`:
si el score no baja cuando se le inyecta una afirmación inventada, el mecanismo
no mide nada y el diferenciador del producto es decorativo.

Ejecutar:  pytest tests/test_fidelidad.py -v
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.contracts import PaqueteEducativo  # noqa: E402
from src.fidelidad import (  # noqa: E402
    Afirmacion,
    Chunk,
    calcular_fidelidad,
    calibrar_bandas,
    coseno,
    extraer_afirmaciones,
    resumen_de_cobertura,
)

# =============================================================================
# Dobles de prueba
# =============================================================================

#: Vocabulario FIJO. Es importante que sea fijo: un embeder que arme vocabulario
#: por llamada devuelve vectores de espacios distintos y la comparación pierde
#: sentido. Los modelos reales son estables; el doble también debe serlo.
_VOCAB = (
    "vcn", "red", "privada", "personalizable", "oracle", "cloud",
    "subred", "subredes", "gateway", "security", "lists", "tráfico",
    "ingress", "egress", "precio", "dólares", "mensuales", "scrum",
    "master", "equipo", "facilita", "impedimentos",
)


def embeder_falso(textos):
    """Bolsa de palabras sobre un vocabulario fijo. Determinista."""
    vectores = []
    for t in textos:
        palabras = set(t.lower().replace("?", "").replace(",", "").split())
        vectores.append([1.0 if v in palabras else 0.0 for v in _VOCAB])
    return vectores


def juez_siempre(veredicto: str):
    """Juez LLM de prueba que siempre dictamina lo mismo."""

    def _juez(afirmacion, chunks):
        return veredicto

    return _juez


CHUNKS = [
    Chunk("c1", "La VCN es una red privada y personalizable en Oracle Cloud"),
    Chunk("c2", "Las security lists controlan el tráfico con reglas ingress y egress"),
]


def af(texto: str, anclaje=()) -> Afirmacion:
    return Afirmacion(texto=texto, item_indice=0, campo="dorso", anclaje_declarado=anclaje)


# =============================================================================
# 1. La prueba central
# =============================================================================


def test_detecta_la_afirmacion_contaminada():
    """
    🔴 LA PRUEBA QUE JUSTIFICA EL MÓDULO.

    Se toma un paquete correcto, se le inyecta una afirmación que NO está en la
    fuente, y el score tiene que bajar. Si no baja, el mecanismo no mide nada.

    Es también el momento más convincente de la demo: mostrar el antes y el
    después en vivo.
    """
    limpias = [
        af("La VCN es una red privada y personalizable en Oracle Cloud"),
        af("Las security lists controlan el tráfico con reglas ingress y egress"),
    ]
    contaminadas = limpias + [af("El precio de la VCN es de cien dólares mensuales")]

    r_limpio = calcular_fidelidad(limpias, CHUNKS, embeder_falso)
    r_sucio = calcular_fidelidad(contaminadas, CHUNKS, embeder_falso)

    assert r_limpio.score > r_sucio.score, "El score no reacciona a una alucinación"
    assert r_limpio.score == 1.0
    assert any(v.sospechosa for v in r_sucio.veredictos)


# =============================================================================
# 2. La cascada: cada zona resuelve por donde debe
# =============================================================================


def test_zona_alta_no_llama_al_llm():
    """Si la similitud es alta, no se gasta una llamada: se acepta."""
    r = calcular_fidelidad(
        [af("La VCN es una red privada y personalizable en Oracle Cloud")],
        CHUNKS,
        embeder_falso,
        juez_llm=juez_siempre("no_soportada"),
    )
    assert r.llamadas_al_llm == 0
    assert r.veredictos[0].metodo == "coseno_alto"
    assert r.score == 1.0


def test_zona_baja_no_llama_al_llm():
    """Si no se parece a nada, tampoco: es alucinación sin discusión."""
    r = calcular_fidelidad(
        [af("El precio mensual es de cien dólares")],
        CHUNKS,
        embeder_falso,
        juez_llm=juez_siempre("soportada"),
    )
    assert r.llamadas_al_llm == 0
    assert r.veredictos[0].metodo == "coseno_bajo"
    assert r.score == 0.0


def test_zona_dudosa_si_llama_al_llm():
    """El LLM se gasta SOLO en la banda del medio. Ahí está el ahorro."""
    dudosa = af("La red privada de Oracle usa subredes y gateway")
    r = calcular_fidelidad(
        [dudosa], CHUNKS, embeder_falso,
        juez_llm=juez_siempre("soportada"),
        banda_alta=0.95, banda_baja=0.10,   # se fuerza la banda dudosa
    )
    assert r.llamadas_al_llm == 1
    assert r.veredictos[0].metodo == "verificador_llm"
    assert r.score == 1.0


@pytest.mark.parametrize(
    "fallo,esperado", [("soportada", 1.0), ("parcial", 0.5), ("no_soportada", 0.0)]
)
def test_los_tres_veredictos_del_juez(fallo, esperado):
    r = calcular_fidelidad(
        [af("La red privada de Oracle usa subredes y gateway")],
        CHUNKS, embeder_falso,
        juez_llm=juez_siempre(fallo),
        banda_alta=0.95, banda_baja=0.10,
    )
    assert r.score == esperado


def test_veredicto_desconocido_del_juez_no_rompe():
    """Si el LLM devuelve cualquier cosa, cuenta como no soportada. No explota."""
    r = calcular_fidelidad(
        [af("La red privada de Oracle usa subredes y gateway")],
        CHUNKS, embeder_falso,
        juez_llm=juez_siempre("no sé, tal vez"),
        banda_alta=0.95, banda_baja=0.10,
    )
    assert r.score == 0.0


def test_sin_juez_la_zona_dudosa_reescala_la_similitud():
    """Modo sin LLM: sirve para desarrollo y si se agota la cuota."""
    r = calcular_fidelidad(
        [af("La red privada de Oracle usa subredes y gateway")],
        CHUNKS, embeder_falso, juez_llm=None,
        banda_alta=0.95, banda_baja=0.10,
    )
    similitud = r.veredictos[0].similitud
    assert r.llamadas_al_llm == 0
    assert 0.10 <= similitud < 0.95
    assert r.score == pytest.approx((similitud - 0.10) / (0.95 - 0.10))


def test_sin_juez_el_reescalado_no_infla_el_puntaje():
    """
    Con e5 el coseno casi nunca baja de ~0.73. Con las bandas sugeridas por la
    calibración (0.8457 / 0.8885), una afirmación en el medio de la zona
    dudosa vale 0.5, no su coseno crudo (0.867).
    """
    baja, alta = 0.8457, 0.8885
    medio = (baja + alta) / 2

    def embeder_a_coseno(textos):
        # Cada afirmación queda a coseno `medio` del único chunk, [1, 0].
        return [[medio, math.sqrt(1 - medio**2)] for _ in textos]

    r = calcular_fidelidad(
        [af("Una afirmación cualquiera")],
        [Chunk("c1", "Un chunk cualquiera")],
        embeder_a_coseno,
        vectores_chunks=[[1.0, 0.0]],
        banda_alta=alta, banda_baja=baja,
    )
    assert r.veredictos[0].similitud == pytest.approx(medio)
    assert r.score == pytest.approx(0.5)


def test_el_ahorro_de_llamadas_es_real():
    """
    La razón de ser de la cascada: la mayoría se resuelve sin LLM.
    Con 4 afirmaciones (2 claras arriba, 2 claras abajo), cero llamadas.
    """
    afirmaciones = [
        af("La VCN es una red privada y personalizable en Oracle Cloud"),
        af("Las security lists controlan el tráfico con reglas ingress y egress"),
        af("El precio mensual es de cien dólares"),
        af("El scrum master facilita al equipo"),
    ]
    r = calcular_fidelidad(afirmaciones, CHUNKS, embeder_falso, juez_siempre("parcial"))
    assert r.llamadas_al_llm == 0
    assert r.evaluadas == 4


# =============================================================================
# 3. Casos límite
# =============================================================================


def test_sin_afirmaciones():
    assert calcular_fidelidad([], CHUNKS, embeder_falso).score == 0.0


def test_sin_chunks_el_score_es_cero():
    """Sin fuente no hay anclaje posible. No es un error: es score 0."""
    r = calcular_fidelidad([af("Cualquier cosa afirmada aquí")], [], embeder_falso)
    assert r.score == 0.0
    assert r.veredictos[0].puntaje == 0.0


def test_coseno_con_vector_nulo():
    assert coseno([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_coseno_identico_es_uno():
    assert coseno([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


# =============================================================================
# 4. Integración con el contrato
# =============================================================================


def test_el_resultado_arma_el_bloque_del_contrato():
    r = calcular_fidelidad(
        [af("La VCN es una red privada y personalizable en Oracle Cloud")],
        CHUNKS, embeder_falso,
    )
    bloque = r.a_evaluacion_calidad("Sin observaciones.", "Alta")
    assert bloque["anclaje_fuente_score"] == 1.0
    assert bloque["afirmaciones_evaluadas"] == 1
    assert bloque["afirmaciones_soportadas"] == 1


def test_supera_umbral():
    r = calcular_fidelidad(
        [af("La VCN es una red privada y personalizable en Oracle Cloud")],
        CHUNKS, embeder_falso,
    )
    assert r.supera(0.80)
    assert not r.supera(1.01)


# =============================================================================
# 5. Extracción consciente del formato
# =============================================================================

_PAQUETE_FLASHCARDS = {
    "status": "exito",
    "metadatos": {
        "perfil_aplicado": "Principiante",
        "formato_generado": "Flashcards",
        "tiempo_estimado_estudio_minutos": 5,
        "conceptos_clave": ["VCN"],
    },
    "contenido_adaptado": {
        "titulo": "Redes en la nube desde cero",
        "introduccion_contextualizada": "Imagina la VCN como tu propio barrio privado.",
        "items": [
            {
                "frente": "¿Qué es una VCN en Oracle Cloud?",
                "dorso": "Es una red privada y personalizable dentro de la nube de Oracle.",
                "pista_didactica": "Piénsala como el terreno cercado donde viven tus servidores.",
                "anclaje": ["c1"],
            }
        ],
    },
    "evaluacion_calidad": {
        "anclaje_fuente_score": 0.9,
        "claridad_pedagogica": "Alta",
        "observaciones": "Sin observaciones relevantes.",
    },
    "almacenamiento_oci": {
        "bucket": "b", "objeto_id": "o.json", "status_upload": "completado",
    },
}


def test_no_verifica_la_pista_didactica():
    """
    🔴 DECISIÓN DE DISEÑO IMPORTANTE.

    `pista_didactica` es una analogía inventada A PROPÓSITO ("piénsala como un
    terreno cercado"). Medirla contra la fuente marcaría alucinación en cada
    tarjeta y hundiría el score justo por hacer bien el trabajo didáctico.
    """
    p = PaqueteEducativo.model_validate(_PAQUETE_FLASHCARDS)
    afirmaciones = extraer_afirmaciones(p)

    assert len(afirmaciones) == 1
    assert afirmaciones[0].campo == "dorso"
    assert all("terreno cercado" not in a.texto for a in afirmaciones)
    assert all("barrio privado" not in a.texto for a in afirmaciones)


def test_conserva_el_anclaje_declarado():
    """Sirve para darle al juez LLM los chunks correctos, no los más parecidos."""
    p = PaqueteEducativo.model_validate(_PAQUETE_FLASHCARDS)
    assert extraer_afirmaciones(p)[0].anclaje_declarado == ("c1",)


def test_resumen_de_cobertura_es_honesto():
    """
    El score no cubre el 100% del texto, y decirlo en la presentación es más
    sólido que esperar a que lo pregunten.
    """
    p = PaqueteEducativo.model_validate(_PAQUETE_FLASHCARDS)
    r = resumen_de_cobertura(p)
    assert r["campos_verificados"] == ["dorso"]
    assert r["afirmaciones_extraidas"] < r["campos_de_texto_totales"]


def test_tutorial_verifica_instruccion_y_resultado():
    datos = {
        **_PAQUETE_FLASHCARDS,
        "metadatos": {**_PAQUETE_FLASHCARDS["metadatos"], "formato_generado": "Tutorial"},
        "contenido_adaptado": {
            "titulo": "Crear una VCN",
            "introduccion_contextualizada": "Vamos paso a paso.",
            "items": [
                {
                    "paso_numero": 1,
                    "titulo_paso": "Abrir la consola",
                    "instruccion": "Entra a la consola de OCI y abre el menú Networking.",
                    "resultado_esperado": "Verás la lista de VCN del compartimento actual.",
                }
            ],
        },
    }
    p = PaqueteEducativo.model_validate(datos)
    campos = {a.campo for a in extraer_afirmaciones(p)}
    assert campos == {"instruccion", "resultado_esperado"}


def test_los_campos_verificables_existen_en_el_contrato():
    """
    Cada campo que se verifica tiene que existir en el esquema de su formato.

    Si el contrato renombra un campo (en el Guion, `narracion` pasó a ser
    `guion`), la extracción no falla: deja de verificar ese campo sin avisar.
    """
    from src.contracts import MODELO_ITEM_POR_FORMATO, FormatoSalida
    from src.fidelidad import campos_verificables

    for formato in FormatoSalida:
        campos = set(campos_verificables(formato))
        assert campos, f"{formato.value} no verifica ningún campo"
        faltan = campos - set(MODELO_ITEM_POR_FORMATO[formato].model_fields)
        assert not faltan, f"{formato.value}: {sorted(faltan)} no están en el contrato"


# =============================================================================
# 6. Calibración
# =============================================================================


def test_calibrar_con_separacion_perfecta():
    """Si los dos grupos no se solapan, las bandas colapsan en un solo corte."""
    alta, baja = calibrar_bandas(ancladas=[0.90, 0.92, 0.95], alucinadas=[0.20, 0.31])
    assert alta == baja
    assert 0.31 < alta < 0.90


def test_calibrar_con_solapamiento_deja_banda_dudosa():
    alta, baja = calibrar_bandas(ancladas=[0.60, 0.88], alucinadas=[0.30, 0.72])
    assert baja == 0.60 and alta == 0.72
    assert baja < alta, "Con solapamiento tiene que quedar una banda dudosa"


def test_calibrar_sin_datos_devuelve_los_defaults():
    from src.fidelidad import BANDA_ALTA, BANDA_BAJA

    assert calibrar_bandas([], []) == (BANDA_ALTA, BANDA_BAJA)


# =============================================================================
# 7. Vectores de chunks ya calculados (embeddings por API)
# =============================================================================


def test_el_revisor_extrae_sin_el_paquete_completo():
    """
    En el Revisor todavía no hay PaqueteEducativo (falta almacenamiento_oci).
    Con el formato y los ítems del borrador basta, y el resultado es el mismo.
    """
    from src.fidelidad import extraer_afirmaciones_de_items

    items = [
        {
            "frente": "¿Qué es una VCN?",
            "dorso": "Es una red virtual privada dentro de la nube de Oracle.",
            "pista_didactica": "Piénsala como un barrio cercado.",
            "anclaje": ["c1"],
        }
    ]
    afirmaciones = extraer_afirmaciones_de_items("Flashcards", items)
    assert [a.campo for a in afirmaciones] == ["dorso"]
    assert afirmaciones[0].anclaje_declarado == ("c1",)


def test_con_vectores_de_chroma_no_re_embebe_los_chunks():
    """
    Con embeddings por API cada llamada gasta cuota. Los vectores de los chunks
    ya están en Chroma: el embeder solo debe recibir las afirmaciones.
    """
    llamadas: list[int] = []

    def embeder_contador(textos):
        llamadas.append(len(textos))
        return embeder_falso(textos)

    afirmaciones = [af("La VCN es una red privada y personalizable en Oracle Cloud")]
    vectores = embeder_falso([c.texto for c in CHUNKS])  # "lo que devolvería Chroma"

    r = calcular_fidelidad(
        afirmaciones, CHUNKS, embeder_contador, vectores_chunks=vectores
    )

    assert llamadas == [1], "Solo debería embeber la afirmación, no los chunks"
    assert r.score == 1.0


def test_vectores_de_chunks_desalineados_fallan_claro():
    """Si la cantidad no coincide, el error dice qué pasó en vez de puntuar mal."""
    with pytest.raises(ValueError, match="mismo orden y cantidad"):
        calcular_fidelidad(
            [af("La VCN es una red privada")],
            CHUNKS,
            embeder_falso,
            vectores_chunks=embeder_falso([CHUNKS[0].texto]),
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", "--tb=short"]))
