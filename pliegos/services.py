"""Cliente para el servicio SOAP "ServicioPliegoWS" de Compr.ar Catamarca.

https://comprar.catamarca.gob.ar/API/v1/ServicioPliegoWS.asmx
"""

from __future__ import annotations

import datetime
import decimal
import logging
from functools import lru_cache
from typing import Any

import requests
import zeep
from django.conf import settings
from zeep.exceptions import Error as ZeepError
from zeep.helpers import serialize_object
from zeep.transports import Transport

logger = logging.getLogger(__name__)

# Nombre de la operación SOAP tal como se expone en el WSDL.
OPERATION_PLIEGOS_APERTURA_PROXIMA = "FindPliegosConAperturaProxima"


class PliegoServiceError(Exception):
    """Error al consumir el servicio SOAP de pliegos."""


@lru_cache(maxsize=1)
def get_soap_client() -> zeep.Client:
    """Crea (una única vez por proceso) el cliente SOAP del WSDL configurado."""
    session = requests.Session()
    transport = Transport(session=session, timeout=settings.PLIEGOS_SOAP_TIMEOUT)
    try:
        return zeep.Client(wsdl=settings.PLIEGOS_WSDL_URL, transport=transport)
    except (ZeepError, requests.RequestException) as exc:
        raise PliegoServiceError(
            f"No se pudo obtener/parsear el WSDL en {settings.PLIEGOS_WSDL_URL}: {exc}"
        ) from exc


def _json_safe(value: Any) -> Any:
    """Convierte tipos devueltos por zeep (Decimal, date, datetime, etc.) a JSON-safe."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return value


def list_operations() -> dict[str, str]:
    """Devuelve las operaciones disponibles en el WSDL con su firma de entrada.

    Útil para inspeccionar el servicio real (requiere acceso de red al WSDL),
    dado que la firma exacta de FindPliegosConAperturaProxima puede variar.
    """
    client = get_soap_client()
    operations: dict[str, str] = {}
    for service in client.wsdl.services.values():
        for port in service.ports.values():
            for name, operation in port.binding._operations.items():
                operations[name] = str(operation.input.signature())
    return operations


def find_pliegos_con_apertura_proxima(**kwargs: Any) -> list[dict[str, Any]]:
    """Invoca la operación FindPliegosConAperturaProxima del WS.

    Cualquier parámetro que la operación real requiera (por ejemplo, cantidad
    de días hacia adelante, organismo, página, etc.) puede pasarse como
    keyword argument; se reenvía tal cual al cliente SOAP. Ejecutar
    ``python manage.py inspect_soap_service`` contra el WSDL real para ver la
    firma exacta esperada.
    """
    client = get_soap_client()
    operation = getattr(client.service, OPERATION_PLIEGOS_APERTURA_PROXIMA)
    try:
        result = operation(**kwargs)
    except ZeepError as exc:
        raise PliegoServiceError(f"Error del servicio SOAP: {exc}") from exc
    except requests.RequestException as exc:
        raise PliegoServiceError(f"Error de red al consumir el WS: {exc}") from exc

    serialized = serialize_object(result, target_cls=dict)
    if serialized is None:
        return []

    # El WSDL suele envolver la colección en un nodo intermedio (p.ej. "Pliego"
    # o "diffgram"); si el resultado no es directamente una lista, buscamos la
    # primera lista anidada, y si no hay ninguna devolvemos el objeto como
    # único elemento.
    if isinstance(serialized, list):
        items = serialized
    elif isinstance(serialized, dict):
        items = None
        for value in serialized.values():
            if isinstance(value, list):
                items = value
                break
            if isinstance(value, dict):
                nested = next((v for v in value.values() if isinstance(v, list)), None)
                if nested is not None:
                    items = nested
                    break
        if items is None:
            items = [serialized]
    else:
        items = [serialized]

    return [_json_safe(item) for item in items]
