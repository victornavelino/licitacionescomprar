"""Cliente para el servicio "ServicioPliegoWS" de Compr.ar Catamarca.

https://comprar.catamarca.gob.ar/API/v1/ServicioPliegoWS.asmx

El binding SOAP de este WS devuelve un error de servidor (NullReferenceException)
al invocarlo directamente. El mismo .asmx expone el protocolo HTTP GET simple (el
que usa el botón "Invocar" de la página de prueba), pero ese servidor también
falla si se lo llama "en frío": el navegador, al entrar antes a la página de
documentación, recibe una cookie de sesión ASP.NET y manda un Referer/User-Agent
de navegador; sin eso, el código del lado del servidor vuelve a fallar con el
mismo tipo de error. Por eso este cliente primero "visita" la página de
documentación (para obtener esa cookie) y recién después invoca la operación
reusando la misma sesión y encabezados de navegador.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

OPERATION_PLIEGOS_APERTURA_PROXIMA = "FindPliegosConAperturaProxima"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}

_session: requests.Session | None = None


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


def _get_session() -> requests.Session:
    """Sesión HTTP reutilizada por proceso, con la cookie de sesión ASP.NET
    obtenida al visitar la página de documentación (como hace el navegador
    antes de que exista la cookie con la que se envía el request real)."""
    global _session
    if _session is not None:
        return _session

    session = requests.Session()
    session.headers.update(_BROWSER_HEADERS)
    try:
        session.get(
            settings.PLIEGOS_SERVICE_URL,
            params={"op": OPERATION_PLIEGOS_APERTURA_PROXIMA},
            timeout=settings.PLIEGOS_SOAP_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning("No se pudo precargar la sesión del WS: %s", exc)

    _session = session
    return session


def find_pliegos_con_apertura_proxima() -> list[dict[str, Any]]:
    """Invoca (vía HTTP GET) FindPliegosConAperturaProxima y devuelve la lista de pliegos."""
    session = _get_session()
    url = f"{settings.PLIEGOS_SERVICE_URL}/{OPERATION_PLIEGOS_APERTURA_PROXIMA}"
    referer = f"{settings.PLIEGOS_SERVICE_URL}?op={OPERATION_PLIEGOS_APERTURA_PROXIMA}"

    try:
        response = session.get(
            url,
            headers={"Referer": referer},
            timeout=settings.PLIEGOS_SOAP_TIMEOUT,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = (response.text or "")[:500]
        raise PliegoServiceError(
            f"Error de red al consumir el WS: {exc}. Respuesta del servidor: {detail}"
        ) from exc
    except requests.RequestException as exc:
        raise PliegoServiceError(f"Error de red al consumir el WS: {exc}") from exc

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise PliegoServiceError(f"Respuesta XML inválida del WS: {exc}") from exc

    return [_element_to_value(child) for child in root]
