"""Cliente para el servicio "ServicioPliegoWS" de Compr.ar Catamarca.

https://comprar.catamarca.gob.ar/API/v1/ServicioPliegoWS.asmx

El binding SOAP de este WS devuelve un error de servidor (NullReferenceException)
al invocarlo, pero el mismo .asmx expone el protocolo HTTP GET simple (el que usa
el botón "Invocar" de la página de prueba), que sí funciona y devuelve el mismo
resultado como XML plano. Por eso este cliente consume esa variante.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OPERATION_PLIEGOS_APERTURA_PROXIMA = "FindPliegosConAperturaProxima"


class PliegoServiceError(Exception):
    """Error al consumir el servicio de pliegos."""


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _element_to_value(element: ET.Element) -> Any:
    children = list(element)
    if not children:
        text = element.text
        return text.strip() if text else None

    child_tags = {_strip_ns(child.tag) for child in children}
    if len(child_tags) == 1:
        # Todos los hijos comparten el mismo tag (p.ej. varios
        # <ActoAdministrativoWSDTO>): lo tratamos como una lista.
        return [_element_to_value(child) for child in children]

    return {_strip_ns(child.tag): _element_to_value(child) for child in children}


def find_pliegos_con_apertura_proxima() -> list[dict[str, Any]]:
    """Invoca (vía HTTP GET) FindPliegosConAperturaProxima y devuelve la lista de pliegos."""
    url = f"{settings.PLIEGOS_SERVICE_URL}/{OPERATION_PLIEGOS_APERTURA_PROXIMA}"
    try:
        response = requests.get(url, timeout=settings.PLIEGOS_SOAP_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise PliegoServiceError(f"Error de red al consumir el WS: {exc}") from exc

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise PliegoServiceError(f"Respuesta XML inválida del WS: {exc}") from exc

    return [_element_to_value(child) for child in root]
