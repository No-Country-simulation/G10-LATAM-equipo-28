"""
NuevaMente — Pruebas del contrato.

LA PRUEBA MÁS IMPORTANTE DEL PROYECTO es test_ejemplo_oficial_valida():
toma el Ejemplo de Solicitud y el Ejemplo de Respuesta tal como están escritos
en el documento del Hackathon (p.4-5) y los valida contra nuestros modelos.

Si esa prueba pasa, el sistema es compatible con lo que un evaluador va a
probar. Si falla, nos apartamos de la especificación oficial.

Ejecutar:   pytest tests/test_contratos.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.contracts import (  # noqa: E402
    ClaridadPedagogica,
    FormatoSalida,
    ItemPreguntaQuiz,
    NichoSector,
    NivelDetalle,
    PaqueteEducativo,
    PerfilDestinatario,
    SolicitudAdaptacion,
    StatusOperacion,
    StatusUpload,
)
from src.errores import CodigoError, ErrorIngesta  # noqa: E402

# =============================================================================
# Los ejemplos oficiales, copiados del documento del Hackathon
# =============================================================================

SOLICITUD_OFICIAL = {
    "documento_titulo": "Introduccion a la Arquitectura de Redes VCN en OCI",
    "documento_contenido": (
        "La Virtual Cloud Network (VCN) es una red privada y personalizable "
        "configurada en Oracle Cloud Infrastructure. Similar a una red de centro "
        "de datos tradicional, la VCN ofrece control total sobre su entorno de red, "
        "incluyendo subredes publicas y privadas, tablas de enrutamiento, Internet "
        "Gateways, NAT Gateways y Security Lists para control de trafico mediante "
        "reglas de entrada (ingress) y salida (egress)."
    ),
    "perfil_destinatario": "Principiante",
    "formato_salida": "Flashcards",
    "nicho_sector": "General",
    "nivel_detalle": "Didactico",
}

RESPUESTA_OFICIAL = {
    "status": "exito",
    "metadatos": {
        "perfil_aplicado": "Principiante",
        "formato_generado": "Flashcards",
        "tiempo_estimado_estudio_minutos": 5,
        "conceptos_clave": ["VCN", "Subredes", "Internet Gateway", "Security Lists"],
    },
    "contenido_adaptado": {
        "titulo": "Dominando Redes en la Nube (VCN) desde Cero",
        "introduccion_contextualizada": (
            "Imagina la VCN como tu propio barrio privado y seguro dentro de la "
            "nube de Oracle, donde tu decides quien entra y quien sale."
        ),
        "items": [
            {
                "frente": "Que es una VCN en Oracle Cloud?",
                "dorso": (
                    "Es tu red virtual privada y personalizada dentro de la nube de "
                    "Oracle, funcionando como la infraestructura de red de tu empresa."
                ),
                "pista_didactica": (
                    "Piensa en ella como el terreno cercado donde residen tus servidores."
                ),
            },
            {
                "frente": "Para que sirven las Security Lists (Listas de Seguridad)?",
                "dorso": (
                    "Son como guardias virtuales con listas de reglas que definen "
                    "exactamente que tipo de trafico de datos puede entrar o salir de tu red."
                ),
                "pista_didactica": "Reglas de entrada (ingress) y reglas de salida (egress).",
            },
        ],
    },
    "evaluacion_calidad": {
        "anclaje_fuente_score": 0.98,
        "claridad_pedagogica": "Alta",
        "observaciones": (
            "Lenguaje ajustado con analogias para publico principiante, sin "
            "tecnicismos excesivos."
        ),
    },
    "almacenamiento_oci": {
        "bucket": "nuevamente-contenidos-educativos",
        "objeto_id": "contenido-vcn-principiante-flashcards-001.json",
        "status_upload": "completado",
    },
}


# =============================================================================
# 1. Compatibilidad con el documento oficial
# =============================================================================


def test_ejemplo_oficial_valida():
    """🔴 LA PRUEBA CRÍTICA: los ejemplos de la p.4-5 validan sin modificarlos."""
    solicitud = SolicitudAdaptacion.model_validate(SOLICITUD_OFICIAL)
    assert solicitud.perfil_destinatario is PerfilDestinatario.PRINCIPIANTE
    assert solicitud.formato_salida is FormatoSalida.FLASHCARDS
    assert solicitud.nivel_detalle is NivelDetalle.DIDACTICO

    paquete = PaqueteEducativo.model_validate(RESPUESTA_OFICIAL)
    assert paquete.status is StatusOperacion.EXITO
    assert paquete.evaluacion_calidad.anclaje_fuente_score == 0.98
    assert len(paquete.contenido_adaptado.items) == 2


def test_la_salida_conserva_los_valores_del_ejemplo():
    """La respuesta debe serializar con los MISMOS textos del ejemplo oficial."""
    paquete = PaqueteEducativo.model_validate(RESPUESTA_OFICIAL)
    d = paquete.model_dump(mode="json")
    assert d["status"] == "exito"
    assert d["metadatos"]["perfil_aplicado"] == "Principiante"
    assert d["metadatos"]["formato_generado"] == "Flashcards"
    assert d["almacenamiento_oci"]["status_upload"] == "completado"


# =============================================================================
# 2. Alias de perfiles y formatos  (A-03 / A-04)
# =============================================================================


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("Principiante", PerfilDestinatario.PRINCIPIANTE),
        ("principiante", PerfilDestinatario.PRINCIPIANTE),
        ("Principiante / Transición de Carrera", PerfilDestinatario.PRINCIPIANTE),
        ("Principiante / Transicion de Carrera", PerfilDestinatario.PRINCIPIANTE),
        ("Desarrollador Junior / Semi Senior", PerfilDestinatario.DESARROLLADOR),
        ("Líder Técnico / Arquitecto", PerfilDestinatario.LIDER_TECNICO),
        ("Lider Tecnico / Arquitecto", PerfilDestinatario.LIDER_TECNICO),
        ("Gestor / Ejecutivo (No Técnico)", PerfilDestinatario.GESTOR_EJECUTIVO),
    ],
)
def test_alias_de_perfil(entrada, esperado):
    assert PerfilDestinatario(entrada) is esperado


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("Flashcards", FormatoSalida.FLASHCARDS),
        ("Flashcards de Memorización", FormatoSalida.FLASHCARDS),
        ("Guía Práctica Paso a Paso (Tutorial)", FormatoSalida.TUTORIAL),
        ("Quiz Interactivo con Justificaciones", FormatoSalida.QUIZ),
        ("Resumen Ejecutivo (TL;DR)", FormatoSalida.RESUMEN_EJECUTIVO),
        ("TL;DR", FormatoSalida.RESUMEN_EJECUTIVO),
        ("Guion de Clase / Video", FormatoSalida.GUION_CLASE),
    ],
)
def test_alias_de_formato(entrada, esperado):
    assert FormatoSalida(entrada) is esperado


def test_ecommerce_acepta_variantes():
    for v in ("E-commerce", "Ecommerce", "e commerce"):
        assert NichoSector(v) is NichoSector.ECOMMERCE


# =============================================================================
# 3. Validación de entrada
# =============================================================================


def test_defaults_de_nicho_y_nivel():
    """A-07: nicho y nivel_detalle tienen valor por defecto."""
    s = SolicitudAdaptacion.model_validate(
        {k: v for k, v in SOLICITUD_OFICIAL.items() if k not in ("nicho_sector", "nivel_detalle")}
    )
    assert s.nicho_sector is NichoSector.GENERAL
    assert s.nivel_detalle is NivelDetalle.ESTANDAR


def test_documento_corto_se_rechaza():
    datos = {**SOLICITUD_OFICIAL, "documento_contenido": "Muy corto."}
    with pytest.raises(ValidationError, match="caracteres"):
        SolicitudAdaptacion.model_validate(datos)


def test_guion_de_clase_no_esta_en_el_mvp():
    """D-01: el quinto formato esta declarado pero no implementado."""
    datos = {**SOLICITUD_OFICIAL, "formato_salida": "Guion de Clase"}
    with pytest.raises(ValidationError, match="no.*implementado en el MVP"):
        SolicitudAdaptacion.model_validate(datos)


def test_campo_desconocido_se_rechaza():
    """extra='forbid': un campo mal escrito no se ignora en silencio."""
    datos = {**SOLICITUD_OFICIAL, "perfil_destinatrio": "Principiante"}
    with pytest.raises(ValidationError):
        SolicitudAdaptacion.model_validate(datos)


def test_clave_de_cache_depende_del_contenido():
    """D-07: el mismo contenido con distinto titulo reutiliza su indice."""
    a = SolicitudAdaptacion.model_validate(SOLICITUD_OFICIAL)
    b = SolicitudAdaptacion.model_validate({**SOLICITUD_OFICIAL, "documento_titulo": "Otro"})
    assert a.clave_cache_documento() == b.clave_cache_documento()


# =============================================================================
# 4. Los items deben coincidir con el formato  (FR-OUT-05)
# =============================================================================


def test_items_de_otro_formato_se_rechazan():
    """Declarar Tutorial y mandar flashcards debe fallar."""
    datos = {
        **RESPUESTA_OFICIAL,
        "metadatos": {**RESPUESTA_OFICIAL["metadatos"], "formato_generado": "Tutorial"},
    }
    with pytest.raises(ValidationError, match="no cumple el esquema"):
        PaqueteEducativo.model_validate(datos)


def test_tutorial_valido():
    datos = {
        **RESPUESTA_OFICIAL,
        "metadatos": {**RESPUESTA_OFICIAL["metadatos"], "formato_generado": "Tutorial"},
        "contenido_adaptado": {
            "titulo": "Crear tu primera VCN",
            "introduccion_contextualizada": "Vamos a crear una red privada paso a paso.",
            "items": [
                {
                    "paso_numero": 1,
                    "titulo_paso": "Abrir la consola",
                    "instruccion": "Entra a la consola de OCI y abre Networking.",
                    "resultado_esperado": "Veras la lista de VCN del compartimento.",
                    "advertencia": "Verifica que estas en la region correcta.",
                },
                {
                    "paso_numero": 2,
                    "titulo_paso": "Crear la VCN",
                    "instruccion": "Haz clic en Create VCN y completa el nombre.",
                    "resultado_esperado": "La VCN aparece en estado Available.",
                },
            ],
        },
    }
    p = PaqueteEducativo.model_validate(datos)
    assert len(p.items_tipados()) == 2


def test_tutorial_con_pasos_salteados_se_rechaza():
    datos = {
        **RESPUESTA_OFICIAL,
        "metadatos": {**RESPUESTA_OFICIAL["metadatos"], "formato_generado": "Tutorial"},
        "contenido_adaptado": {
            "titulo": "Guia",
            "introduccion_contextualizada": "Introduccion de la guia.",
            "items": [
                {
                    "paso_numero": 1,
                    "titulo_paso": "Uno",
                    "instruccion": "Hace esto.",
                    "resultado_esperado": "Pasa esto.",
                },
                {
                    "paso_numero": 5,  # salto
                    "titulo_paso": "Cinco",
                    "instruccion": "Hace aquello.",
                    "resultado_esperado": "Pasa aquello.",
                },
            ],
        },
    }
    with pytest.raises(ValidationError, match="consecutivos"):
        PaqueteEducativo.model_validate(datos)


# =============================================================================
# 5. Quiz: la validación no negociable
# =============================================================================


def test_quiz_con_respuesta_inexistente_se_rechaza():
    """El error mas comun de un LLM generando quizzes. Se valida en el esquema."""
    with pytest.raises(ValidationError, match="no existe entre"):
        ItemPreguntaQuiz.model_validate(
            {
                "pregunta": "Que componente filtra el trafico?",
                "opciones": [
                    {"id": "a", "texto": "Internet Gateway"},
                    {"id": "b", "texto": "Security Lists"},
                    {"id": "c", "texto": "Tabla de enrutamiento"},
                ],
                "respuesta_correcta": "d",  # no existe
                "justificacion": "Las Security Lists definen reglas de ingress y egress.",
            }
        )


def test_quiz_valido():
    item = ItemPreguntaQuiz.model_validate(
        {
            "pregunta": "Que componente filtra el trafico mediante reglas?",
            "opciones": [
                {"id": "A", "texto": "Internet Gateway"},
                {"id": "b", "texto": "Security Lists"},
                {"id": "c", "texto": "Tabla de enrutamiento"},
            ],
            "respuesta_correcta": "B",  # mayuscula: se normaliza
            "justificacion": "Definen que trafico entra y sale.",
            "anclaje": ["chunk_003"],
        }
    )
    assert item.respuesta_correcta == "b"
    assert item.opciones[0].id == "a"
    assert item.anclaje == ["chunk_003"]


def test_quiz_con_menos_de_tres_opciones_se_rechaza():
    with pytest.raises(ValidationError):
        ItemPreguntaQuiz.model_validate(
            {
                "pregunta": "Verdadero o falso?",
                "opciones": [{"id": "a", "texto": "Si"}, {"id": "b", "texto": "No"}],
                "respuesta_correcta": "a",
                "justificacion": "Porque si.",
            }
        )


# =============================================================================
# 6. Coherencia de status  (decisión D-05)
# =============================================================================


def test_fallo_de_oci_no_puede_reportar_exito():
    datos = {
        **RESPUESTA_OFICIAL,
        "almacenamiento_oci": {
            **RESPUESTA_OFICIAL["almacenamiento_oci"],
            "status_upload": "fallido",
        },
    }
    with pytest.raises(ValidationError, match="incoherente"):
        PaqueteEducativo.model_validate(datos)


def test_fallo_de_oci_con_advertencias_es_valido():
    datos = {
        **RESPUESTA_OFICIAL,
        "status": "exito_con_advertencias",
        "almacenamiento_oci": {
            **RESPUESTA_OFICIAL["almacenamiento_oci"],
            "status_upload": "fallido",
            "detalle_fallo": "Tiempo de espera agotado al conectar con Object Storage.",
        },
        "advertencias": ["El paquete se genero pero no se pudo guardar en OCI."],
    }
    p = PaqueteEducativo.model_validate(datos)
    assert p.status is StatusOperacion.EXITO_CON_ADVERTENCIAS
    assert p.almacenamiento_oci.status_upload is StatusUpload.FALLIDO


def test_fidelidad_bajo_umbral_exige_advertencias():
    datos = {
        **RESPUESTA_OFICIAL,
        "evaluacion_calidad": {
            "anclaje_fuente_score": 0.55,
            "claridad_pedagogica": "Requiere revision",
            "observaciones": "Varias afirmaciones no se pudieron anclar en la fuente.",
            "afirmaciones_evaluadas": 20,
            "afirmaciones_soportadas": 11,
            "reintentos_realizados": 1,
            "supero_umbral": False,
        },
    }
    with pytest.raises(ValidationError, match="incoherente"):
        PaqueteEducativo.model_validate(datos)

    datos["status"] = "exito_con_advertencias"
    p = PaqueteEducativo.model_validate(datos)
    assert p.evaluacion_calidad.supero_umbral is False
    assert p.evaluacion_calidad.claridad_pedagogica is ClaridadPedagogica.REQUIERE_REVISION


def test_score_fuera_de_rango_se_rechaza():
    for malo in (-0.1, 1.5):
        datos = {
            **RESPUESTA_OFICIAL,
            "evaluacion_calidad": {
                **RESPUESTA_OFICIAL["evaluacion_calidad"],
                "anclaje_fuente_score": malo,
            },
        }
        with pytest.raises(ValidationError):
            PaqueteEducativo.model_validate(datos)


# =============================================================================
# 7. Añadidos del Decision Gate
# =============================================================================


def test_campos_nuevos_son_opcionales_y_aditivos():
    """El ejemplo oficial no los trae y debe seguir validando."""
    p = PaqueteEducativo.model_validate(RESPUESTA_OFICIAL)
    assert p.metadatos.nicho_aplicado is NichoSector.GENERAL  # A-05
    assert p.metadatos.prerrequisitos == []  # A-09
    assert p.almacenamiento_oci.objeto_documento_original is None  # A-11


def test_prerrequisitos_y_segundo_objeto():
    datos = {
        **RESPUESTA_OFICIAL,
        "metadatos": {
            **RESPUESTA_OFICIAL["metadatos"],
            "nicho_aplicado": "Fintech",
            "prerrequisitos": ["Nociones basicas de redes", "Que es una IP"],
        },
        "almacenamiento_oci": {
            **RESPUESTA_OFICIAL["almacenamiento_oci"],
            "objeto_documento_original": "originales/doc_a1b2c3d4.pdf",
        },
    }
    p = PaqueteEducativo.model_validate(datos)
    assert len(p.metadatos.prerrequisitos) == 2
    assert p.metadatos.nicho_aplicado is NichoSector.FINTECH


def test_nombre_de_objeto_sigue_la_convencion():
    """FR-PER-04, patron evidenciado en el ejemplo oficial."""
    p = PaqueteEducativo.model_validate(RESPUESTA_OFICIAL)
    nombre = p.nombre_objeto_oci()
    assert nombre.startswith("contenido-")
    assert nombre.endswith(".json")
    assert "principiante" in nombre and "flashcards" in nombre


# =============================================================================
# 8. Contrato de error  (A-15)
# =============================================================================


def test_error_produce_contrato_estable():
    err = ErrorIngesta("magic bytes no corresponden a PDF")
    r = err.como_respuesta()
    d = r.model_dump(mode="json")
    assert d["status"] == "error"
    assert d["error"]["codigo"] == CodigoError.DOCUMENTO_NO_SOPORTADO.value
    assert d["error"]["etapa"] == "ingesta"
    assert "PDF" in d["error"]["mensaje_usuario"]


def test_mensaje_al_usuario_no_filtra_detalle_tecnico():
    """NFR-SEC-02: el detalle tecnico va al log, no a la pantalla."""
    tecnico = "Traceback: /home/racso/src/ingesta/extractor.py line 42"
    err = ErrorIngesta(tecnico)
    assert tecnico not in err.como_respuesta().error.mensaje_usuario
    assert err.mensaje_tecnico == tecnico


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", "--tb=short"]))
